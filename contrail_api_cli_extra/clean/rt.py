# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type

from kazoo.client import KazooClient
from kazoo.handlers.gevent import SequentialGeventHandler

from contrail_api_cli.command import Command, Arg, Option, expand_paths
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import server_type


class CleanRT(Command):
    description = "Clean stale route targets"
    check = Option('-c',
                   default=False,
                   action="store_true",
                   help='Just check RTs')
    dry_run = Option('-n',
                     default=False,
                     action="store_true",
                     help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="RT path(s)",
                metavar='path')
    zk_server = Option(help="Zookeeper server (default: %(default)s)",
                       type=server_type,
                       default='localhost:2181',
                       required=True)

    def log(self, message, rt):
        printo('[%s] %s' % (rt.uuid, message))

    def _get_rt_id(self, rt):
        return int(rt['name'].split(':')[-1])

    def _get_zk_node(self, rt_id):
        return '/id/bgp/route-targets/%010d' % rt_id

    def _ensure_lock(self, rt):
        rt_id = self._get_rt_id(rt)
        # No locks created for rt_id < 8000000
        if rt_id < 8000000:
            return
        zk_node = '/id/bgp/route-targets/%010d' % rt_id
        if not self.zk_client.exists(zk_node):
            if rt.get('logical_router_back_refs'):
                fq_name = rt['logical_router_back_refs'][0].fq_name
            else:
                # FIXME: can't determine routing-instance for route-target
                # don't create any lock
                return
            if not self.dry_run:
                self.zk_client.create(zk_node, text_type(fq_name).encode('utf-8'))
            self.log("Added missing ZK lock %s" % zk_node, rt)

    def _clean_rt(self, rt):
        try:
            if not self.dry_run:
                rt.delete()
            self.log("Removed RT %s" % rt.path, rt)
            rt_id = self._get_rt_id(rt)
            zk_node = self._get_zk_node(rt_id)
            if self.zk_client.exists(zk_node):
                if not self.dry_run:
                    self.zk_client.delete(zk_node)
                self.log("Removed ZK lock %s" % zk_node, rt)
        except ResourceNotFound:
            pass

    def _check_rt(self, rt, check):
        try:
            rt.fetch()
        except ResourceNotFound:
            return
        if not rt.get('routing_instance_back_refs') and not rt.get('logical_router_back_refs'):
            self.log('RT %s staled' % rt.fq_name, rt)
            if check is not True:
                self._clean_rt(rt)
        else:
            self._ensure_lock(rt)

    def __call__(self, paths=None, dry_run=False, check=False, zk_server=None):
        self.zk_client = KazooClient(hosts=zk_server, timeout=1.0,
                                     handler=SequentialGeventHandler())
        self.zk_client.start()
        self.dry_run = dry_run
        if not paths:
            resources = Collection('route-target', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'route-target')
        parallel_map(self._check_rt, resources, args=(check,), workers=50)
        self.zk_client.stop()

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError

from contrail_api_cli.command import Command, Arg, expand_paths
from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.client import HTTPError
from contrail_api_cli.exceptions import CommandError

from ..utils import server_type


class CleanRT(Command):
    description = "Clean stale route targets"
    check = Arg('--check', '-c',
                default=False,
                action="store_true",
                help='Just check RTs')
    dry_run = Arg('--dry-run', '-n',
                  default=False,
                  action="store_true",
                  help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="RT path(s)",
                metavar='path')
    zk_server = Arg('--zk-server',
                    help="Zookeeper server (default: %(default)s)",
                    type=server_type,
                    default='localhost:2181')

    def _get_zk_node(self, rt):
        rt_id = int(rt['name'].split(':')[-1])
        return '/id/bgp/route-targets/%010d' % rt_id

    def _ensure_lock(self, rt):
        zk_node = self._get_zk_node(rt)
        if not self.zk_client.exists(zk_node):
            if not self.dry_run:
                self.zk_client.create(zk_node)
            printo("Added missing ZK lock %s" % zk_node)

    def _clean_rt(self, rt):
        zk_node = self._get_zk_node(rt)
        if self.zk_client.exists(zk_node):
            if not self.dry_run:
                self.zk_client.delete(zk_node)
            printo("Removed ZK lock %s" % zk_node)

        try:
            if not self.dry_run:
                rt.delete()
        except HTTPError as e:
            # Rollback if delete fails
            if not e.http_status == 404:
                self.zk_client.create(zk_node)
                printo("Failed to remove RT %s: %s" (rt.path, str(e)))
        else:
            printo("Removed RT %s" % rt.path)

    def _check_rt(self, rt, check):
        try:
            rt.fetch()
        except HTTPError:
            return
        if not rt.get('routing_instance_back_refs') and not rt.get('logical_router_back_refs'):
            printo('RT %s (%s) staled' % (rt.path, rt.fq_name))
            if check is not True:
                self._clean_rt(rt)
        else:
            self._ensure_lock(rt)

    def __call__(self, paths=None, dry_run=False, check=False, zk_server=None):
        self.zk_client = KazooClient(hosts=zk_server, timeout=1.0)
        try:
            self.zk_client.start()
        except KazooTimeoutError:
            raise CommandError('Failed to connect to %s' % zk_server)
        self.dry_run = dry_run
        if not paths:
            resources = Collection('route-target', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'route-target')
        parallel_map(self._check_rt, resources, args=(check,), workers=50)
        self.zk_client.stop()

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from netaddr import IPNetwork, IPAddress

from kazoo.client import KazooClient
from kazoo.handlers.gevent import SequentialGeventHandler

from contrail_api_cli.command import Command, Arg, Option, expand_paths
from contrail_api_cli.resource import Collection, Resource
from contrail_api_cli.utils import printo, parallel_map
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import server_type


class FixFIPLocks(Command):
    description = "Add missing locks for FIPs"
    check = Option('-c',
                   default=False,
                   action="store_true",
                   help='Just check locks')
    dry_run = Option('-n',
                     default=False,
                     action="store_true",
                     help='Run this command in dry-run mode')
    paths = Arg(nargs="*", help="FIP path(s)",
                metavar='path')
    zk_server = Option(help="Zookeeper server (default: %(default)s)",
                       type=server_type,
                       default='localhost:2181',
                       required=True)
    public_fqname = Option(help="Public network fqname",
                           required=True)

    def log(self, message, fip):
        printo('[%s] %s' % (fip.uuid, message))

    def _get_subnet_for_ip(self, ip, subnets):
        for subnet in subnets:
            if ip in subnet:
                return subnet

    def _zk_node_for_ip(self, ip, subnet):
        return '/api-server/subnets/%s:%s/%i' % (self.public_fqname, subnet, ip)

    def _check_fip(self, fip, subnets):
        try:
            fip.fetch()
        except ResourceNotFound:
            return
        ip = IPAddress(fip.get('floating_ip_address'))
        subnet = self._get_subnet_for_ip(ip, subnets)
        if subnet is None:
            self.log('No subnet found for FIP %s' % ip, fip)
            return
        zk_node = self._zk_node_for_ip(ip, subnet)
        if not self.zk_client.exists(zk_node):
            self.log('Lock not found', fip)
            if self.check is not True or self.dry_run is not True:
                self.zk_client.create(zk_node)

    def __call__(self, paths=None, dry_run=False, check=False, zk_server=None, public_fqname=None):
        self.zk_client = KazooClient(hosts=zk_server, timeout=1.0,
                                     handler=SequentialGeventHandler())
        self.zk_client.start()
        self.dry_run = dry_run
        self.check = check
        self.public_fqname = public_fqname
        if not paths:
            resources = Collection('floating-ip', fetch=True)
        else:
            resources = expand_paths(paths,
                                     predicate=lambda r: r.type == 'floating-ip')

        public_vn = Resource('virtual-network', fq_name=public_fqname, fetch=True)
        subnets = []
        for s in public_vn['network_ipam_refs'][0]['attr']['ipam_subnets']:
            subnets.append(IPNetwork('%s/%s' % (s['subnet']['ip_prefix'], s['subnet']['ip_prefix_len'])))

        parallel_map(self._check_fip, resources, args=(subnets,), workers=50)
        self.zk_client.stop()

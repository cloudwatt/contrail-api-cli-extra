# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import netaddr

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from .utils import ip_type


class AddDnsNameserver(Command):
    nameserver_ips = Arg(nargs="*", metavar='nameserver',
                         help='IPs of DNS servers', default=[],
                         type=ip_type)
    network_ipam_fqname = Arg('--network-ipam-fqname',
                              metavar='fqname',
                              help='Network IPAM fqname (default: %(default)s)',
                              default='default-domain:default-project:default-network-ipam')

    def __call__(self, nameserver_ips=None, network_ipam_fqname=None):
        try:
            server_list = [text_type(netaddr.IPAddress(ip))
                           for ip in nameserver_ips]
        except netaddr.core.AddrFormatError:
            raise CommandError('Wrong IP format')
        if not server_list:
            raise CommandError('No nameservers provided')
        try:
            ipam = Resource('network-ipam', fq_name=network_ipam_fqname,
                            check_fq_name=True)
        except ValueError:
            raise CommandError("Can't find %s" % network_ipam_fqname)

        ipam['network_ipam_mgmt'] = {
            'ipam_dns_method': 'tenant-dns-server',
            'ipam_dns_server': {
                'tenant_dns_server_address': {
                    'ip_address': server_list
                }
            }
        }
        ipam.save()

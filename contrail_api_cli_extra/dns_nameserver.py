# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from .utils import ip_type


class DnsNameserver(Command):
    oper = Arg(help='Add or remove DNS nameservers',
               choices=['add', 'del'])
    ips = Arg('--ips', nargs="+", metavar='nameserver',
              help='IPs of DNS servers',
              type=ip_type,
              default=[],
              required=True)
    network_ipam_fqname = Arg('--network-ipam-fqname',
                              metavar='fqname',
                              help='Network IPAM fqname (default: %(default)s)',
                              default='default-domain:default-project:default-network-ipam')

    def __call__(self, oper=None, ips=None, network_ipam_fqname=None):
        try:
            ipam = Resource('network-ipam', fq_name=network_ipam_fqname,
                            check_fq_name=True, fetch=True)
        except ValueError:
            raise CommandError("Can't find %s" % network_ipam_fqname)

        if 'network_ipam_mgmt' not in ipam:
            ipam['network_ipam_mgmt'] = {
                'ipam_dns_method': 'tenant-dns-server',
                'ipam_dns_server': {
                    'tenant_dns_server_address': {
                        'ip_address': []
                    }
                }
            }
            ipam.save()

        if oper == 'add':
            self.add_dns_ips(ipam, ips)
        elif oper == 'del':
            self.del_dns_ips(ipam, ips)

    def add_dns_ips(self, ipam, ips):
        added = False
        for ip in ips:
            if ip not in ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address']:
                ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'].append(ip)
                added = True
        if added:
            ipam.save()
        else:
            raise CommandError('All IPs already configured')

    def del_dns_ips(self, ipam, ips):
        removed = False
        for ip in ips:
            try:
                ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'].remove(ip)
                removed = True
            except ValueError:
                pass
        if removed:
            ipam.save()
        else:
            raise CommandError('All IPs already not configured')

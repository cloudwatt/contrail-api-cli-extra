# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from ..utils import ip_type


class DNSNameserver(Command):
    network_ipam_fqname = Option(metavar='fqname',
                                 help='Network IPAM fqname (default: %(default)s)',
                                 default='default-domain:default-project:default-network-ipam')

    def __call__(self, network_ipam_fqname=None):
        self.ipam = Resource('network-ipam', fq_name=network_ipam_fqname,
                             fetch=True)

        if 'network_ipam_mgmt' not in self.ipam:
            self.ipam['network_ipam_mgmt'] = {
                'ipam_dns_method': 'tenant-dns-server',
                'ipam_dns_server': {
                    'tenant_dns_server_address': {
                        'ip_address': []
                    }
                }
            }


class DNSNameserverAction(DNSNameserver):
    ips = Arg(nargs="+", metavar='nameserver',
              help='IPs of DNS servers',
              type=ip_type,
              default=[])

    def __call__(self, ips=None, network_ipam_fqname=None):
        super(DNSNameserverAction, self).__call__(network_ipam_fqname=network_ipam_fqname)


class AddDNSNameserver(DNSNameserverAction):
    description = 'Add DNS nameserver'

    def __call__(self, ips=None, network_ipam_fqname=None):
        super(AddDNSNameserver, self).__call__(ips=ips, network_ipam_fqname=network_ipam_fqname)
        added = False
        for ip in ips:
            if ip not in self.ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address']:
                self.ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'].append(ip)
                added = True
        if added:
            self.ipam.save()
        else:
            raise CommandError('All IPs already configured')


class DelDNSNameserver(DNSNameserverAction):
    description = 'Del DNS nameserver'

    def __call__(self, ips=None, network_ipam_fqname=None):
        super(DelDNSNameserver, self).__call__(ips=ips, network_ipam_fqname=network_ipam_fqname)
        removed = False
        for ip in ips:
            try:
                self.ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address'].remove(ip)
                removed = True
            except ValueError:
                pass
        if removed:
            self.ipam.save()
        else:
            raise CommandError('All IPs already not configured')


class ListDNSNameserver(DNSNameserver):
    description = 'List DNS nameservers'

    def __call__(self, network_ipam_fqname=None):
        super(ListDNSNameserver, self).__call__(network_ipam_fqname=network_ipam_fqname)
        ips = self.ipam['network_ipam_mgmt']['ipam_dns_server']['tenant_dns_server_address']['ip_address']
        if ips:
            return json.dumps({
                'ips': ips,
                'network_ipam_fqname': network_ipam_fqname
            })
        else:
            return json.dumps([])

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json
import netaddr

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceNotFound

from .utils import network_type


class Subnet(Command):
    virtual_network_fqname = Arg('--virtual-network-fqname',
                                 required=True,
                                 help='VN fqname (eg: default-domain:admin:net)')

    def _get_network_ipam_subnets(self):
        if 'network_ipam_refs' not in self.vn:
            ipam_ref = {
                "attr": {
                    "ipam_subnets": []
                },
                "to": ["default-domain", "default-project", "default-network-ipam"]
            }
            self.vn['network_ipam_refs'] = []
            self.vn['network_ipam_refs'].append(ipam_ref)
        return self.vn['network_ipam_refs'][0]['attr']['ipam_subnets']

    def __call__(self, virtual_network_fqname=None):
        self.vn = Resource('virtual-network',
                           fq_name=virtual_network_fqname,
                           fetch=True)


class SetSubnets(Subnet):
    description = 'Set subnets to virtual-network'
    cidrs = Arg(nargs="+", metavar='CIDR',
                help='subnet CIDR',
                type=network_type,
                default=[])

    def __call__(self, virtual_network_fqname=None, cidrs=None):
        super(SetSubnets, self).__call__(virtual_network_fqname)
        cidrs = [netaddr.IPNetwork(cidr) for cidr in cidrs]
        ipam_subnets = self._get_network_ipam_subnets()
        ipam_subnets_current = [{
            'subnet': {
                'ip_prefix': s['subnet']['ip_prefix'],
                'ip_prefix_len': s['subnet']['ip_prefix_len']
            }
        } for s in ipam_subnets]
        ipam_subnets_wanted = [{
            'subnet': {
                'ip_prefix': text_type(c.network),
                'ip_prefix_len': c.prefixlen
            }
        } for c in cidrs]

        modified = False
        for idx, subnet in enumerate(ipam_subnets_current):
            if subnet not in ipam_subnets_wanted:
                del ipam_subnets[idx]
                modified = True
        for subnet in ipam_subnets_wanted:
            if subnet not in ipam_subnets_current:
                ipam_subnets.append(subnet)
                modified = True
        if modified:
            self.vn.save()


class GetSubnets(Subnet):
    description = 'Get virtual-network subnets'

    def __call__(self, virtual_network_fqname=None):
        try:
            super(GetSubnets, self).__call__(virtual_network_fqname)
            ipam_subnets = self._get_network_ipam_subnets()
            if ipam_subnets:
                return json.dumps([{'virtual_network_fqname': virtual_network_fqname,
                                    'cidrs': ['%s/%s' % (s['subnet']['ip_prefix'], s['subnet']['ip_prefix_len'])
                                              for s in ipam_subnets]}], indent=2)
        except ResourceNotFound:
            pass
        return json.dumps([])

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json
import netaddr

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import network_type
from common import get_network_ipam_subnets


class SetSubnets(Command):
    description = 'Set subnets to virtual-network'
    virtual_network_fqname = Option(required=True,
                                    help='VN fqname (eg: default-domain:admin:net)')
    cidrs = Arg(nargs="+", metavar='CIDR',
                help='subnet CIDR',
                type=network_type,
                default=[])

    def __call__(self, virtual_network_fqname=None, cidrs=None):
        vn = Resource('virtual-network',
                      fq_name=virtual_network_fqname,
                      fetch=True)

        cidrs = [netaddr.IPNetwork(cidr) for cidr in cidrs]
        ipam_subnets = get_network_ipam_subnets(vn)
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
            vn.save()


class GetSubnets(Command):
    description = 'Get virtual-network subnets'
    virtual_network_fqnames = Option(nargs='+',
                                     required=True,
                                     help='List of VN fqnames (eg: default-domain:admin:net)')

    def __call__(self, virtual_network_fqnames=None):
        res = []
        for virtual_network_fqname in virtual_network_fqnames:
            try:
                vn = Resource('virtual-network',
                              fq_name=virtual_network_fqname,
                              fetch=True)
                ipam_subnets = get_network_ipam_subnets(vn)
                if ipam_subnets:
                    res.append({'virtual_network_fqname': virtual_network_fqname,
                                'cidrs': ['%s/%s' % (s['subnet']['ip_prefix'], s['subnet']['ip_prefix_len'])
                                          for s in ipam_subnets]})
            except ResourceNotFound:
                pass
        return json.dumps(res, indent=2)

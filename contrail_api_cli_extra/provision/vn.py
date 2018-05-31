# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json

import netaddr

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.utils import FQName

from common import get_network_ipam_subnets


class VN(Command):
    project_fqname = Option(required=True,
                            dest='project_fqname',
                            help='Project fqname (eg: default-domain:admin)')


class VNAction(VN):
    virtual_network_name = Arg(help='Virtual network name')


class AddVN(VNAction):
    description = 'Add virtual-network'
    external = Option(default=False,
                      action="store_true")
    shared = Option(default=False,
                    action="store_true")
    subnet = Option(action="append",
                    dest="subnets",
                    metavar="CIDR",
                    default=[],
                    help="Add subnet to VN")

    def __call__(self, project_fqname=None, virtual_network_name=None, external=False, shared=False, subnets=None):
        vn_fqname = '%s:%s' % (project_fqname, virtual_network_name)

        # fetch project to sync it from keystone if not already there
        project = Resource('project', fq_name=project_fqname, fetch=True)
        vn = Resource('virtual-network',
                      fq_name=vn_fqname,
                      parent=project,
                      router_external=external,
                      is_shared=shared)
        vn.save()

        if external:
            fip_pool = Resource('floating-ip-pool',
                                fq_name='%s:%s' % (vn_fqname, 'floating-ip-pool'),
                                parent_type='virtual-network',
                                parent_uuid=vn.uuid)
            fip_pool.save()

        cidrs = [netaddr.IPNetwork(cidr) for cidr in subnets]
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


class DelVN(VNAction):
    description = 'Delete virtual-network'

    def __call__(self, project_fqname=None, virtual_network_name=None):
        vn_fqname = '%s:%s' % (project_fqname, virtual_network_name)
        vn = Resource('virtual-network',
                      fq_name=vn_fqname,
                      fetch=True)
        if vn.get('router_external', False):
            try:
                fip_pool = Resource('floating-ip-pool',
                                    fq_name='%s:%s' % (vn_fqname, 'floating-ip-pool'),
                                    check=True)
                fip_pool.delete()
            except ResourceNotFound:
                pass
        vn.delete()


class ListVNs(VN):
    description = 'List virtual-networks'

    def __call__(self, project_fqname=None):
        project = Resource('project', fq_name=project_fqname, check=True)
        vns = Collection('virtual-network',
                         parent_uuid=project.uuid,
                         fetch=True, recursive=2)

        return json.dumps([{
            "virtual_network_name": vn.fq_name[-1],
            "project_fqname": str(FQName(vn.fq_name[0:-1])),
            "shared": vn.get('is_shared', False),
            "external": vn.get('router_external', False),
            "subnets": ['%s/%s' % (s['subnet']['ip_prefix'], s['subnet']['ip_prefix_len'])
                        for s in get_network_ipam_subnets(vn)]
        } for vn in vns], indent=2)

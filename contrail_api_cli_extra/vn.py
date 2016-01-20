# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.exceptions import CommandError

from .utils import network_type


class VN(Command):
    vn_parent_fqname = Arg('--parent-fqname',
                           required=True,
                           dest='vn_parent_fqname',
                           help='VN parent fqname (eg: default-domain:admin)')


class VNAction(VN):
    vn_name = Arg(help='Virtual network name')


class AddVN(VNAction):
    description = 'Add virtual-network'
    external = Arg('--external',
                   default=False,
                   action="store_true")
    shared = Arg('--shared',
                 default=False,
                 action="store_true")
    subnet = Arg('--subnet',
                 required=True,
                 type=network_type,
                 help='Subnet CIDR')

    def __call__(self, vn_parent_fqname=None, vn_name=None, external=False, shared=False, subnet=None):
        vn_fqname = '%s:%s' % (vn_parent_fqname, vn_name)

        project = Resource('project',
                           fq_name=vn_parent_fqname,
                           check_fq_name=True)

        ipam_ref = {
            "attr": {
                "ipam_subnets": [{
                    "subnet": {
                        "ip_prefix": text_type(subnet.network),
                        "ip_prefix_len": subnet.prefixlen
                    }
                }]
            },
            "to": ["default-domain", "default-project", "default-network-ipam"]
        }

        vn = Resource('virtual-network',
                      fq_name=vn_fqname,
                      router_external=external,
                      is_shared=shared,
                      network_ipam_refs=[ipam_ref],
                      parent_type='project',
                      parent_uuid=project.uuid)
        vn.save()

        if external:
            fip_pool = Resource('floating-ip-pool',
                                fq_name='%s:%s' % (vn_fqname, 'floating-ip-pool'),
                                parent_type='virtual-network',
                                parent_uuid=vn.uuid)
            fip_pool.save()


class DelVN(VNAction):
    description = 'Delete virtual-network'

    def __call__(self, vn_parent_fqname=None, vn_name=None):
        vn_fqname = '%s:%s' % (vn_parent_fqname, vn_name)
        try:
            vn = Resource('virtual-network',
                          fq_name=vn_fqname,
                          check_fq_name=True,
                          fetch=True)
            if vn.get('router_external', False):
                try:
                    fip_pool = Resource('floating-ip-pool',
                                        fq_name='%s:%s' % (vn_fqname, 'floating-ip-pool'),
                                        check_fq_name=True)
                    fip_pool.delete()
                except ValueError:
                    pass
            vn.delete()
        except ValueError as e:
            raise CommandError(text_type(e))


class ListVNs(VN):
    description = 'List virtual-networks'

    def __call__(self, vn_parent_fqname=None):
        project = Resource('project',
                           fq_name=vn_parent_fqname,
                           check_fq_name=True)

        vns = Collection('virtual-network',
                         parent_uuid=project.uuid,
                         fetch=True, recursive=2)

        def get_vn_subnet(vn):
            if 'network_ipam_refs' not in vn:
                return
            subnet = vn['network_ipam_refs'][0]['attr']['ipam_subnets'][0]['subnet']
            return '%s/%s' % (subnet['ip_prefix'], subnet['ip_prefix_len'])

        return json.dumps([{
            "vn_name": vn.fq_name[-1],
            "vn_parent_fqname": vn.fq_name[0:-1],
            "shared": vn.get('is_shared', False),
            "external": vn.get('router_external', False),
            "subnet": get_vn_subnet(vn)
        } for vn in vns], indent=2)

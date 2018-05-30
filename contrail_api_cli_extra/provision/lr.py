# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import uuid

from keystoneauth1.exceptions.http import Conflict

from contrail_api_cli.command import Command, Option, Arg
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.utils import FQName, printo
from contrail_api_cli.exceptions import ResourceNotFound

from common import get_network_ipam_subnets


class LR(Command):
    project_fqname = Option(required=True,
                            help='Project fqname (eg: default-domain:admin)')


class LRAction(LR):
    logical_router_name = Arg(help='Logical router name')


class AddLR(LRAction):
    description = 'Add logical-router'
    vn_fqname = Option(action='append',
                       dest='vn_fqnames',
                       default=[],
                       help='Virtual network fqnames to connect the LR to')

    def __call__(self, project_fqname=None, logical_router_name=None, vn_fqnames=None):
        lr_fqname = '%s:%s' % (project_fqname, logical_router_name)

        # fetch project to sync it from keystone if not already there
        project = Resource('project', fq_name=project_fqname, fetch=True)
        lr = Resource('logical-router',
                      fq_name=lr_fqname,
                      parent=project)
        lr.save()

        lr_vns = [vn.uuid for vmi in lr.refs.virtual_machine_interface
                  for vn in vmi.fetch().refs.virtual_network]

        for vn_fqname in vn_fqnames:
            try:
                vn = Resource('virtual-network', fq_name=vn_fqname, fetch=True)
            except ResourceNotFound:
                printo("VN %s not found, ignoring..." % vn_fqname)
                continue
            # VN is already attached to the LR
            if vn.uuid in lr_vns:
                continue
            # We use the first subnet we found.
            ipam_subnets = get_network_ipam_subnets(vn)
            if len(ipam_subnets) > 0:
                gateway = ipam_subnets[0]['default_gateway']
                subnet_uuid = ipam_subnets[0]['subnet_uuid']
            else:
                printo("%s has no subnets, ignoring..." % vn)
                continue
            vmi = Resource('virtual-machine-interface',
                           parent=project,
                           fq_name='%s:%s' % (project_fqname, uuid.uuid4()),
                           virtual_machine_interface_device_owner='neutron:loadbalancer')
            vmi.set_ref(vn)
            vmi.save()
            iip = Resource('instance-ip',
                           fq_name='%s' % uuid.uuid4(),
                           instance_ip_address=gateway,
                           subnet_uuid=subnet_uuid)
            iip.set_ref(vn)
            iip.set_ref(vmi)
            iip.save()
            lr.set_ref(vmi)
            lr.save()


class DelLR(LRAction):
    description = 'Delete logical-router'

    def __call__(self, project_fqname=None, logical_router_name=None, **kwargs):
        lr_fqname = '%s:%s' % (project_fqname, logical_router_name)
        lr = Resource('logical-router', fq_name=lr_fqname, fetch=True)
        for vmi in lr.refs.virtual_machine_interface:
            for iip in vmi.fetch().back_refs.instance_ip:
                iip.delete()
            vmi.remove_back_ref(lr)
            vmi.delete()
        lr.delete()


class ListLRs(LR):
    description = 'List logical-routers'

    def __call__(self, project_fqname=None):
        project = Resource('project', fq_name=project_fqname, check=True)
        lrs = Collection('logical-router',
                         parent_uuid=project.uuid,
                         fetch=True, recursive=2)

        return json.dumps([{
            "project_fqname": str(FQName(lr.fq_name[0:-1])),
            "logical_router_name": str(lr.fq_name[-1]),
            "vn_fqnames": [str(vn.fq_name) for vmi in lr.refs.virtual_machine_interface
                           for vn in vmi.fetch().refs.virtual_network],
        } for lr in lrs], indent=2)

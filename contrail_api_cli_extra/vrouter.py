# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource

from .utils import ip_type


class VRouter(Command):
    vrouter_name = Arg(help='Hostname of compute node')


class AddVRouter(VRouter):
    description = 'Add vrouter'
    vrouter_ip = Arg('--vrouter-ip',
                     help='IP of compute node',
                     type=ip_type,
                     required=True)
    vrouter_type = Arg('--vrouter-type',
                       help='vrouter type',
                       choices=['tor-service-mode', 'embedded'],
                       default=None)

    def __call__(self, vrouter_ip=None, vrouter_name=None, vrouter_type=None):

        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        vrouter = Resource('virtual-router',
                           fq_name='default-global-system-config:%s' % vrouter_name,
                           parent_type='global-system-config',
                           parent_uuid=global_config.uuid,
                           virtual_router_ip_address=vrouter_ip)
        if vrouter_type:
            vrouter['virtual_router_type'] = [vrouter_type]
        vrouter.save()


class DelVRouter(VRouter):
    description = 'Remove vrouter'

    def __call__(self, vrouter_name=None):
        vrouter = Resource('virtual-router',
                           fq_name='default-global-system-config:%s' % vrouter_name)
        vrouter.delete()

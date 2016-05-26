# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg, Option
from contrail_api_cli.resource import Resource, Collection

from ..utils import ip_type


class VRouter(Command):
    vrouter_name = Arg(help='Hostname of compute node')


class AddVRouter(VRouter):
    description = 'Add vrouter'
    vrouter_ip = Option(help='IP of compute node',
                        type=ip_type,
                        required=True)
    vrouter_type = Option(help='vrouter type',
                          choices=['tor-service-mode', 'embedded'],
                          default=None)

    def __call__(self, vrouter_ip=None, vrouter_name=None, vrouter_type=None):

        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config')
        vrouter = Resource('virtual-router',
                           fq_name='default-global-system-config:%s' % vrouter_name,
                           parent=global_config,
                           virtual_router_ip_address=vrouter_ip)
        if vrouter_type:
            vrouter['virtual_router_type'] = [vrouter_type]
        vrouter.save()


class DelVRouter(VRouter):
    description = 'Remove vrouter'

    def __call__(self, vrouter_name=None):
        vrouter = Resource('virtual-router',
                           fq_name='default-global-system-config:%s' % vrouter_name,
                           check=True)
        vrouter.delete()


class ListVRouter(Command):
    description = 'List vrouters'

    def __call__(self):
        vrouters = Collection('virtual-router',
                              fetch=True, recursive=2)
        return json.dumps([{'vrouter_name': vrouter.fq_name[-1],
                            'vrouter_ip': vrouter['virtual_router_ip_address'],
                            'vrouter_type': vrouter.get('virtual_router_type', [])}
                           for vrouter in vrouters], indent=2)

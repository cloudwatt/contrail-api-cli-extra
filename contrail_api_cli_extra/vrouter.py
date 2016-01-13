# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from keystoneclient.exceptions import HttpError

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError

from .utils import ip_type


class VRouter(Command):
    description = 'Add or remove vrouters'
    oper = Arg(help='Add or remove vrouter',
               choices=['add', 'del'])
    vrouter_name = Arg('--vrouter-name',
                       help='Hostname of compute node',
                       required=True)
    vrouter_ip = Arg('--vrouter-ip',
                     help='IP of compute node',
                     type=ip_type)
    vrouter_type = Arg('--vrouter-type',
                       help='vrouter type',
                       choices=['tor-service-mode', 'embedded'],
                       default=None)

    def __call__(self, oper=None, controllers=None, vrouter_ip=None,
                 vrouter_name=None, vrouter_type=None):

        if oper == 'add':
            if not vrouter_ip:
                raise CommandError('--vrouter-ip mandatory to add a vrouter')
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
            try:
                vrouter.save()
            except HttpError as e:
                raise CommandError(text_type(e))

        elif oper == 'del':
            try:
                vrouter = Resource('virtual-router',
                                   fq_name='default-global-system-config:%s' % vrouter_name,
                                   check_fq_name=True)
            except ValueError as e:
                raise CommandError(text_type(e))

            vrouter.delete()

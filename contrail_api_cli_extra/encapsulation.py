# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError, ResourceNotFound


class SetEncapsulation(Command):
    description = 'Set vrouters encapsulation modes'
    modes = Arg(nargs='+',
                help='List of encapsulations modes by priority',
                choices=['MPLSoUDP', 'MPLSoGRE', 'VXLAN'])

    def __call__(self, modes=None):
        if len(modes) > 3:
            raise CommandError('Too much modes provided')
        try:
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      fetch=True)
        except ResourceNotFound:
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config')
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      parent=global_config)

        vrouter_config['encapsulation_priorities'] = {
            'encapsulation': modes
        }
        vrouter_config.save()


class GetEncapsulation(Command):
    description = 'Get vrouters encapsulation modes'

    def __call__(self):
        try:
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      fetch=True)
            if 'encapsulation_priorities' in vrouter_config:
                return json.dumps({
                    "modes": vrouter_config['encapsulation_priorities'].get('encapsulation', [])
                })
        except ResourceNotFound:
            pass
        return json.dumps([])

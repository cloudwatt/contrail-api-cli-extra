# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import CommandError


class SetEncapsulation(Command):
    description = 'Set vrouters encapsulation modes'
    encaps = Arg(nargs='+',
                 help='List of encapsulations modes by priority',
                 choices=['MPLSoUDP', 'MPLSoGRE', 'VXLAN'])

    def __call__(self, encaps=None):
        if len(encaps) > 3:
            raise CommandError('Too much modes provided')
        try:
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      check_fq_name=True,
                                      fetch=True)
        except ValueError:
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config',
                                     check_fq_name=True)
            vrouter_config = Resource('global-vrouter-config',
                                      fq_name='default-global-system-config:default-global-vrouter-config',
                                      parent_uuid=global_config.uuid,
                                      parent_type='global-system-config')
            vrouter_config.save()

        vrouter_config['encapsulation_priorities'] = {
            'encapsulation': encaps
        }
        vrouter_config.save()

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource

from .utils import RouteTargetAction


class SetGlobalASN(Command):
    description = "Set the global ASN to the API server"
    asn = Arg(nargs='?',
              help="Autonomous System Number (default: %(default)s)",
              type=RouteTargetAction.asn_type,
              default=64512)

    def __call__(self, asn=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        global_config['autonomous_system'] = asn
        global_config.save()

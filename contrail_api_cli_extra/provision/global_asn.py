# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import RouteTargetAction


class SetGlobalASN(Command):
    description = "Set the global ASN to the API server"
    asn = Arg(nargs='?',
              help="Autonomous System Number (default: %(default)s)",
              type=RouteTargetAction.asn_type,
              default=64512)

    def __call__(self, asn=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check=True)
        global_config['autonomous_system'] = asn
        global_config.save()


class GetGlobalASN(Command):
    description = "Get global ASN"

    def __call__(self):
        try:
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config',
                                     fetch=True)
            if global_config.get('autonomous_system'):
                return json.dumps({
                    "asn": global_config.get('autonomous_system')
                })
        except ResourceNotFound:
            pass
        return json.dumps([])

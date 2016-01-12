# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import argparse
from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource


def asn_validator(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("Minimum AS number is 1")
    if value > 65534:
        raise argparse.ArgumentTypeError("Maximu AS number is 65534")
    return value


class SetGlobalASN(Command):
    description = "Set the global ASN to the API server"
    asn = Arg(nargs='?', help="Autonomous System Number (default: %(default)s)", type=asn_validator, default=64512)

    def __call__(self, asn=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        global_config['autonomous_system'] = asn
        global_config.save()

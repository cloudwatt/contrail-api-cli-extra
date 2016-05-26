# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Option, Arg
from contrail_api_cli.resource import Resource, Collection


class SAS(Command):
    appliance_set_name = Arg(help='name')


class AddSAS(SAS):
    description = 'Add service appliance set'
    driver = Option(required=True,
                    help='driver python module path')

    def __call__(self, appliance_set_name=None, driver=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config')
        sas = Resource('service-appliance-set',
                       fq_name='default-global-system-config:%s' % appliance_set_name,
                       parent=global_config,
                       service_appliance_driver=driver)
        sas.save()


class DelSAS(SAS):
    description = 'Del service appliance set'

    def __call__(self, appliance_set_name=None):
        sas = Resource('service-appliance-set',
                       fq_name='default-global-system-config:%s' % appliance_set_name,
                       check=True)
        sas.delete()


class ListSAS(Command):
    description = 'List service appliance sets'

    def __call__(self):
        sass = Collection('service-appliance-set',
                          fetch=True, recursive=2)
        return json.dumps([{'appliance_set_name': sas.fq_name[-1],
                            'driver': sas['service_appliance_driver']}
                          for sas in sass if 'service_appliance_driver' in sas], indent=2)

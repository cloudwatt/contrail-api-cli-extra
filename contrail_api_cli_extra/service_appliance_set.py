# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource


class SAS(Command):
    appliance_set_name = Arg(help='name')


class AddSAS(SAS):
    description = 'Add ServiceApplianceSet'
    driver = Arg('--driver',
                 required=True,
                 help='driver python module path')

    def __call__(self, appliance_set_name=None, driver=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config',
                                 check_fq_name=True)
        sas = Resource('service-appliance-set',
                       fq_name='default-global-system-config:%s' % appliance_set_name)
        sas['parent_type'] = 'global-system-config'
        sas['parent_uuid'] = global_config.uuid
        sas['service_appliance_driver'] = driver
        sas.save()


class DelSAS(SAS):
    description = 'Del ServiceApplianceSet'

    def __call__(self, appliance_set_name=None):
        sas = Resource('service-appliance-set',
                       fq_name='default-global-system-config:%s' % appliance_set_name)
        sas.delete()

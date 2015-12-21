from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.resource import Resource


class AddSAS(Command):
    description = 'Add ServiceApplianceSet to the API server'
    appliance_set_name = Arg(help='name')
    driver = Arg(help='driver python module path')

    def __call__(self, appliance_set_name=None, driver=None):
        global_config = Resource('global-system-config',
                                 fq_name='default-global-system-config')
        sas = Resource('service-appliance-set',
                       fq_name='default-global-system-config:%s' % appliance_set_name,
                       check_fq_name=False)
        sas['parent_type'] = 'global-system-config'
        sas['parent_uuid'] = global_config.uuid
        sas['service_appliance_driver'] = driver
        sas.save()

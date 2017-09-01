# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.resource import Collection
from contrail_api_cli.utils import printo
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.schema import require_schema
from contrail_api_cli.command import Command


class MigrateLB22132(Command):
    """Command to migrate LB created in 2.21 to 3.2.

    In 2.21 the admin_state flag didn't matter, but in 3.2 if it is
    not set to True the haproxy config file will not be generated.

    This command set admin_state to True for all lb-pools, lb-members, lb-vips, lb-hms.
    """
    description = "Migrate LBs from 2.21 to 3.2"

    @require_schema(version="2.21")
    def __call__(self, **kwargs):
        resources_types = ('loadbalancer-pool', 'loadbalancer-member',
                           'loadbalancer-healthmonitor', 'virtual-ip')

        for rtype in resources_types:
            printo("Migrating %s" % rtype)
            for r in Collection(rtype, fetch=True):
                try:
                    r.fetch()['%s_properties' % rtype.replace('-', '_')]['admin_state'] = True
                    r.save()
                except ResourceNotFound:
                    continue

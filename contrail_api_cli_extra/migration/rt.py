# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import printo
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.schema import require_schema

from ..utils import CheckCommand, PathCommand


class MigrateRT22132(CheckCommand, PathCommand):
    """Command to migrate custom RTs from 2.21 to 3.2.

    In 3.2 we can benefit from new VN properties that allows to define
    the list of RTs the VNs must import/export.
    """
    description = "Migrate custom RTs from 2.21 to 3.2"

    @property
    def resource_type(self):
        return 'route-target'

    @require_schema(version='3.2')
    def __call__(self, **kwargs):
        super(MigrateRT22132, self).__call__(**kwargs)

        config = Resource('global-system-config', fq_name='default-global-system-config', fetch=True)
        asn = config.autonomous_system

        for rt in self.resources:
            if not text_type(asn) == rt.fq_name[1]:
                printo('Found custom RT %s to migrate' % rt.fq_name)
                if self.check:
                    continue
                for ri in rt.fetch().back_refs.routing_instance:
                    mode = ri['attr']['import_export']
                    try:
                        vn = ri.fetch().parent.fetch()
                    except ResourceNotFound:
                        printo("Can't find VN for RI %s" % ri)
                        continue
                    if mode is None:
                        prop = 'route_target_list'
                    else:
                        prop = mode + '_route_target_list'
                    if prop not in vn:
                        vn[prop] = {'route_target': []}
                    if text_type(rt.fq_name) in vn[prop]['route_target']:
                        continue
                    printo('Adding %s to VN (%s) %s' % (rt.fq_name, vn.fq_name, prop))
                    if not self.dry_run:
                        vn[prop]['route_target'].append(text_type(rt.fq_name))
                        vn.save()

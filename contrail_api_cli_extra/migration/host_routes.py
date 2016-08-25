# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.resource import Resource
from contrail_api_cli.utils import printo, to_json, highlight_json
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import CheckCommand, PathCommand

NEUTRON_IRT_PREFIX = "NEUTRON_IFACE_RT_"
NEUTRON_RT_PREFIX = "NEUTRON_RT_"


class MigrateHostRoutes(CheckCommand, PathCommand):
    """Command to migrate host-route implementation based on
    interface-route-tables to route-tables (V3 plugin)::

        contrail-api-cli --ns contrail_api_cli.migration migrate-host-routes [interface-route-table/uuid]
    """
    description = "Migrate host-routes to new V3 implementation"

    @property
    def resource_type(self):
        return 'interface-route-table'

    def _get_rt(self, fq_name, parent):
        rt = Resource('route-table', fq_name=fq_name, parent=parent)
        try:
            rt.fetch()
        except ResourceNotFound:
            rt['routes'] = {'route': []}
            if not self.dry_run:
                rt.save()
        return rt

    def _migrate(self, irt):
        irt.fetch()

        subnet_uuid, vmi_uuid = irt['name'].replace(NEUTRON_IRT_PREFIX, '').split('_')
        ip = None

        for vmi in irt.back_refs.virtual_machine_interface:
            if ip is not None:
                break
            if vmi.uuid == vmi_uuid:
                vmi.fetch()
                for iip in vmi.back_refs.instance_ip:
                    iip.fetch()
                    if iip.get('subnet_uuid', subnet_uuid) == subnet_uuid:
                        ip = iip['instance_ip_address']
                        break

        if ip is None:
            printo("Failed finding VMI IP, probably no VMI attached to IRT.")
            return

        rt_fq_name = irt.fq_name[0:2] + [NEUTRON_RT_PREFIX + subnet_uuid]
        rt = self._get_rt(rt_fq_name, irt.parent)

        for route in irt.get('interface_route_table_routes', {}).get('route', []):
            route['next_hop'] = ip
            route['next_hop_type'] = 'ip-address'
            rt['routes']['route'].append(route)

        if not self.dry_run:
            rt.save()
        printo("Updated RT %s with :" % rt.fq_name)
        printo(highlight_json(to_json(rt['routes']['route'])))
        if not self.dry_run:
            for vmi in irt.back_refs.virtual_machine_interface:
                irt.remove_back_ref(vmi)
            irt.delete()
        printo("Deleted IRT %s" % irt.fq_name)

    def __call__(self, **kwargs):
        super(MigrateHostRoutes, self).__call__(**kwargs)
        for irt in self.resources:
            if irt.fq_name[-1].startswith(NEUTRON_IRT_PREFIX):
                printo("Found IRT to migrate %s" % irt.fq_name)
                if not self.check:
                    self._migrate(irt)

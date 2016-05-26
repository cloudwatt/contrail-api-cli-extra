# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from contrail_api_cli.command import Command, Option
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.resource import Resource

from ..utils import RouteTargetAction


class RouteTarget(Command):
    virtual_network_fqname = Option(required=True,
                                    help="Virtual network FQName")

    def __call__(self, virtual_network_fqname=None):
        self.vn = Resource('virtual-network', fq_name=virtual_network_fqname,
                           fetch=True)


class RouteTargetAction(RouteTarget):
    route_target_list = Option(nargs='+',
                               action=RouteTargetAction,
                               help="Imported and exported route target \
                                     '<ASN>:<route target number>' (default: %(default)s)",
                               default=[])
    import_route_target_list = Option(nargs='+',
                                      action=RouteTargetAction,
                                      help="Imported route target '<ASN>:<route target number>' (default: %(default)s) \
                                            /!\\ Not supported until Contrail 3.0",
                                      default=[])
    export_route_target_list = Option(nargs='+',
                                      action=RouteTargetAction,
                                      help="Exported route target '<ASN>:<route target number>' (default: %(default)s) \
                                            /!\\ Not supported until Contrail 3.0",
                                      default=[])

    def __call__(self, virtual_network_fqname=None, route_target_list=None,
                 import_route_target_list=None, export_route_target_list=None):
        super(RouteTargetAction, self).__call__(virtual_network_fqname)


class SetRouteTargets(RouteTargetAction):
    description = "Set route targets associated to a virtual network"

    def __call__(self, virtual_network_fqname=None, route_target_list=None,
                 import_route_target_list=None, export_route_target_list=None):
        super(SetRouteTargets, self).__call__(virtual_network_fqname,
                                              route_target_list,
                                              import_route_target_list,
                                              export_route_target_list)

        modified = False
        for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
            input_rt_list = eval(rt_policy)
            if not input_rt_list:
                continue
            if not rt_policy in self.vn:
                self.vn[rt_policy] = {}
            self.vn[rt_policy]['route_target'] = input_rt_list
            modified = True

        if modified:
            self.vn.save()


class GetRouteTargets(RouteTarget):
    description = 'Get route targets'

    def __call__(self, virtual_network_fqname=None):
        try:
            super(GetRouteTargets, self).__call__(virtual_network_fqname)
            result = {}
            for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
                if rt_policy in self.vn and 'route_target' in self.vn[rt_policy]:
                    result[rt_policy] = self.vn[rt_policy]['route_target']
                else:
                    result[rt_policy] = []
            if result:
                return json.dumps(result, indent=2)
        except ResourceNotFound:
            pass
        return json.dumps([])

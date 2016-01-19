# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type
import json

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.resource import Resource

from .utils import RouteTargetAction


class RouteTarget(Command):
    virtual_network_fqname = Arg('--virtual-network-fqname',
                                 help="Virtual network FQName")

    def __call__(self, virtual_network_fqname=None):
        try:
            self.vn = Resource('virtual-network', fq_name=virtual_network_fqname,
                               check_fq_name=True, fetch=True)
        except ValueError as e:
            raise CommandError(text_type(e))


class RouteTargetAction(RouteTarget):
    route_target_list = Arg('--route-target-list',
                            nargs='+',
                            action=RouteTargetAction,
                            help="Imported and exported route target '<ASN>:<route target number>' (default: %(default)s)",
                            default=[])
    import_route_target_list = Arg('--import-route-target-list',
                                   nargs='+',
                                   action=RouteTargetAction,
                                   help="Imported route target '<ASN>:<route target number>' (default: %(default)s) \
                                         /!\\ Not supported until Contrail 3.0",
                                   default=[])
    export_route_target_list = Arg('--export-route-target-list',
                                   nargs='+',
                                   action=RouteTargetAction,
                                   help="Exported route target '<ASN>:<route target number>' (default: %(default)s) \
                                         /!\\ Not supported until Contrail 3.0",
                                   default=[])

    def __call__(self, virtual_network_fqname=None, route_target_list=None,
                 import_route_target_list=None, export_route_target_list=None):
        super(RouteTargetAction, self).__call__(virtual_network_fqname)
        try:
            self.vn = Resource('virtual-network', fq_name=virtual_network_fqname,
                               check_fq_name=True, fetch=True)
        except ValueError as e:
            raise CommandError(text_type(e))


class AddRouteTarget(RouteTargetAction):
    description = "Add route targets associated to a virtual network"

    def __call__(self, virtual_network_fqname=None, route_target_list=None,
                 import_route_target_list=None, export_route_target_list=None):
        super(AddRouteTarget, self).__call__(virtual_network_fqname,
                                             route_target_list,
                                             import_route_target_list,
                                             export_route_target_list)

        modified = False
        for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
            input_rt_list = eval(rt_policy)
            if not input_rt_list:
                continue

            actual_rt_list = []
            if rt_policy in self.vn and 'route_target' in self.vn[rt_policy]:
                actual_rt_list = self.vn[rt_policy]['route_target']
            rt_to_add = list(set(input_rt_list) - set(actual_rt_list))
            if not rt_to_add:
                continue
            if rt_policy in self.vn and 'route_target' in self.vn[rt_policy]:
                self.vn[rt_policy]['route_target'].extend(rt_to_add)
            else:
                self.vn[rt_policy] = {'route_target': rt_to_add}
            modified = True

        if modified:
            self.vn.save()
        else:
            raise CommandError('All route target lists are already up-to-date')


class DelRouteTarget(RouteTargetAction):
    description = "Delete route targets associated to a virtual network"

    def __call__(self, oper=None, virtual_network_fqname=None, route_target_list=None,
                 import_route_target_list=None, export_route_target_list=None):
        super(DelRouteTarget, self).__call__(virtual_network_fqname,
                                             route_target_list,
                                             import_route_target_list,
                                             export_route_target_list)

        modified = False
        for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
            input_rt_list = eval(rt_policy)
            if not input_rt_list:
                continue

            if rt_policy in self.vn and 'route_target' in self.vn[rt_policy]:
                actual_rt_list = self.vn[rt_policy]['route_target']
                rt_to_remove = list(set(actual_rt_list) & set(input_rt_list))
                if rt_to_remove:
                    self.vn[rt_policy]['route_target'] = [rt for rt in actual_rt_list if rt not in rt_to_remove]
                    modified = True

        if modified:
            self.vn.save()
        else:
            raise CommandError('All route target lists are already up-to-date')


class ListRouteTarget(RouteTarget):
    description = 'List route targets'

    def __call__(self, virtual_network_fqname=None):
        try:
            super(ListRouteTarget, self).__call__(virtual_network_fqname)
            result = {}
            for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
                if rt_policy in self.vn and 'route_target' in self.vn[rt_policy]:
                    result[rt_policy] = self.vn[rt_policy]['route_target']
            return json.dumps(result, indent=2)
        except CommandError:
            return json.dumps([])

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.commands import Command, Arg
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.resource import Resource

from .utils import RouteTargetAction


class RouteTarget(Command):
    description = "Set route target to a virtual network"
    oper = Arg(help='Add or remove route target',
               choices=['add', 'del'])
    virtual_network_fqname = Arg('--virtual-network-fqname',
                                 help="Virtual network FQName")
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

    def __call__(self, oper=None, virtual_network_fqname=None, route_target_list=[],
                 import_route_target_list=[], export_route_target_list=[]):
        try:
            vn = Resource('virtual-network', fq_name=virtual_network_fqname,
                          check_fq_name=True, fetch=True)
        except ValueError:
            raise CommandError("Virtual network %s doesn't exists" %
                               router_fq_name)

        modified = False
        for rt_policy in ['route_target_list', 'import_route_target_list', 'export_route_target_list']:
            input_rt_list = eval(rt_policy)
            if not input_rt_list:
                continue

            if oper == 'add':
                actual_rt_list = []
                if rt_policy in vn and 'route_target' in vn[rt_policy]:
                    actual_rt_list = vn[rt_policy]['route_target']
                rt_to_add = list(set(input_rt_list) - set(actual_rt_list))
                if not rt_to_add:
                    continue
                if rt_policy in vn and 'route_target' in vn[rt_policy]:
                    vn[rt_policy]['route_target'].extend(rt_to_add)
                else:
                    vn[rt_policy] = {'route_target': rt_to_add}
                modified = True
            elif oper == 'del' and rt_policy in vn and 'route_target' in vn[rt_policy]:
                actual_rt_list = vn[rt_policy]['route_target']
                rt_to_remove = list(set(actual_rt_list) & set(input_rt_list))
                if rt_to_remove:
                    vn[rt_policy]['route_target'] = [rt for rt in actual_rt_list if rt not in rt_to_remove]
                    modified = True

        if modified:
            vn.save()
        else:
            raise CommandError('All route target lists are already up-to-date')

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Option, Arg, Command, expand_paths
from contrail_api_cli.utils import printo, format_table
from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.schema import require_schema


mode_map = {
    'import': 'import_route_target_list',
    'export': 'export_route_target_list',
    'import_export': 'route_target_list',
}


class ManageRT(Command):
    """Command to manage VN custom RTs
    """
    description = "Manage VN custom RTs"

    path = Arg(help="path", metavar='path',
               complete="resources:virtual-network:path")
    action = Option('-a',
                    choices=['add', 'delete', 'show'],
                    default='show',
                    help="Type of action (default: %(default)s)")
    mode = Option('-m',
                  choices=['import', 'export', 'import_export'],
                  default='import_export',
                  help="Specify type of RT (default: %(default)s)")
    name = Option(help="Name of the RT to create/delete (eg: target:219.0.0.1:1)")

    @property
    def resource_type(self):
        return 'virtual-network'

    def show(self, vn):
        vns = [vn.uuid]
        import_export_list = vn.get('route_target_list', {}).get('route_target', [])
        import_list = vn.get('import_route_target_list', {}).get('route_target', [])
        export_list = vn.get('export_route_target_list', {}).get('route_target', [])

        table = [
            ["VN", "import/export", "import", "export"],
        ]

        def add_row(vn, import_export_rt, import_rt, export_rt):
            table.append([
                vn if vn else "",
                import_export_rt if import_export_rt else "",
                import_rt if import_rt else "",
                export_rt if export_rt else ""
            ])

        map(add_row, vns, import_export_list, import_list, export_list)
        printo(format_table(table))

    def add(self, vn, mode, name):
        prop = mode_map[mode]
        if prop not in vn:
            vn[prop] = {'route_target': []}
        if name in vn[prop]['route_target']:
            raise CommandError('RT %s already added' % name)
        vn[prop]['route_target'].append(name)
        vn.save()
        printo('RT %s added to VN' % name)

    def delete(self, vn, mode, name):
        prop = mode_map[mode]
        rt_list = vn.get(prop, {}).get('route_target', [])
        try:
            rt_list.remove(name)
        except ValueError:
            printo('RT %s not found on VN' % name)
            return
        vn[prop]['route_target'] = rt_list
        vn.save()
        printo('RT %s deleted from VN' % name)

    @require_schema(version='>= 3')
    def __call__(self, path=None, mode=None, action=None, name=None):
        if not action == 'show' and not name:
            raise CommandError("--name is required")

        vn = expand_paths([path], predicate=lambda r: r.type == 'virtual-network')[0]
        vn.fetch()

        if action == 'show':
            self.show(vn)
        elif action == 'add':
            self.add(vn, mode, name)
        elif action == 'delete':
            self.delete(vn, mode, name)

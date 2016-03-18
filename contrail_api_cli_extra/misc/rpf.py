from contrail_api_cli.command import Command, Arg, expand_paths


class RPF(Command):
    description = 'enable/disable RPF on network'
    on = Arg('--on',
             action='store_true',
             help='Enable RPF')
    off = Arg('--off',
              action='store_true',
              help='Disable RPF')
    paths = Arg(nargs='*',
                metavar='vn',
                help='List of VN')

    def __call__(self, paths=None, on=False, off=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: r.type == 'virtual-network')
        for vn in resources:
            vn.fetch()
            if 'virtual_network_properties' not in vn:
                vn['virtual_network_properties'] = {
                    "allow_transit": None,
                    "forwarding_mode": None,
                    "network_id": vn['virtual_network_id'],
                    "vxlan_network_identifier": None
                }
            if off:
                vn['virtual_network_properties']['rpf'] = 'disable'
                vn.save()
            elif on:
                vn['virtual_network_properties']['rpf'] = None
                vn.save()
            else:
                return 'on' if vn['virtual_network_properties']['rpf'] is None else 'off'

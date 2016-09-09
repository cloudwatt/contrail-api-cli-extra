# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.command import Option
from contrail_api_cli.utils import printo

from ..utils import PathCommand


class RPF(PathCommand):
    """Simple command to enable or disable RPF (Reverse Path Forwarding) on a VN.

    To check if RPF is enabled or not run::

        contrail-api-cli rpf virtual-network/uuid

    To enable of disable RPF add ``--on`` or ``--off`` options.
    """
    description = 'enable/disable RPF on network'
    on = Option(action='store_true',
                help='Enable RPF')
    off = Option(action='store_true',
                 help='Disable RPF')

    @property
    def resource_type(self):
        return 'virtual-network'

    def __call__(self, on=False, off=False, **kwargs):
        super(RPF, self).__call__(**kwargs)
        for vn in self.resources:
            vn.fetch()
            if 'virtual_network_properties' not in vn:
                vn['virtual_network_properties'] = {
                    "allow_transit": None,
                    "forwarding_mode": None,
                    "network_id": vn.get('virtual_network_id', None),
                    "vxlan_network_identifier": None
                }
            if off:
                vn['virtual_network_properties']['rpf'] = 'disable'
                vn.save()
            elif on:
                vn['virtual_network_properties']['rpf'] = None
                vn.save()
            else:
                status = 'on' if vn['virtual_network_properties'].get('rpf') is None else 'off'
                printo("%s : %s" % (self.current_path(vn), status))

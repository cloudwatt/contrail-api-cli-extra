# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import uuid
from six import text_type

from contrail_api_cli.schema import require_schema
from contrail_api_cli.command import Command, Arg
from contrail_api_cli.context import Context


def _to_bgpvpn(info):
    bgpvpn = {
        'id': "",
        'import_targets': [],
        'export_targets': [],
        'route_targets': [],
        'type': 'l3',
        'route_distinguishers': [],
        'tenant_id': "",
        'name': "",
    }
    if info['mode'] == 'import_export':
        bgpvpn['route_targets'].append(info['rt'].split(':', 1)[1])
    else:
        bgpvpn['%s_targets' % ['mode']].append(info['rt'].split(':')[1])

    for (project, vns) in info['assocs'].items():
        bgpvpn_ = bgpvpn.copy()
        bgpvpn_['id'] = text_type(uuid.uuid4())
        bgpvpn_['tenant_id'] = project.replace('-', '')
        Context().session.add_kv_store(bgpvpn_['id'], json.dumps(bgpvpn_))
        for vn in vns:
            bgpvpn_net_assoc = {
                'network_id': vn,
                'tenant_id': bgpvpn_['tenant_id'],
                'bgpvpn_id': bgpvpn_['id'],
                'id': text_type(uuid.uuid4()),
            }
            Context().session.add_kv_store(bgpvpn_net_assoc['id'], json.dumps(bgpvpn_net_assoc))


class MigrateToBGPVPNLegacy(Command):
    """Command to migrate custom RTs to BGPVPN API.

    This is for the legacy opencontrail bgpvpn driver.

    First make a gremlin dump and extract custom RTs associations with
    `bgpvpn.groovy` script.
    """
    description = "Migrate custom RTs to BGPVPN API"
    input_file = Arg()

    @require_schema(version="3.2")
    def __call__(self, input_file=None):
        with open(input_file) as f:
            lines = f.readlines()
        for line in lines:
            _to_bgpvpn(json.loads(line))

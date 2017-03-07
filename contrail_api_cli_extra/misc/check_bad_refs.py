# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from pycassa import ConnectionPool, ColumnFamily

from contrail_api_cli.command import Command, Option, Arg
from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceNotFound
from contrail_api_cli.utils import printo, highlight_json, parallel_map

from ..utils import server_type


class PropertiesEncoder(json.JSONEncoder):

    def encode(self, o):
        for k, v in o.items():
            o[k] = json.loads(v)
        return json.JSONEncoder.encode(self, o)


class CheckBadRefs(Command):
    """Check for bad references.
    """
    description = "Check for broken references"
    uuids = Arg(help="Check specific uuids",
                nargs="*", default=[])
    cassandra_servers = Option(help="Cassandra server list' (default: %(default)s)",
                               nargs='+',
                               type=server_type,
                               default=['localhost:9160'])

    def _props_to_json(self, values):
        if self.is_piped:
            return json.dumps(values, cls=PropertiesEncoder, indent=4)
        return highlight_json(json.dumps(values, cls=PropertiesEncoder, indent=4))

    def _get_current_resource(self, uuid, values):
        try:
            r_type = json.loads(values['type']).replace('_', '-')
            return Resource(r_type, uuid=uuid)
        except KeyError:
            printo("[%s] incomplete, no type" % uuid)
            return False

    def _check_ref(self, ref, uuid):
        _, ref_type, ref_uuid = ref.split(':')
        try:
            Resource(ref_type.replace('_', '-'), uuid=ref_uuid, check=True)
            return False
        except ResourceNotFound:
            printo("[%s] broken ref to missing %s/%s" % (uuid, ref_type.replace('_', '-'), ref_uuid))
            return True

    def _check_resource_refs(self, uuid, values):
        ref_attrs = ['ref:', 'backref:', 'children:']
        for key, value in values.items():
            to_check = []
            for attr in ref_attrs:
                if key.startswith(attr):
                    to_check.append(key)
        results = parallel_map(self._check_ref, to_check, args=(uuid,), workers=20)
        return any(results)

    def __call__(self, uuids=None, cassandra_servers=None):
        pool = ConnectionPool('config_db_uuid', server_list=cassandra_servers)
        uuid_cf = ColumnFamily(pool, 'obj_uuid_table')
        if uuids:
            def uuids():
                for uuid in uuids:
                    yield uuid
        else:
            def uuids():
                for k, v in uuid_cf.get_range(column_count=1, filter_empty=True):
                    yield k

        for uuid in uuids():
            values = dict(uuid_cf.xget(uuid))
            res = self._get_current_resource(uuid, values)
            bad_refs = self._check_resource_refs(uuid, values)
            if not res or bad_refs:
                printo(self._props_to_json(values))

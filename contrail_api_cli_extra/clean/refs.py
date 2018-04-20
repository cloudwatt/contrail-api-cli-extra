# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sys import exit
import argparse

from pycassa import ConnectionPool, ColumnFamily

from contrail_api_cli.command import Option, Arg
from contrail_api_cli.utils import printo

from ..utils import server_type, CheckCommand


class CleanRefs(CheckCommand):
    """Clean references in Contrail DB.

    Broken refs can be found with gremlin.

    The command expects a list of ids where the first ID is a valid resource
    while the second is a missing resource still referenced.

    For example::

        > g.V().hasLabel('routing_instance').not(has('_missing')).in().hasLabel('virtual_machine_interface').has('_missing').path().by(id).unfold().fold()
        [ri_id, vmi_id, ri_id, vmi_id, ...]

    This return a list of broken refs between RIs and VMIs where VMIs don't exists or are incomplete.

    We can clean then by running::

        contrail-api-cli --ns contrail_api_cli.clean clean-refs --ref-type backref --target-type virtual_machine_interface ri_id vmi_id ri_id vmi_id ...

    Or directly from a file::

         contrail-api-cli --ns contrail_api_cli.clean clean-refs --ref-type backref --target-type virtual_machine_interface --resources-file file

    Other examples::

        # RIs without any parent VN
        > g.V().hasLabel('routing_instance').not(has('_missing')).out('parent').hasLabel('virtual_network').has('_missing').path().by(id).unfold().fold()
        > contrail-api-cli clean-refs --ref-type parent --target-type virtual_network ...

        # ACLs without any SG
        > g.V().hasLabel('access_control_list').not(has('_missing')).out('parent').hasLabel('security_group').has('_missing').path().by(id).unfold().fold()
        > contrail-api-cli clean-refs --ref-type parent --target-type security_group ...

    """
    description = "Clean for broken references"
    paths = Arg(help="list of refs [src, tgt, src, tgt, ...]",
                nargs="*", default=[])
    resources_file = Option(help="file containing resource ids",
                            nargs="?",
                            type=argparse.FileType('r'))
    ref_type = Option(help="ref type to clean",
                      choices=["ref", "backref", "children", "parent"],
                      required=True)
    target_type = Option(help="resource type of the target",
                         required=True)

    cassandra_servers = Option(help="cassandra server list' (default: %(default)s)",
                               nargs='+',
                               type=server_type,
                               default=['localhost:9160'])

    def _remove_refs(self, paths):
        if len(paths) == 0:
            return
        source, target = paths[:2]
        # when the parent doesn't exists anymore,
        # we don't need to keep the source
        if not self.check:
            if self.ref_type == "parent":
                self.uuid_cf.remove(target)
                self.uuid_cf.remove(source)
            else:
                self.uuid_cf.remove(target)
                self.uuid_cf.remove(source, columns=['%s:%s:%s' % (self.ref_type, self.target_type, target)])

        printo("[%s -> %s] deleted" % (source, target))
        self._remove_refs(paths[2:])

    def _read_file(self, resources_file):
        paths = []
        for l in resources_file:
            paths = paths + l.split()
        return paths

    def __call__(self, paths=None, resources_file=None, ref_type=None, target_type=None, cassandra_servers=None, **kwargs):
        super(CleanRefs, self).__call__(**kwargs)
        pool = ConnectionPool('config_db_uuid', server_list=cassandra_servers)
        self.uuid_cf = ColumnFamily(pool, 'obj_uuid_table')
        self.ref_type = ref_type
        self.target_type = target_type
        if resources_file is not None :
            paths = paths + self._read_file(resources_file)

        self._remove_refs(paths)

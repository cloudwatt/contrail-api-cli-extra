# -*- coding: utf-8 -*-
from pycassa import ConnectionPool, ColumnFamily, ConsistencyLevel
from contrail_api_cli.utils import printo
from ..utils import CassandraCommand, CheckCommand, ConfirmCommand

class CleanObjMandatoryFields(CassandraCommand, CheckCommand, ConfirmCommand):
    """Remove ressources with missing mandatory fields
    
    If an object has a missing parameter included in
    "OBJ_MANDATORY_COLUMNS" the object is deleted from
    "obj_uuid_table"
    """
    description = "Clean obj with missing mandatory fields"

    OBJ_MANDATORY_COLUMNS = ['type', 'fq_name', 'prop:id_perms'] 

    def __call__(self, **kwargs):
        super(CleanObjMandatoryFields, self).__call__(**kwargs)
        pool = ConnectionPool('config_db_uuid', server_list=self.cassandra_servers)
        self.obj_uuid_cf = ColumnFamily(pool, "obj_uuid_table",\
                read_consistency_level=ConsistencyLevel.QUORUM)

        for obj_uuid, _ in self.obj_uuid_cf.get_range(column_count=1):
            cols = dict(self.obj_uuid_cf.xget(obj_uuid))
            missing_cols = set(self.OBJ_MANDATORY_COLUMNS) - set(cols.keys())
            if not missing_cols:
                continue
            printo("Found object %s with missing fields [%s]" % (obj_uuid,
                ", ".join(missing_cols)))
            if self.check or self.dry_run:
                printo("Would remove object %s" % obj_uuid)
            else:
                printo("Removing object %s" % obj_uuid)
                self.obj_uuid_cf.remove(obj_uuid)

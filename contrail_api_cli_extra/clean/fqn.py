# -*- coding: utf-8 -*-
from pycassa import ConnectionPool, ColumnFamily

from contrail_api_cli.utils import printo

from ..utils import CheckCommand, CassandraCommand


class CleanFQN(CassandraCommand, CheckCommand):
    """Remove stale entries in obj_fq_name_table.

    Check for each FQN in obj_fq_name_table if a related UUID exists
    in obj_uuid_table, if not the FQN is considered as stale and so
    is removed from the DB.
    """
    description = "Clean for stale fq_names"

    def _process_fqn(self, fqn, obj_type):
        """Parse fqn entry from obj_fq_name_table and remove it if
        related UUID does not exist in obj_uuid_table.

        
        :param fqn: FQN to check.
        :type fqn: string
        :param obj_type: type of object the FQN refers to.
        :type obj_type: string
        """
        # Extract object uuid from column
        obj_uuid = fqn.split(":")[-1]

        # If no entry match the query, the number of columns should be 0 
        if not self.uuid_cf.get_count(obj_uuid):
            printo("Object %s %s will be removed from the db." % (obj_type, fqn))
            if not self.check and not self.dry_run:
                self.fqname_cf.remove(key=obj_type, columns=[fqn])

    def __call__(self, **kwargs):
        super(CleanFQN, self).__call__(**kwargs)
        pool = ConnectionPool('config_db_uuid', server_list=self.cassandra_servers)
        self.fqname_cf = ColumnFamily(pool, 'obj_fq_name_table')
        self.uuid_cf = ColumnFamily(pool, 'obj_uuid_table')
        
        fqn_rows = self.fqname_cf.get_range()

        for fqn_row in fqn_rows:
            obj_type = fqn_row[0]
            fqns = fqn_row[1].keys()
            for fqn in fqns:
                self._process_fqn(fqn, obj_type)

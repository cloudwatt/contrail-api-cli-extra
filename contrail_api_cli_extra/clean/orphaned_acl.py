# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from pycassa import ConnectionPool, ColumnFamily
from urllib import unquote_plus

from contrail_api_cli.command import Command, Option
from contrail_api_cli.resource import Resource, Collection
from contrail_api_cli.exceptions import ResourceNotFound

from ..utils import server_type


logger = logging.getLogger(__name__)


def decode_string(dec_str, encoding='utf-8'):
    # Decode the string previously encoded using urllib.quote_plus.
    # if dec_str = 'net%C3%A9%C3%B9' (unicode/str)
    # return 'neté' (unicode)
    ret_dec_str = dec_str
    try:
        if type(ret_dec_str) is unicode:
            ret_dec_str = str(ret_dec_str)
        ret_dec_str = unquote_plus(ret_dec_str)
        return ret_dec_str.decode(encoding)
    except Exception:
        return dec_str


class OrphanedACL(Command):
    """Removes stale ACLs.

    ACL is considered as stale if it has no parent::

        contrail-api-cli --ns contrail_api_cli.ns clean-orphaned-acl --cassandra-servers <ip1> <ip2>

    .. note::

        Because of an API server limitation the ACLs are removed directly from the cassandra cluster.
        Thus, the cassandra cluster nodes IPs must be provided.
    """
    description = "Clean all ACLs that don't have any parent"
    force = Option('-f',
                   help="Delete orphan ACL (default: %(default)s)",
                   default=False,
                   action="store_true")
    parent_type = Option(help="Parent type the ACL should have (default: %(default)s)",
                         choices=['security-group', 'virtual-network'],
                         default='security-group')
    cassandra_servers = Option(help="Cassandra server list' (default: %(default)s)",
                               nargs='+',
                               type=server_type,
                               default=['localhost:9160'])

    def __call__(self, force=False, parent_type=None, cassandra_servers=None):
        valid_acl = []
        parents = Collection(parent_type, fetch=True, recursive=2)
        for parent in parents:
            if 'access_control_lists' in parent.keys():
                valid_acl += [acl['uuid'] for acl in parent['access_control_lists']]
        valid_acl = list(set(valid_acl))

        orphaned_acls = set([])
        # Due to a bug in contrail API, we cannot list more than 10000 elements
        # on a resource and there is no way to list ACL by tenant.
        # So that ugly hack directly fetch all ACL UUIDs from the cassandra database :(
        pool = ConnectionPool('config_db_uuid', server_list=cassandra_servers)
        fqname_cf = ColumnFamily(pool, 'obj_fq_name_table')
        for key, value in fqname_cf.xget('access_control_list'):
            acl_uuid = decode_string(key).split(':')[-1]
            if acl_uuid in valid_acl:
                continue
            acl = Resource('access-control-list', uuid=acl_uuid, fetch=True)
            if ('parent_uuid' in acl.keys() and
                    'parent_type' in acl.keys() and
                    acl['parent_type'] == parent_type and
                    acl.uuid not in valid_acl):
                try:
                    parent_acl = acl.parent
                except ResourceNotFound:
                    msg = ("The %s parent ACL %s was not found." %
                           (parent_type.replace('-', ' '), acl['parent_uuid']))
                    if force:
                        msg = msg + " Delete orphan ACL %s." % acl.uuid
                        acl.delete()
                    logger.debug(msg)
                    orphaned_acls.add(acl['uuid'])
                else:
                    logger.debug("The ACL %(acl)s have a %(parent_type)s %(parent_acl)s which exists but \
                                  was not found in the precedent %(parent_type)s list. Not delete it." %
                                 {'acl': acl,
                                  'parent_type': parent_type.replace('-', ' '),
                                  'parent_acl': parent_acl})

        if force:
            logger.debug("%d orphaned ACL were deleted" % len(orphaned_acls))
        else:
            logger.debug("Found %d orphaned ACL to delete" % len(orphaned_acls))

# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

import kazoo.exceptions

from contrail_api_cli.exceptions import CommandError
from contrail_api_cli.utils import printo

from ..utils import ZKCommand, CheckCommand, ConfirmCommand, PathCommand

ZK_BASEPATH = "/id/virtual-networks"


def to_zk_index(nid):
    return "%(#)010d" % {'#': nid - 1}


class Indexes(object):
    # Index managed by the user are always API index. They are internally
    # translated into Zookeeper indexes by this class.
    start = 1
    end = 1 << 24

    def __init__(self, zk_client):
        self._zk_client = zk_client
        self._zk_indexes = self._zk_client.get_children(ZK_BASEPATH)

    def get_available_index(self):
        if len(self._zk_indexes) == self.end:
            raise CommandError("No available index")
        for i in range(self.start, self.end):
            zk_i = to_zk_index(i)
            if zk_i not in self._zk_indexes:
                try:
                    self._zk_client.get(ZK_BASEPATH + "/" + zk_i)
                    self._zk_indexes.append(zk_i)
                    return self.get_available_index()
                except kazoo.exceptions.NoNodeError:
                    return i

    def create(self, index, resource, dry_run):
        value = text_type(resource.fq_name).encode("utf-8")
        zk_index = to_zk_index(index)
        if dry_run:
            print "[dry_run] ",
        printo("%s Create Zookeeper %s with value %s" % (resource.path, ZK_BASEPATH + "/" + zk_index, value))
        if not dry_run:
            self._zk_client.create(ZK_BASEPATH + "/" + zk_index, value=value)
        self._zk_indexes.append(zk_index)


class FixVnId(PathCommand, ZKCommand, CheckCommand, ConfirmCommand):
    """Compare and fix virtual network IDs in Zookeeper and the API server.

    Checks that the ZK lock for a VN has the correct index. Checks also that the VN
    has a lock in ZK.

    To check all VNs run::

        contrail-api-cli fix-vn-id --check

    To fix all VNs or a particular VN run::

        contrail-api-cli fix-vn-id [--dry-run] [vn_uuid]

    """
    description = "Fix the virtual network Zookeeper locks"

    @property
    def resource_type(self):
        return 'virtual-network'

    @property
    def confirm_message(self):
        return 'Do you really want to repair virtual networks?'

    def fix(self, vn):
        if vn['reason'] == "nolock":
            lock = vn['resource']["virtual_network_network_id"]
        if vn['reason'] == "badlock":
            lock = self.indexes.get_available_index()

        self.indexes.create(lock, vn['resource'], self.dry_run)

        if vn['reason'] == "badlock":
            resource = vn["resource"]
            resource["virtual_network_network_id"] = lock
            try:
                resource["virtual_network_properties"]["network_id"] = lock
            except KeyError:
                pass
            if self.dry_run:
                print "[dry_run] ",
            printo("%s Set VN ID to %s" % (resource.path, lock))
            if not self.dry_run:
                resource.save()

    def generate(self):
        result = []
        for r in self.resources:
            r.fetch()
            nid = r.get("virtual_network_network_id", None)
            if nid is not None:
                try:
                    zk_data, _ = self.zk_client.get(ZK_BASEPATH + "/" + to_zk_index(nid))
                    if "%s" % zk_data.decode('utf-8') != "%s" % r.fq_name:
                        result.append({"reason": "badlock", "nid": nid, "path": r.path,
                                       "api-fqname": text_type(r.fq_name), "zk-fqname": zk_data,
                                       "resource": r})
                except kazoo.exceptions.NoNodeError:
                    result.append({"reason": "nolock", "nid": nid, "path": r.path,
                                   "api-fqname": text_type(r.fq_name), "resource": r})
            else:
                result.append({"reason": "badlock", "nid": nid, "path": r.path,
                               "api-fqname": text_type(r.fq_name), "resource": r})
        return result

    def __call__(self, vn_paths=None, **kwargs):
        super(FixVnId, self).__call__(**kwargs)
        self.indexes = None
        result = self.generate()
        self.indexes = Indexes(self.zk_client)
        for r in result:
            if r['reason'] == "nolock":
                printo("No  lock for %(path)s with VN Id %(nid)6s" % r)
            if r['reason'] == "badlock":
                printo("Bad lock for %(path)s with VN Id %(nid)6s zk-fqname: %(zk-fqname)s ; api-fqname: %(api-fqname)s" % r)
            if not self.check:
                self.fix(r)

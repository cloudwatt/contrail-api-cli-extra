# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type

from contrail_api_cli.resource import Collection
from contrail_api_cli.command import Option, Arg, expand_paths
from contrail_api_cli.utils import continue_prompt
from contrail_api_cli.exceptions import CommandError

import kazoo.exceptions

from ..utils import ZKCommand, CheckCommand

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
        print "%s Create Zookeeper %s with value %s" % (resource.path, ZK_BASEPATH + "/" + zk_index, value)
        if not dry_run:
            self._zk_client.create(ZK_BASEPATH + "/" + zk_index, value=value)
        self._zk_indexes.append(zk_index)


class FixVnId(ZKCommand, CheckCommand):
    """Compare and fix virtual network IDs in Zookeeper and the API server.

    Checks that the ZK lock for a VN has the correct index. Checks also that the VN
    has a lock in ZK.

    To check all VNs run::

        contrail-api-cli fix-vn-id --check

    To fix all VNs or a particular VN run::

        contrail-api-cli fix-vn-id [--dry-run] [vn_uuid]

    """
    description = "Fix the virtual network Zookeeper locks"
    yes = Option('-y', action='store_true', help='Assume Yes to all queries and do not prompt')
    vn_paths = Arg(nargs='*',
                   metavar='vn_paths',
                   help='List of VN. If no path is provided, all VNs are considered')

    def fix(self, vn, dry_run=True):
        if vn['reason'] == "nolock":
            lock = vn['resource']["virtual_network_network_id"]
        if vn['reason'] == "badlock":
            lock = self.indexes.get_available_index()

        self.indexes.create(lock, vn['resource'], dry_run)

        if vn['reason'] == "badlock":
            resource = vn["resource"]
            resource["virtual_network_network_id"] = lock
            try:
                resource["virtual_network_properties"]["network_id"] = lock
            except KeyError:
                pass
            if dry_run:
                print "[dry_run] ",
            print "%s Set VN ID to %s" % (resource.path, lock)
            if not dry_run:
                resource.save()

    def generate(self, vn_paths):
        result = []
        if vn_paths == []:
            vns = Collection("virtual-network", fetch=True, detail=True)
        else:
            vns = expand_paths(vn_paths)
            for vn in vns:
                vn.fetch()

        for r in vns:
            nid = r["virtual_network_network_id"]
            try:
                zk_data, _ = self.zk_client.get(ZK_BASEPATH + "/" + to_zk_index(nid))
            except kazoo.exceptions.NoNodeError:
                result.append({"reason": "nolock", "nid": nid, "path": r.path, "api-fqname": text_type(r.fq_name), "resource": r})
                continue
            if "%s" % zk_data.decode('utf-8') != "%s" % r.fq_name:
                result.append({"reason": "badlock", "nid": nid, "path": r.path, "api-fqname": text_type(r.fq_name), "zk-fqname": zk_data, "resource": r})
        return result

    def __call__(self, vn_paths=None, yes=False, **kwargs):
        super(FixVnId, self).__call__(**kwargs)
        if (not yes and
                not self.dry_run and
                not self.check and
                not continue_prompt("Do you really want to repair virtual networks?")):
            print "Exiting."
            exit()

        self.indexes = None
        result = self.generate(vn_paths)
        self.indexes = Indexes(self.zk_client)
        for r in result:
            if r['reason'] == "nolock":
                print "No  lock for %(path)s with VN Id %(nid)6s" % r
            if r['reason'] == "badlock":
                print "Bad lock for %(path)s with VN Id %(nid)6s zk-fqname: %(zk-fqname)s ; api-fqname: %(api-fqname)s" % r
            if not self.check:
                self.fix(r, dry_run=self.dry_run)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from contrail_api_cli.resource import Collection
from contrail_api_cli.command import Command, Option, Arg, expand_paths
from contrail_api_cli.utils import continue_prompt

from kazoo.client import KazooClient
import kazoo.exceptions

ZK_BASEPATH = "/id/virtual-networks"


def to_zk_index(nid):
    return "%(#)010d" % {'#': nid - 1}


class Indexes(object):
    """Index managed by the user are always API index. They are internally
    translated into Zookeeper indexes by this class."""
    start = 1
    end = 1 << 24

    def __init__(self, zk_client):
        self._zk_client = zk_client
        self._zk_indexes = self._zk_client.get_children(ZK_BASEPATH)

    def get_available_index(self):
        for i in range(self.start, self.end):
            zk_i = to_zk_index(i)
            if zk_i not in self._zk_indexes:
                return i
        raise Exception("No available index")

    def create(self, index, resource, dry_run):
        value = ":".join(resource.fq_name).encode("utf-8")
        zk_index = to_zk_index(index)
        if dry_run:
            print "[dry_run] ",
        print "%s Create Zookeeper %s with value %s" % (resource.path, ZK_BASEPATH + "/" + zk_index, value)
        if not dry_run:
            self._zk_client.create(ZK_BASEPATH + "/" + zk_index, value=value)
        self._zk_indexes.append(zk_index)


class FixVnId(Command):
    description = "Fix the virtual network Zookeeper locks"
    check = Option('-c', action='store_true', help='Check if it exists bad virtual networks')
    dry_run = Option('-n', action='store_true', help='Dry run')
    vn_paths = Arg(nargs='*',
                   metavar='vn_paths',
                   help='List of VN. If no path is provided, all VNs are considered.k')
    zookeeper_address = Option(help="Zookeeper address. Format is host:port. Default is localhost:2181",
                  default="localhost:2181")

    def fix(self, vn, dry_run=True):
        if vn['reason'] == "nolock":
            lock = vn['resource']["virtual_network_network_id"]
        if vn['reason'] == "badlock":
            lock = self.indexes.get_available_index()

        self.indexes.create(lock, vn['resource'], dry_run)

        if vn['reason'] == "badlock":
            resource = vn["resource"]
            resource["virtual_network_network_id"] = lock
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
                zk_data, _ = self.zk.get(ZK_BASEPATH + "/" + to_zk_index(nid))
            except kazoo.exceptions.NoNodeError:
                result.append({"reason": "nolock", "nid": nid, "path": r.path, "api-fqname": ":".join(r.fq_name), "resource": r})
                continue
            if "%s" % zk_data.decode('utf-8') != "%s" % r.fq_name:
                result.append({"reason": "badlock", "nid": nid, "path": r.path, "api-fqname": ":".join(r.fq_name), "zk-fqname": zk_data, "resource": r})
        return result

    def __call__(self, vn_paths=None, zookeeper_address=None, check=False, dry_run=False):
        if (not dry_run
            and not check
            and not continue_prompt("Do you really want to repair virtual networks?")):
            print "Exiting."
            exit()
        self.indexes = None
        self.zk = KazooClient(hosts=zookeeper_address)
        self.zk.start()

        result = self.generate(vn_paths)
        self.indexes = Indexes(self.zk)
        for r in result:
            if r['reason'] == "nolock":
                print "No  lock for %(path)s with VN Id %(nid)6s" % r
            if r['reason'] == "badlock":
                print "Bad lock for %(path)s with VN Id %(nid)6s zk-fqname: %(zk-fqname)s ; api-fqname: %(api-fqname)s" % r
            if not check:
                self.fix(r, dry_run)

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools

from networkx.drawing.nx_pydot import write_dot

import networkx as nx

from contrail_api_cli.resource import Resource
from contrail_api_cli.exceptions import ResourceMissing
from contrail_api_cli.command import Command, Arg, Option, expand_paths


def network_attributes(network):
    acc = []
    for ipam in network['network_ipam_refs']:
        for s in ipam['attr']['ipam_subnets']:
            acc.append("%s/%s" % (s['subnet']['ip_prefix'],s['subnet']['ip_prefix_len']))
    return acc

rendering_map = {"routing-instance": {"color": "#E77AF4", "alias":  "ri"},
                 "route-target": {
                     "color": "#F47A7A",
                     "alias": "rt",
                     "attributes": lambda r: r.get("display_name", "").split(":")[1:]},
                 "virtual-machine-interface": {"color": "#7AF4D0", "alias":  "vmi"},
                 "virtual-network": {"color": "#7AD3F4", "alias":  "vn",
                                     "attributes": network_attributes},
                 "logical-router": {"color": "white", "alias":  "lr"},
                 "instance-ip": {"color": "#E6F521", "alias":  "ip",
                                 "attributes": lambda r: [r.get("instance_ip_address")]},
                 "service-instance": {"color": "#CDEE93", "alias":  "si"},
                 "virtual-router": {"color": "white", "alias":  "vr"},
                 "service-template": {"color": "white", "alias":  "st"},
                 "network-ipam": {"color": "white", "alias":  "ipam"},
                 "virtual-machine": {"color": "#F4C07A", "alias":  "vm"}}

def default_renderer(path_name):
    return {"color": "white", "alias": path_name}


def short_name(path_name):
    return path_name[0:7]


def _node_rendering(path, provided=False, resource=None):
    renderer = rendering_map.get(path.base, default_renderer(path.base))
    if "attributes" in renderer:
        if resource is None:
            resource = expand_paths([path])[0]
            resource.fetch()
        attributes = renderer["attributes"](resource)
    else:
        attributes = []
    label = "%s\n%s\n%s" % (renderer["alias"], short_name(path.name), "\n".join(attributes))
    if provided:
        shape = "box"
        color = "red"
    else:
        shape = "box"
        color = "black"
    return {"label": label,
            "style": "filled",
            "color": color,
            "shape": shape,
#            style="
            "fillcolor": renderer["color"]}


class Dot(Command):
    description = "Create a dot file representing provided resources"
    filename_output = Option('-f', help="Output Dot filename", required=True)
    exclude_resource_type = Option('-e', help="Exclude resource types",
                                   action="append", default=[], dest='excludes')
    paths = Arg(help="Resource URL", metavar='path', nargs="*")

    def __call__(self, paths=None, filename_output=None, excludes=[]):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        graph = nx.Graph()

        # For each provided resources, a edge is created from this
        # resource to all of its refs, back_refs and parent.
        for r in resources:
            print "%s %s" % (short_name(r.path.name), r.path)
            r.fetch()
            graph.add_node(r.path, _node_rendering(r.path, resource=r, provided=True))

            paths = [t.path for t in itertools.chain(r.refs, r.back_refs, r.children)]
            try:
                paths.append(r.parent.path)
            except ResourceMissing:
                pass
            for p in paths:
                if p.base in excludes:
                    continue
                print "%s   %s" % (short_name(p.name), p)
                graph.add_node(p, _node_rendering(p))
                graph.add_edge(r.path, p)

        print "Dot file written to %s" % filename_output
        write_dot(graph, filename_output)

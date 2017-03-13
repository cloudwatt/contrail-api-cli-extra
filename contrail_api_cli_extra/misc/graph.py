# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from itertools import chain

# from networkx.drawing.nx_pydot import write_dot
import networkx as nx

from contrail_api_cli.resource import Collection
from contrail_api_cli.command import Command, Arg


class Graph(Command):
    description = "Create a graph file (graphml) by listing several collections"
    filename = Arg(help="Output filename", metavar='filename', type=str)

    def _to_graphml(self, filename):
        tmp_filename = "%s.tmp" % filename
        nx.write_graphml(self.graph, tmp_filename)

        # This is a hack since gremlin/thinkerpop requires a id on edges to be
        # able to load a graphml structure
        counter = 0
        with open(tmp_filename, 'r') as f1:
            with open(filename, 'w') as f2:
                for l in f1.readlines():
                    e = unicode(l, "utf8").replace(u'edge ', u'edge id="e%d" ' % counter)
                    f2.write(e.encode("utf8"))
                    counter += 1
        os.remove(tmp_filename)

    def __call__(self, filename):
        self.graph = nx.DiGraph()

        cols = [Collection(r, fetch=True, detail=True)
                for r in ["virtual-machine-interface",
                          "virtual-network",
                          "instance-ip",
                          "loadbalancer-pool",
                          "virtual-ip",
                          "instance-ip",
                          "logical-router",
                          "floating-ip",
                          "service-template",
                          "service-instance"]]

        def add_node(g, r):
            self.graph.add_node(r.uuid, type=r.type,
                                fq_name=":".join(r.fq_name),
                                name=r.fq_name[-1])

        for e in chain(*cols):
            add_node(self.graph, e)
            for r in e.refs:
                add_node(self.graph, r)
                self.graph.add_edge(e.uuid,  r.uuid)

        self._to_graphml(filename)

        # TODO: we can aslo generate a dot file
        # write_dot(G, 'foo.dot')
        # os.system('dot -Tsvg foo.dot -o /tmp/foo.svg')

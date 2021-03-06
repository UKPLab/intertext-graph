from __future__ import annotations
import json
from typing import Dict, Iterator, List, Optional, TextIO

from intertext_graph.itgraph import Etype, IntertextDocument, Node


class IntertextMultiGraph(IntertextDocument):

    def __init__(self, *args: IntertextDocument, **kwargs: Optional[Dict]) -> None:
        # Need to initialize IntertextDocument first.
        super().__init__([], [], '', {})

        nodes = []
        edges = []
        # Use meta dict if specified else merge metadata from docs
        self.meta = kwargs['meta'] if 'meta' in kwargs else {}
        for doc in args:
            nodes += doc.nodes
            edges += doc.edges
            if 'meta' not in kwargs and doc.meta:
                self.meta.update(doc.meta)

        self._prefix = 'multi'
        """As we build the new IntertextDocument from existing graphs, set
        _deserialization to True to avoid creating double edges
        in IntertextDocument.add_node()."""
        self._init_from_existing_doc = True
        for n in nodes:
            self.add_node(n)
        for e in edges:
            self.add_edge(e)
        self._init_from_existing_doc = False

    @property
    def root(self) -> Node:
        """Use roots for multi graphs."""
        raise NotImplemented

    @property
    def roots(self) -> Iterator[Node]:
        """Finds and returns the root nodes.

        Requires a graph containing next edges."""
        for node in self.nodes:
            if not node.get_edges(Etype.NEXT, outgoing=False) and node.get_edges(Etype.NEXT, incoming=False):
                yield node

    @classmethod
    def load_json(cls, *args: TextIO) -> IntertextMultiGraph:
        data = {'nodes': [], 'edges': [], 'span_nodes': [], 'prefix': 'multi', 'meta': {}}
        prefixes = []
        for fp in args:
            tmp = json.load(fp)
            data['nodes'] += tmp['nodes']
            data['edges'] += tmp['edges']
            data['span_nodes'] += tmp['span_nodes']
            data['meta'].update(tmp['meta'])
            prefixes.append(tmp['prefix'])
        return cls(cls._from_json(data))

    def unroll_graph(self) -> List[Node]:
        """Use unroll_subgraph() for multi graphs."""
        raise NotImplementedError

    def unroll_subgraph(self, root: Node) -> List[Node]:
        """Returns an ordered list of nodes.

        Follows next edges from the specified root.
        """
        return self._unroll_graph(root)

from __future__ import annotations
from enum import auto, Enum
import json
from typing import Any, Iterator, TextIO
from uuid import uuid4

import networkx as nx


class Node:

    def __init__(self, content: str, ntype: str = None, meta: dict[str, Any] = None) -> None:
        self.ix = None
        self._uuid = str(uuid4())
        self.content = content.strip()
        self.ntype = ntype
        self.meta = meta
        self.embedding: Any | None = None
        # Keep track of edges by UUID and retrieve edge objects using the graph instance
        # Necessary to break reference cycles between nodes and edges
        # Lists are faster here then sets due to iterations in the computed properties below
        self._incoming_edges = []
        self._outgoing_edges = []
        self._doc = None

    @property
    def incoming_edges(self) -> list[Edge]:
        # Prevent reference cycles by retrieving edge objects in a computed property
        return [self._doc._edges[uuid] for uuid in self._incoming_edges]

    @property
    def outgoing_edges(self) -> list[Edge]:
        # Prevent reference cycles by retrieving edge objects in a computed property
        return [self._doc._edges[uuid] for uuid in self._outgoing_edges]

    def add_edge(self, edge: Edge) -> None:
        if edge.src_node == self:
            assert edge._uuid not in self._outgoing_edges
            self._outgoing_edges.append(edge._uuid)
        elif edge.tgt_node == self:
            assert edge._uuid not in self._incoming_edges
            self._incoming_edges.append(edge._uuid)

    def remove_edge(self, edge: Edge) -> None:
        if edge.src_node == self:
            self._outgoing_edges.remove(edge._uuid)
        elif edge.tgt_node == self:
            self._incoming_edges.remove(edge._uuid)

    def get_edges(self, etype: Etype = None, outgoing: bool = True, incoming: bool = True) -> list[Edge]:
        """Get all edges with optional filters."""
        edges = []
        if outgoing:
            edges += [e for e in self.outgoing_edges if not etype or e.etype == etype]
        if incoming:
            edges += [e for e in self.incoming_edges if not etype or e.etype == etype]
        return edges

    def __lt__(self, other: Node) -> bool:
        if not isinstance(other, Node):
            raise NotImplemented
        assert self._doc is not None
        # Check that both nodes are connected
        assert other in self._doc.nodes
        # Use node indices as a weak indicator for an optimal search direction
        # Assumption is that (most) nodes are added sequentially
        if self._doc.nodes.index(self) < self._doc.nodes.index(other):
            for node in self._doc.breadcrumbs(other, Etype.NEXT):
                if node == self:
                    return True
            return False
        else:
            for node in self._doc.breadcrumbs(self, Etype.NEXT):
                if node == other:
                    return False
            return True

    def __le__(self, other: Node) -> bool:
        return self < other or self == other

    def __gt__(self, other: Node) -> bool:
        if not isinstance(other, Node):
            raise NotImplemented
        return other < self

    def __ge__(self, other: Node) -> bool:
        return self > other or self == other

    def __str__(self) -> str:
        return self.content


class Etype(Enum):

    PARENT = auto()
    NEXT = auto()
    LINK = auto()

    def __str__(self) -> str:
        return self.name.lower()


class Edge:

    def __init__(self, src_node: Node, tgt_node: Node, etype: Etype, meta: dict[str, Any] = None) -> None:
        self._uuid = str(uuid4())
        # Keep track of src and tgt nodes by UUID and retrieve node objects using the graph instance
        # Necessary to break reference cycles between nodes and edges
        self._src_node = src_node._uuid
        self._tgt_node = tgt_node._uuid
        self.etype = etype
        self.meta = meta
        self._doc = None

    @property
    def ix(self) -> str:
        """Concatenate ix from source and target.

        Use a computed property since source and / or target ix could be updated.
        """
        assert self.src_node.ix is not None and self.tgt_node.ix is not None
        return f'{self.src_node.ix}_{self.tgt_node.ix}_{str(self.etype)}'

    @property
    def src_node(self) -> Node:
        # Prevent reference cycles by retrieving node objects in a computed property
        assert self._doc is not None
        return self._doc._nodes[self._src_node]

    @property
    def tgt_node(self) -> Node:
        # Prevent reference cycles by retrieving node objects in a computed property
        assert self._doc is not None
        return self._doc._nodes[self._tgt_node]


class IntertextDocument:

    def __init__(self, nodes: list[Node], edges: list[Edge], prefix: str, meta: dict[str, Any] = None) -> None:
        self._prefix = prefix
        self.meta = meta or {}
        if 'ix_counter' not in self.meta:
            self.meta['ix_counter'] = -1
        # Uses dicts for nodes and edges as fast internal lookup tables
        self._nodes: dict[str, Node] = dict()
        # Make mapping of node ix's to uuids
        self._node_ix_to_uuid = {}
        self._edge_ix_to_uuid = {}
        # Flag for limiting use of automagic expressions during deserialization
        self._init_from_existing_doc = False
        for n in nodes:
            self.add_node(n)
        self._edges: dict[str, Edge] = dict()
        for e in edges:
            self.add_edge(e)

    def __len__(self) -> int:
        return len(self._nodes)

    @property
    def nodes(self) -> list[Node]:
        # Hide UUID lookup dict from public API
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        # Hide UUID lookup dict from public API
        return list(self._edges.values())

    @property
    def root(self) -> Node:
        """Finds and returns the root node.

        Requires a graph containing next edges."""
        if len(self.nodes) == 1:
            # The doc consists of only one node and no edges
            return self.nodes[0]
        for node in self.nodes:
            if not node.get_edges(Etype.NEXT, outgoing=False) and node.get_edges(Etype.NEXT, incoming=False):
                return node

    def add_node(self, node: Node) -> None:
        # Ix counter never decreases to prohibit naming collision
        # Increase ix counter independently of existing ix to reflect the number of nodes added over time
        self.meta['ix_counter'] += 1
        # Index is not overridden, e.g. when loading from JSON or combining multiple docs via multi graph
        if node.ix is None:
            node.ix = f'{self._prefix}_{self.meta["ix_counter"]}'
        # Reset edges to match this graph, e.g. in case a node has been moved from one graph to another
        node._incoming_edges = []
        node._outgoing_edges = []
        node._doc = self
        assert node.ix not in self._node_ix_to_uuid
        self._nodes[node._uuid] = node
        self._node_ix_to_uuid[node.ix] = node._uuid
        # For span nodes add an edge from their source.
        # Skip when building from an existing IntertextDocument object.
        if not self._init_from_existing_doc and isinstance(node, SpanNode):
            edge = Edge(node.src_node, node, Etype.LINK, meta={
                'created_by': node.meta['created_by']
            } if node.meta and 'created_by' in node.meta else None)
            edge._doc = self
            self.add_edge(edge)

    def add_edge(self, edge: Edge) -> None:
        edge._doc = self
        assert edge.ix not in self._edge_ix_to_uuid
        # Nodes have to keep track of their incoming and outgoing edges
        edge.src_node.add_edge(edge)
        edge.tgt_node.add_edge(edge)
        self._edges[edge._uuid] = edge
        self._edge_ix_to_uuid[edge.ix] = edge._uuid

    def remove_node(self, node: Node) -> None:
        """Removes a node and all its adjacent edges."""
        for edge in node.incoming_edges + node.outgoing_edges:
            self.remove_edge(edge)
        del self._nodes[node._uuid]
        del self._node_ix_to_uuid[node.ix]

    def remove_edge(self, edge: Edge) -> None:
        edge.src_node.remove_edge(edge)
        edge.tgt_node.remove_edge(edge)
        del self._edges[edge._uuid]
        del self._edge_ix_to_uuid[edge.ix]

    def save_json(self, fp: TextIO) -> None:
        fp.write(self.to_json(indent=4))
        return

    def to_json(self, indent=4) -> str:
        nodes, span_nodes = [], []
        for node in self.nodes:
            if isinstance(node, SpanNode):
                span_nodes.append(node)
            else:
                nodes.append(node)
        edges = []
        for edge in self.edges:
            edges.append(edge)
        data = {'nodes': nodes, 'span_nodes': span_nodes, 'edges': edges, 'prefix': self._prefix, 'meta': self.meta}
        out = json.dumps(data, cls=IntertextEncoder, indent=indent)
        return out

    @classmethod
    def _from_json(cls, data: dict[str, Any]) -> IntertextDocument:
        itg = IntertextDocument([], [], data['prefix'], data['meta'])
        itg._init_from_existing_doc = True
        for n in data['nodes']:
            node = Node(n['content'], n['ntype'], n['meta'])
            node.ix = n['ix']
            itg.add_node(node)
        for sn in data['span_nodes']:
            span_node = SpanNode(
                ntype=sn['ntype'],
                src_node=itg.get_node_by_ix(sn['src_ix']),
                start=sn['start'],
                end=sn['end'],
                meta=sn['meta'],
                label=sn['label']
            )
            span_node.ix = sn['ix']
            itg.add_node(span_node)
        # Reset the ix counter which has been increased by add_node()
        # For backwards compatibility this is optional
        if 'ix_counter' in data['meta']:
            itg.meta['ix_counter'] = data['meta']['ix_counter']
        for e in data['edges']:
            itg.add_edge(Edge(itg.get_node_by_ix(e['src_ix']),
                itg.get_node_by_ix(e['tgt_ix']),
                Etype[e['etype'].upper()],
                e['meta']))
        itg._init_from_existing_doc = False
        return itg

    @classmethod
    def load_json(cls, fp: TextIO) -> IntertextDocument:
        return cls._from_json(json.load(fp))

    def _unroll_graph(self, node: Node) -> list[Node]:
        result = []
        breadcrumbs = []
        queue = [node]
        while queue:
            current_node = queue.pop(0)
            for e in current_node.get_edges(Etype.NEXT, incoming=False):
                # Use breadcrumbs to keep track of followed edges
                # This prevents infinite loops when some nodes are visited multiple times
                if e.ix not in breadcrumbs:
                    breadcrumbs.append(e.ix)
                    queue.append(e.tgt_node)

            result.append(current_node)

        return result

    def unroll_graph(self) -> list[Node]:
        """Returns an ordered list of nodes.

        Follows next edges from the root.
        """
        return self._unroll_graph(self.root)

    def breadcrumbs(self, node: Node, etype: Etype) -> Iterator[Node]:
        """Returns an ordered iterator of nodes from the given node following edges backwards to its source.

        In case of `parent` or `next` this finds a path to the root, for `ref` the source could be any node.

        If there are multiple parallel path for the specified edge type only one will be returned.
        The one picked does not have to be the shortest path. This does not affect `parent` and `next` edges."""
        yield node
        # Find and follow an incoming edge
        for edge in node.get_edges(etype, outgoing=False):
            yield from self.breadcrumbs(edge.src_node, etype)
            # Break loop for performance gain
            break

    def tree_distance(self, n_1: Node, n_2: Node, etype: Etype) -> int:
        """Returns the tree distance between two nodes following one edge type.

        If there are multiple parallel path for the specified edge type only one distance will be returned.
        The one picked does not have to be the shortest path. This does not affect `parent` and `next` edges."""
        # Follow node breadcrumbs to their source (root) for both nodes individually
        b_1 = set(self.breadcrumbs(n_1, etype))
        b_2 = set(self.breadcrumbs(n_2, etype))
        # Get the length of the difference between both sets
        # Automatically excludes the node were both breadcrumbs meet and therefore returns the number of edges
        return len(b_1 ^ b_2)

    def to_plaintext(self, allow_list: List[str] = None) -> str:
        """Returns a line separated plaintext representation of the graph."""
        nodes = []
        for node in self.unroll_graph():
            if allow_list is None or node.ntype in allow_list:
                nodes.append(str(node))
        return '\n'.join(nodes)

    def to_networkx(self) -> nx.MultiDiGraph():
        """IntertextDocument works independent of NetworkX.

        The MultiDiGraph can be used for additional features or prototyping."""
        graph = nx.MultiDiGraph()
        for node in self.nodes:
            graph.add_node(node)
        for edge in self.edges:
            # Unique key required when removing overlapping edges
            graph.add_edge(edge.src_node, edge.tgt_node, key=edge.ix, attr={'etype': edge.etype, 'ix': edge.ix})
        return graph

    @property
    def node_ix_to_uuid(self) -> dict[str, uuid4]:
        return self._node_ix_to_uuid

    @property
    def edge_ix_to_uuid(self) -> dict[str, uuid4]:
        return self._edge_ix_to_uuid

    def get_node_by_ix(self, ix: str) -> Node:
        return self._nodes[self._node_ix_to_uuid[ix]]

    def get_edge_by_ix(self, ix: str) -> Edge:
        return self._edges[self._edge_ix_to_uuid[ix]]


class SpanNode(Node):
    """Extra node class for annotations etc. to keep added nodes separate from nodes that stem from source parsing.

    Span nodes and their respective source node are automagically connected over a link edge."""

    def __init__(
            self,
            ntype: str,
            src_node: Node,
            start: int = 0,
            end: int = None,
            meta: dict[str, Any] = None,
            label: dict = None
    ) -> None:
        self.ix = None
        self.start = start
        self.end = end if end is not None else len(str(src_node))
        self.src_node = src_node
        self.label = label if label else {}
        super().__init__(content='', ntype=ntype, meta=meta)

    @property
    def content(self):
        return self.src_node.content[self.start:self.end + 1]

    @content.setter
    def content(self, value: str) -> None:
        """Empty setter"""
        pass


class IntertextEncoder(json.JSONEncoder):

    def default(self, o: Any) -> Any:
        if isinstance(o, Edge):
            return {'src_ix': o.src_node.ix, 'tgt_ix': o.tgt_node.ix, 'etype': str(o.etype), 'meta': o.meta}
        elif isinstance(o, Node):
            node = {'ix': o.ix, 'content': o.content, 'ntype': o.ntype, 'meta': o.meta}
            if isinstance(o, SpanNode):
                node.update({'src_ix': o.src_node.ix, 'start': o.start, 'end': o.end, 'label': o.label})
            return node
        return json.JSONEncoder.default(self, o)

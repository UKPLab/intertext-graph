from multiprocessing import Pool
from os import PathLike
import pkg_resources
import re
from typing import Any, Dict, Iterator, List, Union
from warnings import warn

from tqdm import tqdm

from intertext_graph.itgraph import Edge, Etype, Node, SpanNode
from intertext_graph.parsers.utils import chunksize, num_processes


class IntertextParser:

    def __init__(self, path: Union[PathLike, str]) -> None:
        self._meta = {
            'parser': type(self).__name__,
            'intertext-graph': pkg_resources.require('intertext-graph')[0].version
        }

    @classmethod
    def _make_node(cls, content: str, ntype: str, meta: Dict[str, Any] = None) -> Node:
        """Adds a created by meta attribute and passes the arguments to the Node constructor."""
        if not meta:
            meta = {}
        meta['created_by'] = cls.__name__
        return Node(content, ntype, meta)

    @classmethod
    def _make_edge(cls, src_node: Node, tgt_node: Node, etype: Etype, meta: Dict[str, Any] = None) -> Edge:
        """Adds a created by meta attribute and passes the arguments to the Edge constructor."""
        if not meta:
            meta = {}
        meta['created_by'] = cls.__name__
        return Edge(src_node, tgt_node, etype, meta)

    @classmethod
    def _make_span_node(
            cls,
            ntype: str,
            src_node: Node,
            start: int = 0,
            end: int = None,
            etype: Etype = Etype.LINK,
            meta: Dict[str, Any] = None,
            label: Dict = None) -> Node:
        """Adds a created by meta attribute and passes the arguments to the SpanNode constructor."""
        if not meta:
            meta = {}
        meta['created_by'] = cls.__name__
        return SpanNode(ntype, src_node, start, end, etype, meta, label)

    @classmethod
    def _parse_whitespace(cls, text: str) -> str:
        # This replaces line breaks, tabs, spaces, and non-breaking spaces (both as a string and unicode character)
        text = re.sub(r'[\n\t   ]+', ' ', text)
        return text.strip()

    def parse(self) -> Any:
        warn('parse() is deprecated. Use __call__() instead.', DeprecationWarning, stacklevel=2)
        return self.__call__()

    def __call__(self, *args, **kwargs) -> Any:
        raise NotImplementedError

    @classmethod
    def _batch_func(cls, path: Any) -> Any:
        raise NotImplementedError

    @classmethod
    def batch_parse(cls, files: List[Any]) -> Iterator[Any]:
        """Parse a list of files using multiprocessing."""
        total = len(files)
        with Pool(processes=num_processes()) as pool:
            for parsed in tqdm(
                    pool.imap_unordered(cls._batch_func, files, chunksize(total)),
                    total=total,
                    desc='parsing documents'):
                if parsed:
                    yield parsed
            pool.close()
            pool.join()

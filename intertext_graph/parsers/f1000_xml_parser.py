from copy import deepcopy
from importlib.resources import open_text
from io import BytesIO
from os import PathLike
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from lxml import etree
from lxml.etree import XMLSyntaxError
import requests

from intertext_graph.itgraph import Node, Edge, Etype, IntertextDocument
from intertext_graph.parsers.itparser import IntertextParser
from intertext_graph import resources


class F1000XMLParser(IntertextParser):

    def __init__(self, path: Union[PathLike, str]) -> None:
        # TODO: Handle broken xml
        super().__init__(path)
        if isinstance(path, str) and path.startswith('http'):
            request = requests.get(path)
            self._root = etree.parse(BytesIO(request.content))
        else:
            with open(path, encoding='utf-8') as xml:
                self._root = etree.parse(xml)
        self._curr_section = []
        self._xref_targets = {}

    def get_doc_and_version(self) -> Tuple[str, int]:
        # If the doc has already been parsed return values stored in the meta dict
        if 'doc_id' in self._meta and 'version' in self._meta:
            return self._meta['doc_id'], self._meta['version']
        meta = self._root.find('.//article-meta')
        volume = meta.xpath('volume')[0].text
        # Elocation id can be prefixed with venue specific strings which are discarded
        elocation_id = meta.xpath('elocation-id')[0].text.split('-')[-1]
        for status in meta.xpath('title-group/fn-group/fn/p')[0].text.strip('[]').split(';'):
            if status.startswith('version '):
                return f'{volume}-{elocation_id}', int(status[8:])
        assert False

    def _parse_meta(self) -> None:
        meta = self._root.find('.//article-meta')
        article_id = meta.find('.//article-id[@pub-id-type="doi"]')
        doi = article_id.text if article_id is not None else 'NA'
        atype = self._root.getroot().attrib['article-type']
        # brief report = research note, see https://f1000research.com/for-authors/article-guidelines
        if atype == "brief-report":
            atype = "research-note"
        title = self._stringify(meta.find('.//article-title'))
        abstract = self._parse_whitespace(self._stringify(meta.find(".//abstract")))
        license = meta.find('.//license').attrib['{http://www.w3.org/1999/xlink}href']
        contributors = [
            {
                'surname': contrib.find('.//name/surname').text,
                'given-names': contrib.find('.//name/given-names').text
            } for contrib in meta.find('.//contrib-group')
            if contrib.tag == 'contrib' and (contrib.find('.//name/surname') is not None)
        ]
        self._meta.update({'doi': doi, 'atype': atype, 'license': license, 'title': title, 'abstract': abstract, 'contributors': contributors})
        doc_id, version = self.get_doc_and_version()
        if doc_id is not None:
            self._meta['url'] = f'https://f1000research.com/articles/{doc_id}/v{version}/'
            self._meta.update({'doc_id': doc_id, 'version': version})

    @classmethod
    def _stringify(cls, element: etree._Element) -> str:
        """Stringifies XML elements by removing all nested tags."""
        children = list(element)
        if children:
            return ' '.join(element.itertext()).strip()
        else:
            return element.text

    @classmethod
    def _split_element(cls, element: etree._Element, selector: str) -> List[etree._Element]:
        """Split an element before and after the selector."""
        node = deepcopy(element)
        # TODO: Find a more generic way to remove namespaces
        leaf = etree.tostring(node.xpath(selector)[0], with_tail=False).decode('utf-8').replace(' xmlns:xlink="http://www.w3.org/1999/xlink"', '')
        s_0, s_1, s_2 = etree.tostring(node).decode('utf-8').partition(leaf)
        parser = etree.XMLParser(recover=True)
        xml_split = [etree.fromstring(s_0, parser), etree.fromstring(s_1, parser)]
        for e in reversed(list(xml_split[0].iter())):
            s_2 = f'<{e.tag}>' + s_2
        xml_split.append(etree.fromstring(s_2, parser))
        return xml_split

    @classmethod
    def _elevate_element(cls, element: etree._Element, selector: str) -> List[etree._Element]:
        # Remove boxed text from the current paragraph and elevate it to its parent node
        node = element.xpath(selector)
        element.remove(node[0])
        # If there are siblings elevate the node otherwise replace its parent
        # There would be multiple roots otherwise
        if list(element.iterdescendants()):
            element.addnext(node[0])
        else:
            element = node[0]
        # Pass the current element with its new set of succeeding siblings back for another iteration
        return [element] + list(element.itersiblings())

    @classmethod
    def _make_node(cls, element: etree._Element, stringify: bool = False, meta: Dict[str, Any] = None) -> Optional[Node]:
        if stringify:
            content = cls._stringify(element)
            if content:
                content = cls._parse_whitespace(content)
        else:
            content = element.tag.capitalize()
        if content and len(content.strip()) > 0:
            return super()._make_node(content, element.tag, meta)
        else:
            return None

    @classmethod
    def _make_xml_node(cls, element: etree._Element, meta: Dict[str, Any] = None) -> Node:
        content = cls._parse_whitespace(etree.tostring(element).decode('utf-8'))
        return super()._make_node(content, element.tag, meta)

    @classmethod
    def _parse_node_meta(cls, element: etree._Element) -> Optional[Dict[str, str]]:
        meta = {}
        if 'id' in element.attrib:
            meta['id'] = element.attrib['id']
        caption = element.xpath('caption')
        if caption:
            meta['caption'] = cls._parse_whitespace(cls._stringify(caption[0]))
        graphic = element.xpath('graphic')
        if graphic:
            for key, value in graphic[0].attrib.items():
                # F1000 key is {http://www.w3.org/1999/xlink}href
                if key.endswith('href'):
                    meta['uri'] = value
        return meta if len(meta) > 0 else None

    def _generate_sec_index(self, element: etree._Element) -> str:
        """Get current section depth by counting ancestor tags.

        Can handle multiple levels of subsections.
        """
        # Checking for an existing title tag is important as only those are represented in the graph
        ancestors = len(element.xpath(f'ancestor::{element.tag}/title'))
        # Reduce current section depth based on ancestors
        # This resets the list when ascending in the subsection path
        self._curr_section = self._curr_section[:ancestors + 1]
        # Set the current section index
        if len(self._curr_section) < ancestors + 1:
            self._curr_section.append(1)
        else:
            self._curr_section[ancestors] += 1
        # Concatenate potential subsection levels
        return '.'.join(map(lambda x: str(x), self._curr_section))

    @classmethod
    def _collect_xrefs(cls, element: etree._Element) -> Set[str]:
        """Collects xrefs for fig, table, boxed-text, and sec."""
        xrefs = element.xpath('.//xref[@rid and (@ref-type="bibr" or @ref-type="fig" or @ref-type="table" or @ref-type="boxed-text" or @ref-type="sec")]')
        # Return a set as a node can contain one reference multiple times but should be linked with a single edge
        return {xref.attrib['rid'] for xref in xrefs}

    def _parse_element(self, element: etree._Element) -> Tuple[Optional[Node], List[etree._Element]]:
        children = list(element)
        if children:
            # Parse nodes with children, i.e. subtrees
            if element.tag == 'body':
                return None, children
            elif element.tag == 'abstract':
                node = self._make_node(element)
            elif element.tag == 'sec':
                # Move the title child to the root node of a section
                title_element = element.xpath('title')
                if title_element and title_element[0].text:
                    meta = {'section': self._generate_sec_index(element)}
                    if 'id' in element.attrib:
                        meta['id'] = element.attrib['id']
                    if 'sec-type' in element.attrib:
                        meta['sec-type'] = element.attrib['sec-type']
                    node = self._make_node(title_element[0], stringify=True, meta=meta)
                    children.remove(title_element[0])
                    # Keep track of potential xref targets
                    if meta and 'id' in meta:
                        self._xref_targets[meta['id']] = node
                else:
                    # Section has no title
                    node = None
            elif element.tag == 'list':
                # Concatenate list items with new line
                # Do not pass through _make_node() or new lines will be removed
                content = '\n'.join([f'- {self._parse_whitespace(self._stringify(e))}' for e in element.xpath('list-item')])
                ntype = element.tag
                node = super()._make_node(content, ntype)
                # Drop children
                children = []
            elif element.tag == 'p':
                # Stringify paragraphs, drop all inline tags
                tags = [e.tag for e in element.iterdescendants()]
                if 'boxed-text' in tags:
                    # Boxed text has to be processed before other nested types as is might contain these as children
                    return None, self._elevate_element(element, 'boxed-text')
                elif element.xpath('preformat'):
                    # Elevate immediate children but ignore nested inline tags
                    return None, self._elevate_element(element, 'preformat')
                elif 'list' in tags:
                    # Split paragraph before and after an inline list
                    # A human would probably read this as separate paragraphs
                    return None, self._split_element(element, './/list')
                meta = None
                # Add metadata for xrefs which will later be parsed into edges
                if 'xref' in tags:
                    xrefs = self._collect_xrefs(element)
                    if xrefs:
                        meta = {'xrefs': xrefs}
                # Drop inline xref
                etree.strip_tags(element, 'xref')
                node = self._make_node(element, stringify=True, meta=meta)
                # Drop children
                children = []
            elif element.tag in ['fig', 'table-wrap', 'boxed-text']:
                # Get optional meta data
                meta = self._parse_node_meta(element)
                label_element = element.xpath('label')
                if label_element:
                    # Move the label child to the root node
                    node = self._make_node(element.xpath('label')[0], stringify=True, meta=meta)
                    # Remove the label tag and do another recursive call to parse element as an XML node
                    etree.strip_elements(element, 'label', with_tail=False)
                    children = [element]
                else:
                    # Handle second recursive call or cases where there is no label
                    node = self._make_xml_node(element, meta=meta)
                    # Drop children
                    children = []
                # Keep track of potential xref targets
                if meta and 'id' in meta:
                    self._xref_targets[meta['id']] = node
            elif 'formula' in element.tag:
                # Discard for now
                return None, []
            else:
                node = self._make_xml_node(element)
                # Drop children
                children = []
        else:
            # Parse leaf nodes with potential inline tags
            node = self._make_node(element, stringify=True)
        return node, children

    def _parse_tree(self, curr_root: etree._Element, parent: Node = None) -> Tuple[List[Node], List[Edge]]:
        """Takes the <body> tag as first input."""
        # Parse the root node
        node, children = self._parse_element(curr_root)
        nodes = []
        edges = []
        if node is not None:
            nodes.append(node)
            if parent is not None:
                edges.append(super()._make_edge(parent, node, Etype.PARENT))
        else:
            # If node is empty, i.e. body node or a section without a title, use the parent node
            node = parent
        # Recursive call on each child
        for child in children:
            n, e = self._parse_tree(child, node)
            if len(n) == 1:  # TODO: Check if condition is sufficient
                # TODO: Implement proper parsing, see https://f1000research.com/for-referees/guidelines#rar
                for line in open_text(resources, 'review_boilerplate.txt'):
                    if line.strip() in n[0].content:
                        # Drop questionnaire nodes
                        return nodes, edges
            nodes += n
            edges += e
        return nodes, edges

    def _parse_refs(self, ref_list: etree._Element) -> None:
        # Do not add ref nodes to the graph yet otherwise they would become part of the next graph
        for ref in ref_list:
            self._xref_targets[ref.attrib['id']] = self._make_node(ref, stringify=True, meta={'id': ref.attrib['id']})

    def _add_supplementary_edges(self, nodes: List, edges: List) -> None:
        """Adds next and ref edges."""
        # Assumes sequential parsing of the XML file
        prev = None
        for curr in nodes:
            if prev is not None:
                edges.append(super()._make_edge(prev, curr, Etype.NEXT))
            prev = curr
        # Add ref edges
        for key, tgt_node in self._xref_targets.items():
            for node in nodes:
                # As of now supplementary material is not supported, therefore some xrefs have no target node
                if node.meta is not None and 'xrefs' in node.meta and key in node.meta['xrefs']:
                    edges.append(super()._make_edge(node, tgt_node, Etype.LINK))
                    # Add target nodes to the graph after computing the next graph
                    # Disconnected references are dropped
                    if tgt_node not in nodes:
                        nodes.append(tgt_node)
                    break
        for node in nodes:
            if node.meta is not None and 'xrefs' in node.meta:
                # Clean up temporary helper data
                del node.meta['xrefs']
                if len(node.meta) == 0:
                    node.meta = None

    def _parse(self, element: etree._Element, meta: Dict[str, Any], prefix: str = '') -> Optional[IntertextDocument]:
        nodes, edges = [], []
        title_node = self._make_node(element.find('.//article-title'), stringify=True)
        nodes.append(title_node)
        abstract = element.find('.//abstract')
        # Abstract is optional, e.g. in reviews
        if abstract is not None:
            n, e = self._parse_tree(abstract, title_node)
            nodes += n
            edges += e
        # Parse refs
        # TODO: Look into ways to parse fn-group tags
        ref_list = element.findall('back/ref-list/ref')
        if ref_list:
            self._parse_refs(ref_list)
        body = element.find('body')
        if body is not None:
            n, e = self._parse_tree(body, title_node)
            nodes += n
            edges += e
        else:
            # TODO: Why does this happen?
            return None
        self._add_supplementary_edges(nodes, edges)
        return IntertextDocument(nodes, edges, prefix, meta)

    def __call__(self, *args, **kwargs) -> Tuple[IntertextDocument, Dict[str, IntertextDocument], Optional[IntertextDocument]]:
        # Main document
        self._parse_meta()
        prefix = None
        if 'doc_id' in self._meta.keys():
            # Assign a unique prefix
            # This has to be version unique for diffs
            prefix = f'{self._meta["doc_id"]}_v{self._meta["version"]}'
        main_doc = self._parse(self._root, self._meta, prefix or 'doc')
        # Reviews
        reviews = {}
        for review in self._root.xpath('.//sub-article[@article-type="ref-report"]'):
            review_id = review.attrib['id']
            license = review.find('.//license').attrib['{http://www.w3.org/1999/xlink}href']
            recommendation = review.find('.//meta-value').text  # TODO: A bit dirty here
            doi = review.find('.//front-stub/article-id[@pub-id-type="doi"]').text
            contributors = [
                {
                    'surname': contrib.find('.//name/surname').text,
                    'given-names': contrib.find('.//name/given-names').text
                } for contrib in review.find('.//front-stub/contrib-group')
                if contrib.tag == 'contrib' and (contrib.find('.//name/surname') is not None)
            ]
            meta = {'review_id': review_id, 'license': license, 'recommendation': recommendation, 'doi': doi, 'contributors': contributors}
            reviews[review_id] = self._parse(review, meta, review_id)
        # Revision comment
        version_changes = self._root.xpath('.//sec[@sec-type="version-changes"]')
        if version_changes:
            # TODO: Check if any nodes need additional parsing
            nodes, edges = self._parse_tree(version_changes[-1])
            self._add_supplementary_edges(nodes, edges)
            if prefix:
                prefix = f'revision_{prefix}'
            revision = IntertextDocument(nodes, edges, prefix or 'revision')
        else:
            revision = None
        return main_doc, reviews, revision

    @classmethod
    def _batch_func(cls, path: Union[PathLike, str]) -> Optional[Tuple[IntertextDocument, Dict[str, IntertextDocument], Optional[IntertextDocument]]]:
        try:
            parser = cls(path)
            doc, reviews, rev = parser()
            if doc is not None:
                return doc, reviews, rev
        except XMLSyntaxError:
            return None

    @classmethod
    def batch_parse(cls, files: List[Union[PathLike, str]]) -> Iterator[Tuple[IntertextDocument, Dict[str, IntertextDocument], Optional[IntertextDocument]]]:
        return super().batch_parse(files)

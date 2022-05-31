from abc import ABC, abstractmethod
import copy
import logging
from typing import List, Dict, Tuple

import pandas as pd
import spacy

from intertext_graph.itgraph import Node, IntertextDocument
from intertext_graph.itgraph import SpanNode


logger = logging.getLogger(__name__)


class SentenceSplitter(ABC):

    @abstractmethod
    def __init__(
            self,
            model: str = 'naive_splitter'
    ):
        self.model_name = model.name
        self.split_type = model.type

    @abstractmethod
    def split(
            self,
            txt: str,
    ) -> List[Tuple[int, int]]:

        char_ix = 0
        ret = []
        for sentence in txt.split('. '):
            if len(sentence) > 0:
                start_ix = char_ix,
                end_ix = char_ix + len(sentence) - 1
                ret.append(start_ix, end_ix)
                char_ix = char_ix + len(sentence) + 2
        return ret


# Class to add sentences to the "p" nodes of an ITG
class IntertextSentenceSplitter:
    def __init__(
            self,
            itg: IntertextDocument,
            splitter: SentenceSplitter = None,
            gold: Dict[str, List[Dict[str, str]]] = {}
    ):
        """
        If neither splitter nor gold is provided, the sentence splitter
        falls back to the default Spacy sentence splitter.
        :param itg: The IntertextDocument to add sentences to
        :param splitter: A SentenceSplitter object.
        :param gold: A list of dictionaries
        """
        self.itg = itg

        if splitter:
            self.splitter = splitter
            self.split_type = splitter.split_type
            self.model_name = splitter.model_name
        elif gold:
            self.gold_sents = gold
            self.split_type = 'from_gold'
            self.model_name = 'from_gold'
        else:
            self.splitter = SpacySplitter(
                spacy.load('en_core_sci_sm')
            )
            self.split_type = self.splitter.split_type
            self.model_name = self.splitter.model_name
            logger.warning(
                f'Falling back to default splitter: '
                f'Type: {self.split_type}, '
                f'Model Name: {self.model_name}'
            )

        return

    def add_sentences_to_itg(self):
        # check if sentence splits come from document or should be computed
        if self.split_type == 'from_gold':
            sentence_nodes = self._get_sents_from_gold_for_itg()
        else:
            sentence_nodes = self._get_sentences_from_itg()

        out = copy.deepcopy(self.itg)
        out.meta.update(
            {
                'sentence_split_type': self.split_type,
                'sentence_split_model': self.model_name
            }
        )

        for n in sentence_nodes:
            out.add_node(n)
            edge = out.get_edge_by_ix(f'{n.src_node.ix}_{n.ix}_link')
            meta_update = {'created_by': type(self).__name__}
            if edge.meta is None:
                edge.meta = meta_update
            else:
                edge.meta.update(meta_update)

        return out

    def _get_sents_from_gold_for_itg(self) -> List[SpanNode]:
        sentence_nodes = match_sentences_from_gold_to_itg(
            self.gold_sents,
            self.itg
        )

        return sentence_nodes

    def _get_sentences_from_itg(self) -> List[SpanNode]:

        sentence_nodes = []
        for node in self.itg.nodes:
            if node.ntype in ['p', 'article-title']:
                boundaries = self.splitter.split(node.content)

                new_sentence_nodes = make_sentence_nodes(
                    node,
                    boundaries
                )

                sentence_nodes += new_sentence_nodes

        return sentence_nodes


def make_sentence_node(
        p_node: Node,
        boundary: Tuple[int, int],
        sentence_ix: int = None,
        sentence_id: str = '',
) -> SpanNode:
    if sentence_ix is not None:
        sentence_node_ix = f'{p_node.ix}@{sentence_ix}'
    elif sentence_id:
        sentence_node_ix = sentence_id
    else:
        raise ValueError('sentence_ix or sentence_id must be provided')

    meta = {
        'created_by': 'IntertextSentenceSplitter'
    }

    sentence_node = SpanNode(
        ntype='s',
        src_node=p_node,
        start=boundary[0],
        end=boundary[1],
        meta=meta
    )
    sentence_node.ix = sentence_node_ix

    return sentence_node


def make_sentence_nodes(
        p_node: Node,
        boundaries: List[Tuple[int, int]]
) -> List[SpanNode]:

    sentence_nodes = []
    for i, boundary in enumerate(boundaries):
        sentence_nodes.append(make_sentence_node(
            p_node, boundary, sentence_ix=i
        ))

    return sentence_nodes


def match_sentences_from_gold_to_itg(
        gold: Dict[str, List[Dict[str, str]]],
        itg: IntertextDocument
) -> List[SpanNode]:

    sentence_nodes = []
    # Iterate over all paragraphs in gold split data
    for paragraph_ix, paragraph in gold.items():
        paragraph_node = itg.get_node_by_ix(paragraph_ix)
        for sentence in paragraph:
            if sentence['text'] != '@q' and sentence['text'] != '':
                # FIXME: handle erroneous sentences elsewhere
                try:
                    boundary = get_span_boundary(sentence['text'].strip(), paragraph_node.content)
                    sentence_node = make_sentence_node(
                        paragraph_node,
                        boundary,
                        sentence_id=sentence['ix']
                    )

                    sentence_nodes.append(sentence_node)
                except ValueError:
                    print('*'*80)
                    print(
                        f'Sentence matching failed for sentence {sentence["ix"]}'
                    )
                    print(sentence['text'])
                    print(paragraph_node.content)
                    pass
                except AssertionError:
                    print('*'*80)
                    print(
                        f'Assertion Error for sentence {sentence["ix"]}'
                    )
                    print(sentence['text'])
                    print(paragraph_node.content)
                    pass

    return sentence_nodes


def get_span_boundary(
        span: str,
        full_txt: str,
) -> Tuple[int, int]:
    start = full_txt.index(span)
    end = start + len(span)

    return start, end


def make_gold_sents_dict_from_df(
        gold_sents_df: pd.DataFrame,
        review_id: str = ''
) -> Dict[str, List[Dict[str, str]]]:

    if review_id:
        gold_sents_df = gold_sents_df.loc[
            gold_sents_df['review_id'] == review_id
        ]
    gold_sents_dict = {}
    for row in gold_sents_df.itertuples():
        paragraph_ix = row.ix.split('@')[0]
        if not paragraph_ix in gold_sents_dict:
            gold_sents_dict[paragraph_ix] = []
        gold_sents_dict[paragraph_ix].append({
            'ix': row.ix,
            'text': row.s_text
        })

    return gold_sents_dict


def make_gold_sents_dict_from_json(
        gold_json: {}
) -> Dict[str, List[Dict[str, str]]]:
    gold_sents_dict = {}
    for paragraph in gold_json['data']:
        gold_sents_dict[paragraph['ix']] = []
        for sentence in paragraph['sentences']:
            gold_sents_dict[paragraph['ix']].append({
                'ix': sentence['sid'],
                'text': sentence['text']
            })

    return gold_sents_dict


def get_span_boundaries(
        list_of_span_txt: List[str],
        full_txt: str
) -> List[Tuple[int, int]]:
    boundaries = []
    for span in list_of_span_txt:
        boundaries.append(get_span_boundary(span, full_txt))

    return boundaries

# TODO: check whether spacy tokenization can be sped up by doing something
# like
# nlp = en_core_sci_sm.load()
# tokenizer = Tokenizer(nlp.vocab)
class SpacySplitter(SentenceSplitter):
    def __init__(
            self,
            spacy_model: spacy.language.Language
    ) -> None:

        self.model = spacy_model
        self.split_type = 'spacy'
        self.model_name = self.get_model_name()

    def split(
            self,
            txt: str,
    ) -> List[Tuple[int, int]]:

        ret = []

        for sent in self.model(txt).sents:
            ret.append((sent.start_char, sent.end_char))

        return ret

    def get_model_name(self):
        return f'{self.model.meta["lang"]}_{self.model.meta["name"]}'

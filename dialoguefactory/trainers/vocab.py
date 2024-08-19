#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# The class Vocabulary has been adapted from the code provided in the YSDA course in Natural Language Processing
# which is licensed under the MIT License.
# Modifications have been made to the original code.
#
# Original repository: https://github.com/yandexdataschool/nlp_course
#
# Original license notice:
#

# MIT License
#
# Copyright (c) 2018 Yandex School of Data Analysis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module implements classes and functions related to the vocabulary used in a list of sentences.
"""
from ..environments.world import compute_unique_list


def filter_words(obj):
    """ Creates a flat list of words.
        If the obj is a list, recursively add all elements of the list
        such that the result is a flat list of words.
    """
    words = []
    if isinstance(obj, str):
        words.append(obj)
    elif isinstance(obj, (list, tuple)):
        for elem in obj:
            words += filter_words(elem)
    return words


def compute_world_vocab(world):
    """
    Find all words that are part of the property keys, property values, and
    the attributes as well.
    """

    words = []
    property_keys = [prop for prop in world.all_properties if prop not in ['var_name', 'door_to']]
    for word in property_keys+world.get_property_values(property_keys):
        words += filter_words(word)

    words += [attr for attr in world.all_attributes if attr != ('main', 'player')]

    return words


def compute_policies_words():
    """ Computes all the words that are used in the rule-based policies. """

    policies_words = [',', '.', '?', ':', 'the', 'entity', "'s",
                      'be', 'is', 'Is', 'say', 'says', 'try', 'tries', 'go', 'goes', 'going',
                      'drop', 'drops', 'dropping', 'get', 'gets', 'getting',
                      'look', 'looks', 'looking', 'open', 'opens', 'opening',
                      'have', 'has',
                      'close', 'closes', 'closing', 'change', 'changes', 'changing',
                      'revealed', 'issued', 'to', 'a',  'in', 'on', 'under',
                      'and', 'then', 'can', 'not', 'no',
                      'whether', 'know', 'item',
                      'permitted', 'if', 'has', 'direction', 'players', 'The', 'path',
                      'position', 'from', 'conflicting', 'with', 'attribute', 'items', 'see', 'sees',
                      'There', 'nothing', 'special', 'about', 'an', 'empty',
                      'response', 'unrecognizable', 'command', 'or', 'itself']
    return list(set(policies_words))


def compute_input_vocab(easy_world, hard_world):
    """ Computes all the input vocabulary words by merging the words returned from the rule-based policies,
        the words from the training environment (easy_world) and the words from the testing environment (hard_world).
    """
    words = compute_policies_words() + compute_world_vocab(easy_world)+compute_world_vocab(hard_world)
    words += ['abstract']
    words = compute_unique_list(words)
    return words


def compute_serializer_words():
    """ Computes the words that are used for serializing the agent's response.
        This includes all the argument keys and the types of serialized objects like list, entity, etc.
        The prefixes 'b' and 'e' mean begin and end correspondingly.
    """
    words = []

    all_arg_keys = ['Rel', 'Arg-PPT', 'Arg-GOL', 'Arg-PRD', 'Arg-PAG', 'Arg-DIR', 'Arg-LOC',
                    'AM-NEG', 'AM-MOD', 'AM-LOC', 'AM-DIR', 'AM-ADV']

    serializer_words = ['list', 'entity', 'sent', 'desc', 'set']
    aux_words = [None, 'abstract']

    for word in all_arg_keys+serializer_words:
        words.append("b"+word)
        words.append("e"+word)

    words += aux_words
    return words


def compute_output_vocab(easy_world, hard_world):
    """ Compute the output vocabulary by merging the serializer words together with the
        input vocabulary words, which might also appear in the agent's output as well.
    """
    words = compute_serializer_words() + compute_input_vocab(easy_world, hard_world)
    words = compute_unique_list(words)
    return words


class Vocabulary:
    """
    Class for creating input and output vocabularies that are used
    for training a machine learning model.

    The class Vocabulary is adapted from the materials of the
    `YSDA Natural Language Processing course <https://github.com/yandexdataschool/nlp_course>`_.
    Credits go to them.

    Attributes
    ----------
    tokens_dict : dict
        A mapping, token (str) to index (int).
    inv_tokens_dict : dict
        An inverse mapping, index (int) to token (str)
    bos : str, optional
        The bos token indicates the beginning of a sequence. It is usually used in seq2seq models 
        in the decoder module to indicate the beginning of the output.
    eos : str, optional
        The eos indicates the end of a sequence. It is usually used for padding the input sequence
        because many input sequences might have different lengths.
        Later, during the encoding process, the eos token can be used to know where the sequence stops.
    bos_ix: int
        The index of the bos.
    eos_ix: int
        The index of the eos.
    """

    def __init__(self, tokens, bos=None, eos=None):
        self.tokens_dict = {t: tix for tix, t in enumerate(tokens)}
        self.inv_tokens_dict = {tix: t for tix, t in enumerate(tokens)}
        if bos is not None and eos is not None:
            self.bos = bos
            self.eos = eos
            self.bos_ix = self.tokens_dict[bos]
            self.eos_ix = self.tokens_dict[eos]

    def __len__(self):
        """ Returns the length of the vocabulary. """
        return len(self.tokens_dict)

    @staticmethod
    def create_vocab(texts, bos, eos):
        """ Creates an instance of Vocabulary from a list of token sequences. """
        tokens = []
        for text in texts:
            tokens += text
        tokens += [bos, eos]
        tokens = set(tokens)
        return Vocabulary(tokens, bos, eos)

    def to_indices(self, texts, max_len=None, add_bos=False, add_eos=False):
        """
        Converts the token sequences (texts) to indices and pads them to the length of the longest
        sequence.

        Parameters
        ----------
        texts : list of lists
            The list of variable length token sequences.
        max_len : int, optional
            The sequence with the longest length. If None, it is computed from the texts.
        add_bos : bool, optional
            Whether to add the bos token at the beginning of each sequence.
        add_eos : bool, optional
            Whether to add the eos token at the end of each sequence.

        Returns
        -------
        indices : list of lists
            The converted index sequences.

        """
        max_len = max_len or max(map(len, texts))
        max_len += 1 if add_bos else 0
        max_len += 1 if add_eos else 0
        indices = []

        for text in texts:
            indices_text = [self.bos_ix] if add_bos else []

            indices_text += [self.tokens_dict[c] for c in text]
            indices_text += [self.eos_ix] if add_eos else []

            # pad sequence
            indices_text += [self.eos_ix]*(max_len - len(indices_text))

            # crop sequence in case max_len is provided, and it's lower
            indices_text = indices_text[:max_len]

            indices.append(indices_text)

        return indices

    def to_text(self, indices):
        """
        Converts a list of indices into sequences of tokens.

        Parameters
        ----------
        indices : list of lists
            A list of token sequences.

        Returns
        -------
        texts : list of lists
            A list of index sequences.

        """
        texts = []
        for ind in indices:
            text = [self.inv_tokens_dict[i] for i in ind]
            texts.append(text)

        return texts

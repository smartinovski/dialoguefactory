#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions that are used by all other modules in this folder.
"""

import functools
from . import components as lc


def auto_fill(args_ignored_ids=None, args_ignored_keys=None):
    """
    Creates a decorator that fills the missing argument parts in the
    :mod:`language.sentences <dialoguefactory.language.sentences>` functions and
    the :mod:`language.queries <dialoguefactory.language.queries>` modules.
    Each argument of the functions is a tuple (argument_value, argument_part).
    If the argument_value is the only one provided,
    the argument_part is automatically filled, and the necessary tuple is created.

    Parameters
    ----------
    args_ignored_ids : list, optional
        The indices of the arguments that should not be filled. The indices start from 0, 1, ...
        0 represents the first argument in the function.

    args_ignored_keys : list, optional
        The keys of the arguments that should not be filled.
        The keys are the argument names. For example, the argument name "player" in sentences.go.
    Returns
    -------
    function
        The function decorator.

    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            arg_dict = {}
            arg_list = list()
            for idx, key in enumerate(args):
                if idx in args_ignored_ids or isinstance(args[idx], tuple):
                    arg_list.append(args[idx])
                else:
                    arg_list.append((args[idx], convert_obj_to_part(args[idx])))

            for key, value in kwargs.items():
                if key in args_ignored_keys or isinstance(value, tuple):
                    arg_dict[key] = value
                else:
                    arg_dict[key] = (value, convert_obj_to_part(value))

            return func(*arg_list, **arg_dict)
        return wrapper
    return decorator


def convert_obj_to_part(obj):
    """ Converts the object to a language component (Word, Phrase, or list). """
    from ..environment import entities as em

    part = obj
    if isinstance(obj, str):
        part = lc.Word(obj)
    elif isinstance(obj, em.BaseEntity):
        part = obj.describe()
    elif isinstance(obj, list):
        new_list = []
        for elem in obj:
            new_list.append(convert_obj_to_part(elem))
        part = new_list

    return part


def returns_same(sentence):
    """ Returns the same object. """
    return sentence


def join_parts_with_connector(parts, connector):
    """ Adds a Word(connector) between each of the language components (Word, Phrase, or Sentence).
    """
    joined = [parts[0]]
    for i in range(1, len(parts)):
        word_connector = lc.Word(connector)
        joined.append(word_connector)
        joined.append(parts[i])
    return joined


def reduce_sentences(sentences, memo=None, add_original=False):
    """
    Reduce the sentences to simpler ones. Please check the components.Sentence.reduce for more information.

    Parameters
    ----------
    sentences : list
        The list of sentences to be reduced. Each sentence should be an instance
        of the class :class:`Sentence <dialoguefactory.language.components.Sentence>` and have the reduce method implemented
        or should define the field sent.customizers['reduce']
        by creating an instance of the class :class:`Customizer <dialoguefactory.language.components.Customizer>`.
        If the reduce method is not implemented, the same sentence
        is returned.
    memo : dict, optional
        A dictionary that prevents reducing the same sentence twice.
    add_original : bool, optional
        Whether to add the original/unreduced form of the sentence to the list.

    Returns
    -------
    reduced : list
        The list of reduced sentences.

    """

    if memo is None:
        memo = dict()

    reduced = []
    for sent in sentences:
        sent_id = id(sent)
        if sent_id not in memo:
            memo[sent_id] = sent
            reduc = sent.reduce()

            if not isinstance(reduc, list):
                reduc = [reduc]
            if len(reduc) == 1 and id(reduc[0]) == id(sent):
                reduced += reduc
            else:
                if add_original:
                    reduced.append(sent)
                reduced += reduce_sentences(reduc, memo, add_original)

    return reduced

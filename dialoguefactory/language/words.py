#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides a function that creates a specific word.
"""
from . import components as lc
from ..environment import entities as em


def create_words_from_string(string_value):
    """ Converts the string into a list of lc.Word-s"""
    tokens = string_value.split(" ")
    words = [lc.Word(t) for t in tokens]

    return words


def create_word_property(item, property_name):
    """
    Converts the item.properties[property_name] into a language component (lc.Phrase, lc.Word) or
    in a list of lc.Word-s.
    """
    property_part = None
    prop = item.get_property(property_name)

    if isinstance(prop, em.BaseEntity):
        property_part = prop.describe()
    elif isinstance(prop, str):

        words = create_words_from_string(prop)

        if len(words) >= 1:
            property_part = words

    elif isinstance(prop, (set, tuple, list)):
        words = []
        for elem in prop:
            words.append(lc.Word(elem))

        property_part = words

    return property_part

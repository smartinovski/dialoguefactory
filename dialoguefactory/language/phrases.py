#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the functions that create a specific phrase.
"""
from . import words as twords
from . import components as lc
from . import sentences as tsentences


def description(entity, elements, add_describer=True):
    """
    Generates a description for the entity based on its attributes and properties.

    Parameters
    ----------
    entity : Entity
        The entity to be described.
    elements : list
        A list of attributes and properties that belong to the entity.
        If the entity does not have a specific attribute or property, but the element is a string,
        it is still added as lc.Word.
    add_describer : bool, optional
        Whether to add meta sentences/additional information to each lc.Word or lc.Phrase.
        Examples of meta sentences added to the phrase "red static bathroom" are:

            - The red static bathroom's color is red.
            - Red is a color.
            - The red static bathroom is static.

    Returns
    -------
    phrase : Phrase
        The phrase that describes the entity.

    """
    parts = []

    phrase = lc.Phrase()
    for elem in elements:

        if isinstance(elem, tuple):
            elem_list = list(elem)
            elem_list_part = twords.create_words_from_string(" ".join(elem))
        else:
            elem_list = [elem]
            elem_list_part = [lc.Word(elem)]

        if elem in entity.properties:
            part = twords.create_word_property(entity, elem)
            if isinstance(part, list):
                parts += part
            else:
                parts.append(part)

            if add_describer:
                prop_val = entity.get_property(elem)

                sent = tsentences.be(([entity, "'s"]+elem_list, [phrase, lc.Word("'s")]+elem_list_part),
                                     ("is", lc.Word("is")),
                                     (None, None),
                                     (prop_val, part))
                sent2 = tsentences.be((prop_val, part),
                                      ("is", lc.Word("is")),
                                      (None, None),
                                      (elem_list if isinstance(elem, tuple) else elem_list[0],
                                       elem_list_part if isinstance(elem, tuple) else elem_list_part[0])
                                      )
                if isinstance(part, list):
                    part[0].meta_sent = [sent, sent2]
                else:
                    part.meta_sent = [sent, sent2]
        elif elem in entity.attributes:
            if isinstance(elem, str):
                part = lc.Word(elem)
                parts.append(part)
            else:
                part = elem_list_part
                parts += part
            if add_describer:
                sent = tsentences.be((entity, phrase),
                                     ("is", lc.Word("is")),
                                     (None, None),
                                     (elem, part))
                if isinstance(part, list):
                    part[0].meta_sent = [sent]
                else:
                    part.meta_sent = [sent]
        elif isinstance(elem, str):
            part = lc.Word(elem)
            parts.append(part)

    if len(parts) == 0:
        parts.append(lc.Word("entity"))

    phrase.parts += parts

    return phrase

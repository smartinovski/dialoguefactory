#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions that extract meaningful information from the sentences.
"""
from ..language import desc_mappers
from ..language import components as lc
from ..environment import entities as em


def have_parse(sent):
    """
    Extracts the constituent arguments of one of the following sentences:

        - <entity> has (neg) <entity_1>, ... , <entity_n> (location)
        - <entity> has not items (location)

    For example, Andy has the small ball and the big ball.
    The (neg) is optional and refers to the negation 'not'.

    """
    if (desc_mappers.have(sent.describers) == sent
            and lc.verb_tense(sent.describers[0].get_arg("Rel")) in lc.PRESENT_TENSES):
        describer = sent.describers[0]
        owner = describer.get_arg("Arg-PAG")
        if not isinstance(owner, em.Entity):
            return None

        possession = describer.get_arg("Arg-PPT")
        if possession is None:
            return None

        neg = describer.get_arg("AM-NEG")

        location = describer.get_arg("AM-LOC")

        if location is not None and not isinstance(location, list):
            return None
        return owner, possession, neg, location
    return None


def elem_exists_parse(sent):
    """
    Extracts the entity, element (property or attribute), and a negation (if it exists)
    if the sentence matches one of the following formats:

        - <entity> has (not) <property>
        - <entity> has (not) <attribute>
        - <entity> has (not) direction <direction>

    The (neg) is optional and refers to the negation 'not'.
    """
    if (desc_mappers.have(sent.describers) == sent
            and lc.verb_tense(sent.describers[0].get_arg("Rel")) in lc.PRESENT_TENSES):
        describer = sent.describers[0]
        ent = describer.get_arg("Arg-PAG")
        elem = describer.get_arg("Arg-PPT")
        pneg = describer.get_arg("AM-NEG")
        loc = describer.get_arg("AM-LOC")
        if loc is None and isinstance(ent, em.Entity):
            if isinstance(elem, list) and len(elem) == 2 and elem[0] == 'direction':
                pkey = elem[1]
            elif isinstance(elem, list):
                pkey = tuple(elem)
            else:
                pkey = elem
            return ent, pkey, pneg
    return None

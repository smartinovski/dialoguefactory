#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides the functions that help all other modules in this folder to do their operations.
"""
from ..language import sentences as tsentences
from ..environment import entities as em
from ..state import kn_helpers


def join_el_conn(elements, connector, last_conn=None):
    """ Adds the connector between the elements of the lists.
        The last_conn connects the last two elements, which might differ from the connector.
        The default one is 'and'.
        This function returns [elem1, connector, elem2, connector, elem3, last_conn, elem4] if the list
        has 4 elements. This is useful in responses where you want to list objects in a sentence like:
        "The <entity> contains the toy apple, toy carrot, and a book", where the last connector differs.
    """
    if last_conn is None:
        last_conn = 'and'
    if isinstance(elements, (list, set)):
        joined = []
        for idx, el in enumerate(elements):
            joined.append(el)
            if idx < len(elements) - 2:
                joined.append(connector)
            elif idx != len(elements)-1:
                joined.append(last_conn)

        return joined
    else:
        return elements


def check_can_not(sentences, verb):
    """
    Checks whether a Sentence from a list of sentences contains this pattern: "can not <verb>."

    """
    result = False
    for sent in sentences:
        if len(sent.describers) == 1:
            describer = sent.describers[0]
            if (describer.get_arg("AM-MOD") == 'can' and describer.get_arg("AM-NEG") == 'not'
                    and describer.get_arg("Rel") == verb):
                result = True
                break
    return result


def extract_tries_sent(sentence, world):
    """ Extracts the inner sentence from the following one:

            <player> tries <inner_sentence>

        In the following example: "Hannah tries changing the toy's color",
        the "changing the toy's color" is extracted.
    """
    tries_describer = sentence.describers[0]
    player = tries_describer.get_arg('Arg-PAG')
    if player != sentence.speaker:
        player = None
    inner_utter = tries_describer.get_arg('Arg-PPT')
    if isinstance(player, em.Entity):
        player = getattr(world, player.properties.get("var_name"), None)
    else:
        player = None
    if sentence != tsentences.tries((player, None),
                                    (None, None),
                                    (None, None),
                                    ("tries", None),
                                    (inner_utter, None)):
        inner_utter = None

    return inner_utter, player


def item_path(item):
    """ Returns all locations of the item that lead to the top location.
        The list includes the item itself.
        For example, if the item is located on a shelf in a kitchen's drawer, the path will be:
        [item, shelf, kitchen's drawer, kitchen].
    """
    loc_path = []
    curr_loc = item
    while True:

        loc_path.append(curr_loc)
        if curr_loc == curr_loc.properties['location'][1]:
            break
        curr_loc = curr_loc.properties['location'][1]
    return loc_path


def check_desc_collision(entity, elements):
    # return the collision elements.
    # to check which elements collide go through desc.elements and check which ones are seen and are
    # avaiable in both of the items

    for el in elements:
        if el in entity.attributes:
            entity.attr_seen[el] = None
        elif el in entity.properties:
            entity.prop_seen[el] = entity.properties[el]
    shared_el = []
    for obj in entity.world.obj_list:
        elems = kn_helpers.shared_elements([entity], obj, elements, True, False)
        if len(elems) > 0:
            print (elems, entity.properties['var_name'], obj.properties['var_name'], entity.prop_seen, obj.prop_seen)
        shared_el.extend(elems)

    # the elements are not seen so you do not have to check if
    # previously they had
    for el in elements:
        if el in entity.attr_seen:
            del entity.attr_seen[el]
        elif el in entity.prop_seen:
            del entity.prop_seen[el]

    return shared_el

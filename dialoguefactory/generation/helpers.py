#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions that are used by all other modules in this folder.
"""
import copy
import random
import inspect
import logging


def generate_primitive_structure(primitive_templates):
    """
    Returns a list that contains a single tuple. The tuple's first value is
    the string 'primitive' and the second is a randomly selected template (function)
    from a list of primitive templates.
    """
    list_of_tuples = []
    random_template = random.choice(primitive_templates)
    list_of_tuples.append(('primitive', random_template))

    return list_of_tuples


def generate_complex_structure(dia_generator,
                               depth=0,
                               max_depth=2):
    """
    Prepares a skeleton/structure for a random complex template. The templates are functions and can contain
    other primitive or complex templates as parameters.

    The skeleton consists of a list of tuples. Each tuple is in the format
    ('complex', rand_complex_template, num_templates), where num_templates
    indicates the number of constituent templates the complex template is made of.
    The constituent templates follow after in the same list.

    The skeleton is prepared for the select_complex_template function.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The dialogue generator.
    depth : int, optional
        The current depth of the structure. The value starts from 0.
    max_depth : int, optional
        The maximum depth of the structure. The default is 2.

    Returns
    -------
    list_of_tuples : list
        A list of tuples.

    """
    depth += 1
    template_rand = random.choice(dia_generator.complex_templates)
    params = dict(inspect.signature(template_rand).parameters)

    list_of_tuples = []
    for key in list(params.keys()):
        if any(list(map(key.startswith, dia_generator.primitive_template_names))):
            list_of_tuples += generate_primitive_structure(dia_generator.primitive_templates)
        elif (any(list(map(key.startswith, dia_generator.any_template_names)))
              or any(list(map(key.startswith, dia_generator.complex_template_names)))):

            count_prim = len(dia_generator.primitive_templates)
            count_complex = len(dia_generator.complex_templates)
            total_count = count_prim + count_complex
            template_type = random.choices(['primitive', 'complex'],
                                          weights=[count_prim/total_count,
                                                  count_complex/total_count], k=1)[0]

            if ((any(list(map(key.startswith, dia_generator.any_template_names))) and template_type == 'primitive')
                    or depth >= max_depth):
                list_of_tuples += generate_primitive_structure(dia_generator.primitive_templates)
            else:
                added_statements = generate_complex_structure(dia_generator,
                                                              depth,
                                                              max_depth)
                list_of_tuples += added_statements

    list_of_tuples.insert(0, ('complex', template_rand, len(list_of_tuples)))
    return list_of_tuples


def generate_property_val(dia_generator, candidate_keys):
    """ Selects a random key from a list of property keys and generates a random property value. """
    random_key = random.choice(candidate_keys)
    if random_key == 'location':
        random_val = [random.choice(dia_generator.world.location_positions),
                      random.choice(dia_generator.world.obj_list)]
    elif (isinstance(random_key, tuple) and len(random_key) == 2
          and random_key[0] in dia_generator.world.directions and random_key[1] == 'obstacle'):
        random_val = random.choice(dia_generator.world.obj_list)
    elif random_key in dia_generator.world.directions:
        random_val = random.choice(dia_generator.world.places)
    else:
        random_val = random.choice(dia_generator.world.get_property_values(candidate_keys))

    return random_val


def find_policy(policy_db, policy_class):
    """ Find the policy from the list of policies based on the policy class """
    found_policy = None
    for policy in policy_db:
        if isinstance(policy, policy_class):
            found_policy = policy
            break
    return found_policy


def create_unk_item(item, similar_elements, item_description=None):
    """
    Creates an item that is not part of the world based on the elements of a concrete item that is part of the world.
    Additionally, if the new item's description is not provided, it is taken from the <item>'s description.

    Parameters
    ----------
    item : Entity
        The concrete item that is used to fetch the elements and potentially the
        item's description that is needed for the new item.
    similar_elements : list
        A list of properties and attributes that will be fetched from the <item>.
    item_description : BaseDescription
        The item_description is used for the generate_description(...) method which
        dictates the order and the elements used in the item's description.

    Returns
    -------
    unk_item : BaseEntity
        The new item is not part of the world and has the "abstract" attribute to indicate the fact.

    """
    from ..environment import entities as em
    unk_item = em.BaseEntity()
    for elm in similar_elements:
        if elm in item.properties:
            unk_item.properties[elm] = item.properties[elm]
        elif elm in item.attributes:
            unk_item.attributes[elm] = item.attributes[elm]

    unk_item.attributes["abstract"] = None

    if item_description is None:
        if item.description is None:
            item_description = item.generate_description()
        else:
            item_description = item.description.mycopy()

    unk_item.description = item_description
    unk_item.description.item = unk_item
    unk_item.description.elements = similar_elements
    unk_item.description.mandatory = [True]*len(similar_elements)

    unk_item.description.generate_description(False)

    return unk_item


def unk_from_desc(item):
    """ Creates an abstract item from a concrete item.
        The new item is created using some description elements of the concrete item.
    """
    random_item_desc = item.generate_description()
    cand_elements = copy.copy(random_item_desc.elements)

    for elem in ['the', 'entity']:
        if elem in cand_elements:
            cand_elements.remove(elem)
    included_elements = []
    for elem in cand_elements:
        if random.choice([0, 1]) == 1:
            included_elements.append(elem)
    if len(included_elements) == 0:
        included_elements.append(cand_elements[-1])
    item = create_unk_item(item, included_elements, random_item_desc)
    return item


def extract_knowledge(stat, memo=None):
    """ Extracts the meta sentences from a Sentence or a Phrase. It includes the meta sentences
        from all inner sentences, phrases or words that a phrase or sentence might contain.
    """
    from ..language import components as lc

    if memo is None:
        memo = dict()

    stat_id = id(stat)
    memo_stat = memo.get(stat_id)
    if memo_stat is not None:
        return []
    memo[stat_id] = stat

    knowledge = []
    knowledge += stat.meta_sent

    for sent in stat.meta_sent:
        knowledge += extract_knowledge(sent, memo)

    if isinstance(stat, (lc.Sentence, lc.Phrase)):
        for part in stat.parts:
            if isinstance(part, (lc.Sentence, lc.Phrase, lc.Word)):
                knowledge += extract_knowledge(part, memo)

    return knowledge


def reduce_and_extract(sentences, add_original=False):
    """ Reduces the sentences and extracts the meta sentences from them.
        If the add_original is True, the original sentences are added to the final list.
    """
    from ..language.helpers import reduce_sentences

    reduce_sent = reduce_sentences(sentences, None, add_original)
    all_knowledge = []
    for utt in reduce_sent:
        all_knowledge.append(utt)
        all_knowledge += reduce_sentences(extract_knowledge(utt), None, add_original)
    return all_knowledge


def make_dynamic_copy(pol):
    """ Makes a new instance of the policy class and assigns the same class member references
        as the old one.
    """
    attributes = vars(pol)
    pol_class = pol.__class__
    new_pol = pol_class.__new__(pol_class)
    for key, val in attributes.items():
        setattr(new_pol, key, val)

    return new_pol


def configure_logging(filename, level=None, format_=None):
    """ Configures the level and format of the logging."""
    if level is None:
        level = logging.ERROR
    if format_ is None:
        format_ = '%(asctime)s:%(levelname)s - %(message)s'
    logging.basicConfig(filename=filename, level=level,
                        format=format_
                        )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the classes needed to describe an object/entity.
"""
import copy
import random

from ..state import kn_helpers


def permute_list_of_lists(lists, fixed_elements=None, random_gen=None):
    """
    Permutes the elements of the individual lists contained in one main list.

    Parameters
    ----------
    lists : list
        A list that contains multiple lists.
    fixed_elements : list, optional
        The indices that should not be permuted.
    random_gen : random.Random, optional
        A random number generator. It is used to shuffle the elements.

    Returns
    -------
    lists : list
        The list of lists that have the permuted elements.


    """
    if fixed_elements is None:
        fixed_elements = list()

    nonfixed_indices = [idx for idx in range(len(lists[0])) if idx not in fixed_elements]
    nonfixed_elements = [[lists[idx][idy] for idy in nonfixed_indices] for idx in range(len(lists))]

    if random_gen is None:
        random_gen = random.Random()
    random_gen.shuffle(nonfixed_indices)
    for idx in range(len(nonfixed_elements)):
        for idy in range(len(nonfixed_elements[idx])):
            lists[idx][nonfixed_indices[idy]] = nonfixed_elements[idx][idy]

    return lists


class BaseDescription:
    """
    Generates the elements that are used to describe an entity. For example, the [size, color, type] might be
    used to describe an apple.

    Attributes
    ----------
    item : BaseEntity or Entity
        The item that is described.
    mandatory : list
        A list of True-s and False-s indicating whether the elements (self.elements)
        used for the description are mandatory.
        True represents mandatory, and False represents optional.
    elements : list
        The list of elements that are used to describe the item.
        These can be properties and attributes of the item.
        These elements are selected from the list of candidates.
    cand_elements : list
        The list of candidate elements. The self.elements are selected from this list.
    cand_mandatory : list
        This list of True-s and False-s indicates whether the candidate elements are mandatory or not.
    random_gen : random.Random
        The random generator is used to pick the optional arguments from the list of candidate elements.

    """
    def __init__(self, item=None, mandatory=None, elements=None,
                 cand_elements=None, cand_mandatory=None, random_gen=None):
        self.item = item
        self.mandatory = list() if mandatory is None else mandatory
        self.elements = list() if elements is None else elements
        self.cand_elements = list() if cand_elements is None else cand_elements
        self.cand_mandatory = list() if cand_mandatory is None else cand_mandatory
        if cand_mandatory is None and cand_elements is not None:
            self.cand_mandatory = [False] * len(cand_elements)

        self.random_gen = random_gen if random_gen is not None else random.Random()

    def __eq__(self, other):
        """ Checks whether two descriptions are equal. """
        result = False
        if isinstance(other, BaseDescription) and type(self) is type(other):
            if (len(self.elements) > 0 and self.elements == other.elements
                    and len(self.mandatory) > 0 and self.mandatory == other.mandatory):
                result = True
            elif len(self.elements) == 0 and len(other.elements) == 0 and self.cand_elements == other.cand_elements:
                result = True

        return result

    def mycopy(self):
        """  Shallow copies the members of the description. """
        cls = self.__class__
        result = cls.__new__(cls)
        setattr(result, 'item', self.item)
        setattr(result, 'mandatory', copy.copy(self.mandatory))
        setattr(result, 'elements', copy.copy(self.elements))
        setattr(result, 'cand_elements', copy.copy(self.cand_elements))
        setattr(result, 'cand_mandatory', copy.copy(self.cand_mandatory))
        setattr(result, 'random_gen', copy.copy(self.random_gen))
        return result

    def pick_random_elements(self):
        """ Randomly selects the optional description elements, and
            it removes the rest of the optional elements from the self.elements and self.mandatory lists.
            For this function to work, the fields self.elements and self.mandatory must already be filled. """
        indices_included = []
        for idx in range(len(self.mandatory)):
            if self.mandatory[idx] is True or (self.mandatory[idx] is False and self.random_gen.randint(0, 1) == 1):
                indices_included.append(idx)

        self.elements = [self.elements[idx] for idx in range(len(self.elements)) if idx in indices_included]
        self.mandatory = [self.mandatory[idx] for idx in range(len(self.mandatory)) if idx in indices_included]

    def filter_candidate_elements(self, cand):
        """
        Selects a set of elements from the list of candidate elements that uniquely describe the item.

        Priority is given to the elements that are already seen by the agent. The non-seen elements needed for the
        entity's description to be unique are kept to the minimum.

        Parameters
        ----------
        cand : list
            The candidate is a list of two lists. The first list contains the elements, and the second one is
            a list of False-s and True-s, indicating whether you prefer the elements to be mandatory or not.
            If you do not have a preference you can leave all values False since in this function
            a check is done whether the optional arguments need to be mandatory anyway.

        Returns
        -------
        elements : list
            A list of elements that are used for the entity's description
        mandatory : list
            A list of False-s and True-s indicating whether the element is mandatory or not (with True being mandatory).

        """
        seen_indices = []
        not_seen_indices = []
        for idx, el in enumerate(cand[0]):
            if el in self.item.prop_seen or el in self.item.attr_seen:
                seen_indices.append(idx)
            else:
                not_seen_indices.append(idx)

        new_cand = [[], []]
        for idx in seen_indices+not_seen_indices:
            new_cand[0].append(cand[0][idx])
            new_cand[1].append(cand[1][idx])
        cand = new_cand
        elements = []
        mandatory = []
        unique = False
        first_unique = True
        similar_objs = self.item.world.obj_list

        for idx, el in enumerate(cand[0]):
            if el in self.item.properties or el in self.item.attributes:
                elements.append(el)
                # open and locked are changeable attributes.
                if el not in ['open', 'locked']:
                    if not unique:
                        similar_objs = kn_helpers.find_similar_objs(similar_objs, self.item, el)
                        if len(similar_objs) == 1 and similar_objs[0] == self.item:
                            unique = True
                mandatory.append(cand[1][idx] is True or not unique or (unique and first_unique))

                if unique and first_unique:
                    first_unique = False

        if unique is False:
            return [], []

        new_el = []
        new_mand = []

        for idx, el in enumerate(elements):
            if el in self.item.prop_seen or el in self.item.attr_seen:
                new_el.append(el)
                new_mand.append(mandatory[idx])
            else:

                # do not reveal too much information at once
                # if the element is not revealed
                if mandatory[idx] is False:
                    break
                else:
                    new_el.append(el)
                    new_mand.append(mandatory[idx])

        elements = new_el
        mandatory = new_mand

        return elements, mandatory

    def generate_description(self, random_pick=True):
        """ Generates and updates the self.elements and self.mandatory if they are empty.
            Additionally, it can pick which optional elements from the self.elements list to be included.
        """
        if len(self.elements) == 0:
            self.generate_elements()
        if random_pick:
            self.pick_random_elements()

    def generate_elements(self):
        """ Generates the elements and the mandatory list from the list of candidate elements."""
        self.elements, self.mandatory = self.filter_candidate_elements(permute_list_of_lists([self.cand_elements,
                                                                                              self.cand_mandatory],
                                                                                             random_gen=self.random_gen))


class Description1(BaseDescription):
    """ Describes the entity in the following format:

            "the" cand_elem1 cand_elem2 ... "entity"

    """
    def __init__(self, item=None, mandatory=None, elements=None,
                 cand_elements=None, cand_mandatory=None, random_gen=None):
        super().__init__(item, mandatory, elements, cand_elements, cand_mandatory, random_gen)

    def generate_description(self, random_pick=True):
        """ Calls the parent function to generate the self.elements and self.mandatory if they are not initialized.
            It additionally adds the string 'entity' if the property 'type' is not used for the description.
            For example, if the description consist just of the article 'the' and the attribute 'static',
            then it is necessary to add 'entity' to complete the description 'the static entity'.
            If the property 'type' is in self.elements, it is positioned at the end of the list.
            For example, "the apple big red" makes no sense in the English language,
            and "the big red apple" is used instead.
        """
        super().generate_description(random_pick)
        if len(self.elements) > 0:
            if 'type' not in self.elements and 'entity' not in self.elements:
                self.elements.append('entity')
                self.mandatory.append(True)
            if 'the' not in self.elements:
                self.elements.insert(0, 'the')
                self.mandatory.insert(0, True)
            if 'abstract' in self.item.attributes and 'the' in self.elements:
                idx = self.elements.index('the')
                del self.elements[idx]
                del self.mandatory[idx]

            if 'type' in self.elements and 'entity' in self.elements:
                idx = self.elements.index('entity')
                del self.elements[idx]
                del self.mandatory[idx]

            if 'type' in self.elements:
                idx = self.elements.index('type')
                self.elements.remove('type')
                self.elements.append('type')
                mand_val = self.mandatory[idx]
                del self.mandatory[idx]
                self.mandatory.append(mand_val)

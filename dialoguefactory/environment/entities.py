#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the classes that represent the entities/objects in the simulation.
"""

import copy
import random

from ..language import components as lc
from . import descriptions as tdescriptions

from ..language import phrases as tphrases
from ..language import sentences as tsentences


class BaseEntity:
    """
    Creates an entity that is abstract (not part of the world).

    For example, in the following sentence: Andy, get a red apple, a red apple is BaseEntity
    because it can refer to more than one entity in the world.
    Please refer to the Entity class if you want to create an entity that is part of the world.

    Attributes
    ----------
    properties : dict
        The entity can contain properties like size, color, and material.
    attributes: dict
        The entity can contain attributes like open, static, place, player, etc. This dictionary always has
        values None. This is what makes the attributes different from the properties.
        In the future, we plan to replace the attributes type with a set since the dictionary values are always None.
    objects: list
        The list of other entities the entity might contain. For example, this parameter can be used
        when the entity is a container, place, supporter, or hollow.
    undo_changes: list
        A list of functions that undo the changes made to the entity.
    description: Description
        The description of the entity. The description uses properties and attributes to describe
        the entity. Please check the descriptions.Description for more information.
    descriptions: dict
        It stores the previously generated descriptions after they are converted to Phrase-s. It is done,
        so that the phrases can be reused and time can be saved.
    random_gen : random.Random
        The random generator is used instead of random, so that if the dialogue is run again
        the same generation process will proceed.

    """
    def __init__(self, properties=None, attributes=None, objects=None, undo_changes=None, random_gen=None):
        self.properties = ({} if properties is None else properties)
        self.attributes = ({} if attributes is None else attributes)
        self.objects = ([] if objects is None else objects)
        self.undo_changes = ([] if undo_changes is None else undo_changes)
        self.description = None
        self.descriptions = dict()
        self.random_gen = random.Random() if random_gen is None else random_gen

    def __eq__(self, other):
        """
        Checks whether two entities are equal.

        Comparing the two entities is only possible if the properties do not contain any entities. If they do, the
        __eq__ function might be stuck in an infinite recursion.

        Parameters
        ----------
        other : Entity
            The other entity to be compared with self.

        Returns
        -------
        is_equal: bool
            Indicates whether the two entities are the same.

        """
        is_equal = False

        if isinstance(other, BaseEntity):
            is_equal = self.properties == other.properties and self.attributes == other.attributes
        return is_equal

    def __hash__(self):
        """
        Computes the hash for the Entity.

        Returns
        -------
        hash_code : int
            An integer value representing the hash code.

        """
        hash_code = hash(lc.prepare_hash(set(list(self.properties.items())+list(self.attributes.items()))))

        return hash_code

    def mycopy(self, memo):
        """
        Makes a copy of the Entity object so that any changes to the original object do not affect the copied one.

        Parameters
        ----------
        memo : dict
            A dictionary that prevents a recursive loop. It stores the entities by id and checks if the current entity
            is already copied.

        Returns
        -------
        result: Entity
            The copied entity.

        """
        self_id = id(self)

        result = memo.get(self_id)
        if result is not None:
            return result

        cls = self.__class__
        result = cls.__new__(cls)

        memo[self_id] = result

        setattr(result, 'undo_changes', list())

        result.properties = lc.mycopy_el(self.properties, memo)
        result.attributes = lc.mycopy_el(self.attributes, memo)
        result.objects = lc.mycopy_el(self.objects, memo)
        if self.description is not None:
            setattr(result, 'description', self.description.mycopy())
        else:
            setattr(result, 'description', self.description)
        setattr(result, 'descriptions', copy.copy(self.descriptions))

        return result

    def describe(self, elements=None, add_describer=True):
        """
        Describes an Entity based on the elements using an instance of the Phrase class.

        Parameters
        ----------
        elements : list of strings
            A list of property and attribute keys or other strings that describe the Entity. These elements
            are later converted to a Phrase object. If the elements are not provided, first, a description is generated.
        add_describer : bool
            Whether to add describers for each of the Word-s in the Phrase.
            Please refer to :func:`phrases.description() <dialoguefactory.language.phrases.description>` for more information.

        Returns
        -------
        phrase: Phrase
            The Phrase that describes the entity.

        """
        if elements is None:
            if self.description is None:
                generated_desc = self.generate_description()
                self.set_description(generated_desc)
            included_elements = self.description.elements
        else:
            included_elements = elements
        prop_key_val = dict()
        for el in included_elements:
            if el in self.properties:
                prop_key_val[el] = self.properties[el]
            elif el in self.attributes:
                prop_key_val[el] = self.attributes[el]
            else:
                prop_key_val[el] = None

        prop_key_val = frozenset(lc.prepare_hash(list(prop_key_val.items())))
        if prop_key_val not in self.descriptions:
            phrase = tphrases.description(self, included_elements, add_describer)
            self.descriptions[prop_key_val] = phrase

            def undo_desc(ent=self, prop_key_value=prop_key_val):
                del ent.descriptions[prop_key_value]
            self.undo_changes.append(undo_desc)

        else:
            phrase = self.descriptions[prop_key_val]
        return phrase

    def generate_description(self):
        """ Generates a description using all the properties and attributes of the entity.
            For example, if the entity has a color property 'blue' and an attribute 'container',
            the description will be 'blue container'
        """
        all_elements = list(self.properties.keys())+list(self.attributes.keys())
        mandatory = [True] * len(all_elements)
        base_desc = tdescriptions.BaseDescription(self, mandatory, all_elements)
        return base_desc

    def set_description(self, description):
        """ Sets the entity description and saves the previous one. """
        self.description = description

    def get_property(self, property_name):
        """ Get the property value given the property key. Return an empty string if the property is non-existent. """
        return self.properties.get(property_name, '')


class Entity(BaseEntity):
    """
    Creates an instance of an entity that belongs to the physical world.

    Attributes
    ----------
    world: World
        The world that the entity belongs to.
    prop_seen: dict
        A mapping property_key : property_value, that indicates what properties are revealed in the context.
    prop_seen_neg: dict
        A mapping property key => list of property values that are not equal to the correct property value.
        For example, the entity's size might be 'small', and the list of property values might be ['medium', 'large'].
        The properties have to be revealed in the context.
    attr_seen : dict
        A mapping attribute : None that indicates what attributes are revealed in the context.
        In the future, this dictionary can be replaced with a set since all values of the dictionary are None.
    attr_seen_neg: dict
        A mapping attribute : None that indicates what attributes the entity does not have.
        In the future, the dictionary can be replaced with a set since all values of the dictionary are None.
    elem_exists: set
        A set of elements (properties and attributes) that the entity has and that are revealed in the context.
    elem_not_exists: set
        A set of elements (properties and attributes) that the entity does not have and that
        this information is revealed in the context.

    """
    def __init__(self, world=None, properties=None, attributes=None, objects=None):
        undo_changes = world.undo_changes if world is not None else list()
        super().__init__(properties, attributes, objects, undo_changes)
        self.world = world
        self.prop_seen = dict()
        self.prop_seen_neg = dict()
        self.attr_seen = dict()
        self.attr_seen_neg = dict()
        self.elem_exists = set()
        self.elem_not_exists = set()

    def change_world(self, new_world):
        """ Changes the world that the entity is part of. """
        self.world = new_world
        self.undo_changes = new_world.undo_changes

    def mycopy(self, memo):
        """
        Makes a copy of the Entity object so that any changes to the original object do not affect the copied one.

        Parameters
        ----------
        memo : dict
            A dictionary that prevents a recursive loop. It stores the entities by id and checks if the current entity
            is already copied.

        Returns
        -------
        result: Entity
            The copied entity.

        """
        self_id = self.properties.get("var_name")

        if self_id is None:
            self_id = id(self)

        result = memo.get(self_id)
        if result is not None:
            return result

        cls = self.__class__
        result = cls.__new__(cls)

        memo[self_id] = result

        setattr(result, 'undo_changes', list())

        result.properties = lc.mycopy_el(self.properties, memo)
        result.attributes = lc.mycopy_el(self.attributes, memo)
        result.objects = lc.mycopy_el(self.objects, memo)
        if self.description is not None:
            setattr(result, 'description', self.description.mycopy())
        else:
            setattr(result, 'description', None)

        setattr(result, 'descriptions', copy.copy(self.descriptions))
        setattr(result, 'world', self.world)
        setattr(result, 'prop_seen', copy.copy(self.prop_seen))
        setattr(result, 'attr_seen', copy.copy(self.attr_seen))
        setattr(result, 'prop_seen_neg', copy.copy(self.prop_seen_neg))
        setattr(result, 'attr_seen_neg', copy.copy(self.attr_seen_neg))
        setattr(result, 'elem_exists', copy.copy(self.elem_exists))
        setattr(result, 'elem_not_exists', copy.copy(self.elem_not_exists))

        return result

    def __eq__(self, other):
        """
        Checks whether two entities are equal.

        In the case where the Entity does not have a var_name, comparing the two entities is
        only possible if the properties do not contain entities. If they do, the
        __eq__ function might be stuck in an infinite recursion.

        Parameters
        ----------
        other : Entity
            The other entity to be compared with self.

        Returns
        -------
        is_equal: bool
            A boolean value indicates whether the two entities are the same.

        """
        is_equal = False

        if isinstance(other, Entity):
            is_equal = self.properties['var_name'] == other.properties['var_name']

        return is_equal

    def __gt__(self, other):
        """
        Checks whether the entity is greater than another entity.

        The comparison is made based on the property 'size'. If the property 'size' is not available,
        None is returned.
        """
        result = None
        if isinstance(other, Entity) and 'size' in self.properties and 'size' in other.properties:

            order_size = {('very', 'small'): -1, 'small': 0, 'medium': 1, 'big': 2, ('very', 'big'): 3}
            self_size = self.properties['size']
            other_size = other.properties['size']

            if isinstance(self_size, list):
                self_size = tuple(self_size)
            if isinstance(other_size, list):
                other_size = tuple(other_size)

            result = order_size[self_size] > order_size[other_size]
        return result

    def __hash__(self):
        """
        Computes the hash for the Entity.

        Returns
        -------
        hash_code : int
            An integer value representing the hash code.

        """
        if "var_name" in self.properties:
            hash_code = hash(self.properties["var_name"])
        else:
            hash_code = hash(lc.prepare_hash(set(list(self.properties.items())+list(self.attributes.items()))))

        return hash_code

    def select_unique_descriptions(self, cand_descriptions=None):
        """
        Selects the unique descriptions from the candidate descriptions.

        If the candidate descriptions are not provided,
        they are instantiated from the world.all_description_objects.

        Parameters
        ----------
        cand_descriptions : list
            A list of :class:`~dialoguefactory.environment.descriptions.BaseDescription` instances
            that are used to describe the world's entities.

        Returns
        -------
        seen : list
            The list of unique descriptions where all the description's elements are seen by the players.
        not_seen : list
            The list of unique descriptions where all the description's elements are not seen by the players.
        partially_seen : list
            The list of unique descriptions where some of the description's elements are seen by the players.

        """
        unique_descriptions = []
        if cand_descriptions is None:
            cand_descriptions = []
            for descr in self.world.all_description_objects:
                new_instance = descr.mycopy()
                new_instance.item = self
                # do not copy the random_gen
                new_instance.random_gen = descr.random_gen
                cand_descriptions.append(new_instance)

        seen = []
        not_seen = []
        partially_seen = []
        for desc in cand_descriptions:
            desc.generate_description()
            if len(desc.elements) > 0:
                unique_descriptions.append(desc)
                seen_elems = []
                not_seen_elems = []
                filtered_elems = []
                for elem in desc.elements:
                    if elem not in ['the', 'entity']:
                        if elem in self.prop_seen or elem in self.attr_seen:
                            seen_elems.append(elem)
                        else:
                            not_seen_elems.append(elem)
                        filtered_elems.append(elem)

                if len(seen_elems) == len(filtered_elems):
                    seen.append(desc)
                elif len(not_seen_elems) == len(filtered_elems):
                    not_seen.append(desc)
                else:
                    partially_seen.append(desc)
        return seen, not_seen, partially_seen

    def generate_description(self, cand_descriptions=None, random_gen=None, relaxed=True):
        """
        Generates a description of the entity.

        Parameters
        ----------
        cand_descriptions : list, optional
            A list of candidate descriptions (instances of the class BaseDescription).
        random_gen : random.Random, optional
            The random_gen makes sure that the dialogue always has the same randomization in case
            the dialogue is restarted.
        relaxed : bool, optional
            If False, when generating the descriptions,
            priority is given to the descriptions generated for the first time (the agent has not seen any of
            the entity's properties or attributes).
            Otherwise, priority is given to the descriptions where the agent has seen some properties/attributes.

        Returns
        -------
        description : Description
            The description of the entity.

        """

        unique_seen, unique_not_seen, unique_partially_seen = self.select_unique_descriptions(cand_descriptions)
        description = None

        if len(unique_seen) > 0:
            description = self.random_gen.choice(unique_seen)
        elif len(unique_partially_seen) > 0 and relaxed:
            description = self.random_gen.choice(unique_partially_seen)
        elif len(unique_not_seen) > 0:
            description = self.random_gen.choice(unique_not_seen)

        return description

    def top_location(self):
        """ Compute the top location of an item. For example, if the item is in a container and
            the container is in a room, then the top location of the item is the room.
        """

        if 'location' not in self.properties:
            return None
        item_location = self.properties['location'][1]
        prev_location = item_location

        while True:
            if 'location' in item_location.properties:
                item_location = item_location.properties['location'][1]
                if prev_location != item_location:
                    prev_location = item_location
                else:
                    break
            else:
                break

        return item_location

    def validate_reachability(self, player, location_entity, neg_res=None):
        """
        Checks whether the entity (self) is reachable to the player at a specific location.

        Parameters
        ----------
        player : Entity
            The player that executes the action.
        location_entity : Entity
            The location entity where self is found.
        neg_res : Sentence
            The negative response in case the entity is not reachable.
            For example, <player> can not get <self>.

        Returns
        -------
        log : list
            Returns an empty list if the item is reachable to the player at the location.
            If the entity is not reachable, return the negative response concatenated together with the reason why.
        """

        log = []
        player_top_loc = player.top_location()
        if 'player' not in player.attributes:
            log.append(tsentences.cont([neg_res, tsentences.be(player, 'is', 'not', 'player')]))

        if (('type' in self.properties and self.properties['type'] != 'door') or 'type' not in self.properties) and location_entity.top_location() != player_top_loc:
            log.append(tsentences.cont([neg_res, tsentences.be([player, "'s", 'location'],
                                       'is', 'not', ['in', location_entity.top_location()])]))

        if ('type' in self.properties and self.properties['type'] == 'door' and
                "door_to" in self.properties and
                self.properties["door_to"] != player_top_loc and
                self.properties["location"][1] != player_top_loc and
                location_entity == self.properties["location"][1]):

            res1 = tsentences.be([player, "'s", 'location'],
                                 'is',
                                 'not',
                                 ['in', self.properties["door_to"]])
            res2 = tsentences.be([player, "'s", 'location'],
                                 'is',
                                 'not',
                                 ['in', self.properties["location"][1]])
            log.append(tsentences.cont([neg_res, res1, res2]))

        if (("container" in location_entity.attributes and
                self.properties["location"][1] != location_entity.top_location())):
            curr_loc = location_entity
            log_locked = []
            log_not_open = []

            while True:
                if curr_loc == curr_loc.properties['location'][1]:
                    break
                if "locked" in curr_loc.attributes:
                    res1 = tsentences.be(curr_loc,
                                         'is',
                                         None,
                                         'locked')

                    log_locked.append(tsentences.cont([neg_res, res1]))
                elif "openable" in curr_loc.attributes and "open" not in curr_loc.attributes:
                    res1 = tsentences.be(curr_loc,
                                         'is',
                                         'not',
                                         'open')

                    log_not_open.append(tsentences.cont([neg_res, res1]))
                curr_loc = curr_loc.properties['location'][1]
            log += log_locked

            if len(log_locked) == 0:
                log += log_not_open

        return log

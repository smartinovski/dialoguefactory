#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions that generate random parameters for the template functions.
"""

import random
from . import helpers


def random_world_list(curr_params, member_name):
    """
        Fetches an iterable member of the class World
        and generates a random value from it.

        For example, the member can be players, so a random value will be selected from the
        world.players list.

        Parameters
        ----------
        curr_params : dict
            A dictionary that contains the parameters. It is a mapping parameter_name: parameter_value.
        member_name : str
            The name of the member that will be fetched from the class World.

        Returns
        -------
        any
            A random value selected from the world's member.


    """
    world = curr_params['world']
    member_list = getattr(world, member_name, None)
    if isinstance(member_list, (list, tuple, str)):
        return random.choice(member_list)


def random_param_value(curr_params, param_name):
    """
        Fetches a parameter from the dictionary of parameters and generates a random value from it.
        The parameter should be an iterable.

        Parameters
        ----------
        curr_params : dict
            A dictionary that contains the parameters. It is a mapping parameter_name: parameter_value.
        param_name : str
            The name of the parameter.

        Returns
        -------
        any
            A random value selected from the iterable.

    """
    parameter = curr_params.get(param_name)
    if isinstance(parameter, (list, tuple, str)):
        return random.choice(parameter)


def candidate_prop_keys(curr_params):
    """ Fetches all property keys from the world except var_name and door_to """
    world = curr_params.get('world')
    if world is not None:
        return [key for key in world.all_properties if key not in ['var_name', 'door_to']]


def random_property_val(dia_generator, curr_params):
    """ Generates random property value for a given property key. It takes one value from the
        list of property values that are suitable for the property key. For example, for the property key color,
        it takes one of the following 'red', 'blue', 'green', etc. Later, it takes ten values
        that are not suitable for the property key. For the given example, this can be 'size' like 'small' or 'big'.
        Finally, it returns a single random value from the list of 11 values.

        The selection is done this way, so that the agent can see a variety of property values, not only the ones
        that are suitable.
    """
    candidate_key = curr_params.get('property_key')
    if candidate_key is not None:
        candidate_key_val = helpers.generate_property_val(dia_generator, [candidate_key])
        candidate_property_keys = curr_params.get('candidate_property_keys')
        if candidate_property_keys is not None:
            candidate_property_keys = [key for key in candidate_property_keys if key != candidate_key]
            item = curr_params.get('item')
            all_vals = [candidate_key_val]
            if candidate_key in item.properties:
                item_value = item.properties[candidate_key]
                if item_value not in all_vals:
                    all_vals.append(item_value)
                added = 0
            else:
                added = -1

            while added < 3:
                other_val = helpers.generate_property_val(dia_generator, candidate_property_keys)
                if other_val not in all_vals:
                    all_vals.append(other_val)
                    added += 1
            return random.choice(all_vals)


def random_location(curr_params):
    """ Generates a random location. The location can be an object. Some templates allow None to be the location,
        meaning the location is not provided.
    """
    world = curr_params.get('world')
    if world is not None:
        all_locations = []

        all_locations += random.sample(world.obj_list, 4)
        item = curr_params.get('item')
        item_loc = item.properties.get('location', None)
        if item_loc is not None and item_loc[1] not in all_locations:
            del all_locations[-1]
            all_locations.append(item_loc[1])

        all_locations += [None]*len(all_locations)
        return random.choice(all_locations)


def random_item(curr_params):
    """ Generates a random item from the list of objects in the world. If the determiner_a is True, the world's object
        should be converted to an abstract object. The abstract object can not be uniquely determined. For example,
        the flour container will be converted to a flour container.
    """
    item = random_world_list(curr_params, "obj_list")
    if curr_params.get("determiner_a", None) is True:
        item = helpers.unk_from_desc(item)
    return item


def random_user(curr_params):
    """ Generates a random player from the list of players except the main player.
        Therefore, the main player can not issue requests.
    """
    world = curr_params.get('world')
    list_candidates = [player for player in world.players if ('main', 'player') not in player.attributes]
    return random.choice(list_candidates)


def random_attribute(curr_params):
    """ Generates a random attribute except the attribute ('main', 'player'). This is an internal attribute
        that is not visible to the agents.
    """
    world = curr_params.get('world')
    list_candidates = [attr for attr in world.all_attributes if attr != ('main', 'player')]
    return random.choice(list_candidates)
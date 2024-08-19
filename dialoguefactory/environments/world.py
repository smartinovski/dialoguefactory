#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the class World which represents the simulated world.
"""
import dijkstar
import itertools

from . import path_helpers
from ..environment import descriptions
from ..environment import entities as em


class World:
    """
    The simulated world.

    Attributes
    ----------
    obj_list : list
        A list of Entity-s that belong to the world.
    undo_changes : list
        A list of all changes done to the entities. This list is passed to the constructor of each Entity.
        Whenever an action changes an entity property/attribute, an undo() function is saved in the undo_changes
        that will reverse the change. The changes are saved in chronological order.
    <var_name> : Entity
        For easier fetching of the entities (instead of looking for them in the list),
        self.<entity_var_name> can be used to get an entity. For example, self.rug or self.main_door.
    directions : list
        A list of strings representing all directions used in the world. For example: north, northeast, south, ...
    all_properties : list
        A list of all property keys that the entities in the world have.
    all_attributes : list
        A list of all attributes that the entities in the world have.
    <property_key>s : list
        To fetch all the possible values of a specific property key, the plural version of the property key is used.
        For example, to fetch all colors self.colors can be used. In case the property key is a tuple of strings,
        the strings are merged with an underscore, and the letter "s" is added at the end.

        The following properties are not added because their values do not represent all possible values:
        the obstacles (key: (north, obstacle), ... ), the directions (key: north, east, ...),
        the locations (key: location) and the doors leading to a location (key: door_to).
        For example, the big apple might have location ['on', table], but in the future ['in', player]
        and self.locations should therefore contain all these possible variations
        which we found is unnecessary to compute.
        Please check the function self.check_val_is_key in case you want to check if a specific value can be a location.
    <attribute>s : list
        A list of all objects that have a specific attribute. For example, to fetch all players, you can use
        self.players.
    graph : dijkstar.Graph
        The graph contains edges that represent connections between two neighboring places.
        The doors are not represented in the graph since the doors can be opened. We currently haven't implemented
        any static obstacles that can be present in front of the doors.
        Based on the graph, the shortest path between two places can be computed.
    all_paths: dict
        A dictionary mapping
        (location A, location B) => list of directions that lead the play from location A to location B.
    change_action_properties : list
        The list of properties that can be changed. This member is used by the
        :func:`actions.change() <dialoguefactory.environment.actions.change>` function.
    all_description_objects : list
        The Description objects are used for describing the entities.
    location_positions : list
        A list of prepositions used in the <entity>.properties['location'].
        The prepositions can be 'on', 'under', 'in'...
        For example, carrot.properties['location']=['on', kitchen_table]


    """
    def __init__(self, obj_list=None, undo_changes=None, change_action_properties=None,
                 all_description_objects=None, location_positions=None, init=True):
        self.obj_list = obj_list if obj_list is not None else list()
        self.undo_changes = undo_changes if undo_changes is not None else list()
        self.directions = list()
        self.all_properties = list()
        self.all_attributes = list()
        self.graph = dijkstar.Graph()
        self.all_paths = dict()
        self.change_action_properties = ['color',
                                         'size',
                                         'nickname',
                                         'surname',
                                         'name'] if change_action_properties is None else change_action_properties
        if all_description_objects is None:
            self.all_description_objects = [descriptions.Description1(cand_elements=['material',
                                                                                     'size',
                                                                                     'color',
                                                                                     'type',
                                                                                     ]),
                                            descriptions.BaseDescription(cand_elements=['name',
                                                                                        'nickname',
                                                                                        'surname'])]
        else:
            self.all_description_objects = all_description_objects

        self.location_positions = ['in', 'on', 'under'] if location_positions is None else location_positions

        if init:
            self.basic_init(obj_list)

    def basic_init(self, obj_list=None):
        """ Initializes the world's class members that are affected by the new objects list. """
        self.obj_list += list_diff(obj_list, self.obj_list)

        for obj in self.obj_list:
            setattr(self, obj.properties['var_name'], obj)

        self.directions += list_diff(self.compute_directions(), self.directions)
        self.all_properties += list_diff(self.get_properties(), self.all_properties)
        self.all_attributes += list_diff(self.get_attributes(), self.all_attributes)

        self.update_all_attributes()
        self.update_all_property_vals()

        self.update_graph()
        self.update_paths()

    def expand_world(self, new_world):
        """ Expands the current world with the objects of a new world.
            All the members of self are added without losing the current references.
        """
        diff_objs = list_diff(new_world.obj_list, self.obj_list)
        self.obj_list += diff_objs
        for obj in diff_objs:
            setattr(self, obj.properties['var_name'], obj)

        for obj in diff_objs:
            obj.change_world(self)
        del self.all_properties[:]
        self.all_properties += self.get_properties()
        del self.all_attributes[:]
        self.all_attributes += self.get_attributes()

        self.update_all_attributes()
        self.update_all_property_vals(new_world)

        del self.directions[:]
        self.directions += self.compute_directions()
        self.update_graph()
        self.update_paths()

        self.location_positions += list_diff(new_world.location_positions, self.location_positions)
        self.change_action_properties += list_diff(new_world.change_action_properties, self.change_action_properties)
        self.all_description_objects += list_diff(new_world.all_description_objects, self.all_description_objects)

    def save_state(self):
        """ Saves the world state by remembering the last point a world change was done. """
        return len(self.undo_changes)

    def recover_state(self, state):
        """ Recovers the world state to a specific point in the past.
            That point is <state> which is a positive integer and all changes past that point are undone. """
        prev_undo_counter = state
        for i in range(len(self.undo_changes) - 1, prev_undo_counter - 1, -1):
            cmd = self.undo_changes[i]
            cmd()
        del self.undo_changes[prev_undo_counter:]

    def flush_undo_changes(self):
        """ Removes the saved changes in order to save memory. """
        del self.undo_changes[:]

    def find_all_vals(self, prop_key):
        """ Finds all the property values in the world for a given property key. """
        vals = []
        for obj in self.obj_list:
            if prop_key in obj.properties:
                val = obj.properties[prop_key]
                if val not in vals:
                    vals.append(val)
        return vals

    def find_all_objs(self, attr):
        """ Finds all objects that have a specific attribute."""
        objs = []
        for obj in self.obj_list:
            if attr in obj.attributes and obj not in objs:
                objs.append(obj)
        return objs

    def update_all_property_vals(self, new_world=None):
        """ Updates all self.<property_key>s. This function is useful after adding new objects,
            or when merging worlds.
            If new_world is not None, it additionally updates all self.<property_key>s
            with the unassigned property values of the new_world.
            By unassigned, we mean the property values are not assigned to any of the objects of the new world.
            For example, some colors might be added, like new_world.colors.append("blue"), but blue
            might not appear anywhere in the objects.

        """
        for key in self.all_properties:
            if key != 'location' and key not in self.directions and not (
                    isinstance(key, tuple) and len(key) == 2 and key[0] in self.directions and key[1] == 'obstacle'):
                if isinstance(key, str):
                    plural_key = key + "s"
                elif isinstance(key, tuple):
                    plural_key = "_".join(key) + "s"
                else:
                    plural_key = None

                if plural_key is not None:
                    prop_vals_self = getattr(self, plural_key, None)
                    if prop_vals_self is None:
                        prop_vals_self = list()
                        setattr(self, plural_key, prop_vals_self)

                    prop_vals_self += list_diff(self.find_all_vals(key), prop_vals_self)
                    if new_world is not None:
                        prop_vals_new = getattr(new_world, plural_key, [])
                        prop_vals_self += list_diff(prop_vals_new, prop_vals_self)

        player_prop = ['name', 'nickname', 'surname']
        for prop in player_prop:
            player_prop_name = getattr(self, "player_"+prop+"s", None)

            if player_prop_name is None:
                prop_list = list()
                setattr(self, "player_"+prop+"s", prop_list)
            else:
                prop_list = player_prop_name

            for player in self.players:
                if prop in player.properties and player.properties[prop] not in prop_list:
                    prop_list.append(player.properties[prop])
            if new_world is not None:
                prop_list_new = getattr(new_world, "player_"+prop+"s", [])
                prop_list += list_diff(prop_list_new, prop_list)

    def update_all_attributes(self):
        """ Updates all self.<attribute>s. This function is useful after adding new objects,
            or when merging worlds.
        """
        for attr in self.all_attributes:
            if isinstance(attr, str):
                plural_attr = attr+"s"
            elif isinstance(attr, tuple):
                plural_attr = "_".join(attr)+"s"
            else:
                plural_attr = None

            if plural_attr is not None:
                attr_self = getattr(self, plural_attr, None)
                if attr_self is None:
                    attr_self = list()
                    setattr(self, plural_attr, attr_self)

                del attr_self[:]
                attr_self += self.find_all_objs(attr)

    def compute_directions(self):
        """ Finds all directions present in the world. For example,
            the bathroom can have a direction north which leads to the kitchen.
            The directions can be "north", "east", "northeast", ... and so on.
        """
        all_directions = ['north', 'east', 'west', 'south']
        permutations = list(itertools.permutations(all_directions, 2))
        permutations = [perm[0]+perm[1] for perm in permutations] + all_directions

        directions = []
        for obj in self.obj_list:
            for elem in permutations:
                if elem in obj.properties and elem not in directions:
                    directions.append(elem)
        return directions

    def check_val_is_key(self, key, val):
        """ Check if a specific value belongs to a key. For example, check if 'red' is a color.

            For most of the values, this can be done by using self.<property_key>s (self.colors in the example above).
            But for some properties like the object's location, self.<property_key>s does not exist because all
            the location values have to be manually computed: ['on', obj1], ['in', obj1], ... and so on. Instead, they
            are pattern-matched here in this function.
        """
        result = False
        if isinstance(key, tuple):
            list_vals = getattr(self, "_".join(key)+"s", None)
        else:
            list_vals = getattr(self, key+"s", None)

        if (key == 'location' and isinstance(val, list)
                and len(val) == 2 and val[0] in self.location_positions
                and isinstance(val[1], em.BaseEntity)):
            result = True
        elif key in self.directions+['door_to'] and isinstance(val, em.BaseEntity) and "place" in val.attributes:
            result = True
        elif (isinstance(key, tuple) and len(key) == 2 and key[0] in self.directions
              and key[1] == 'obstacle' and isinstance(val, em.BaseEntity)):
            result = True
        elif key == 'direction':
            if val in self.directions:
                result = True
            else:
                result = False
        else:
            if list_vals is None:
                result = None
            elif val in list_vals:
                result = True
        return result

    def update_paths(self):
        """ Update all the paths. This function is useful when the list of places is modified. """
        for source in self.places:
            for target in self.places:
                path = path_helpers.find_shortest_path(source, target, self.graph)
                if path is not None:
                    self.all_paths[(source, target)] = path

    def update_graph(self):
        """ Update the graph after the places and/or directions are modified."""
        for loc in self.places:
            for direction in self.directions:
                if direction in loc.properties:
                    self.graph.add_edge(loc, loc.properties[direction], (1, direction))

    def get_attributes(self):
        """ Gets all attributes that the objects in the world have."""
        items = self.obj_list
        attributes = []
        for i in items:
            attributes += list(i.attributes.keys())
        return list(set(attributes))

    def get_properties(self):
        """ Gets all properties that the objects in the world have."""
        property_keys = []
        for item in self.obj_list:
            property_keys += list(item.properties.keys())

        return list(set(property_keys))

    def get_property_values(self, prop_keys):
        """ Get all the property values for the given property keys and merge them in a list.
            This is done only if <property_key>s exists in the class.
        """
        total_vals = []
        for key in prop_keys:
            if isinstance(key, tuple):
                list_vals = getattr(self, "_".join(key) + "s", [])
            else:
                list_vals = getattr(self, key + "s", [])
            total_vals += list_vals
        return total_vals

    def query_entity_from_db(self,  entity):
        """ Returns all entities that are similar to the given entity.
            The similarity is done by comparing
            all properties and attributes between the given entity and the entities in self.obj_list.
        """

        filter_properties = lambda o, e=entity: all([p in o.properties and o.properties[p] == e.properties[p] for p in e.properties if e.properties[p] != "empty" and p != "var_name"])
        filter_attributes = lambda o, e=entity: all([a in o.attributes for a in e.attributes if a != "abstract" and a != ("main", "player")])
        filtered_objects = filter_items(self.obj_list, [filter_properties, filter_attributes])

        return filtered_objects


def filter_items(all_objects, filter_conditions=None):
    """ Returns the objects from the list all_objects that satisfy the given conditions.

    Parameters
    ----------
    all_objects : list
        A list of Entity-s.
    filter_conditions : list
        A list of functions that accept as the first parameter an Entity. The functions should return True or False.
        The functions act as a set of conditions that the objects should satisfy.
    """
    items = []
    for obj in all_objects:
        if filter_conditions is None:
            items.append(obj)
        else:
            all_true = all([cond(obj) for cond in filter_conditions])
            if all_true:
                items.append(obj)
    return items


def list_diff(list1, list2):
    """ Returns the elements that are present in list1 but not in list2."""
    diff_elems = []
    for element in list1:
        if element not in list2:
            diff_elems.append(element)
    return diff_elems


def compute_unique_list(_list):
    """ Computes a list with elements that do not repeat. This function is useful when
        the built-in function set is not applicable due to the non-hashable elements present in the list.
    """
    new_list = []
    for elem in _list:
        if elem not in new_list:
            new_list.append(elem)
    return new_list

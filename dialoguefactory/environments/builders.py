#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module offers functions that create instances of the class Entity based on their attributes and properties.
"""


def remove_none_values(dict_):
    """ Removes the dictionary values that are None."""
    keys_delete = []
    for key, val in dict_.items():
        if val is None:
            keys_delete.append(key)
    for key in keys_delete:
        del dict_[key]


def build_entity(world, var_name=None, size=None, _type=None, color=None, material=None, location=None,
                 name=None, surname=None, nickname=None):
    """ Creates an Entity instance and initializes it with the properties given above. If the location is provided,
        the entity is added to the :attr:`location.objects <dialoguefactory.environment.entities.Entity.objects>` field.
    """
    from ..environment import entities as env

    ent = env.Entity(world)
    ent.properties['var_name'] = var_name
    ent.properties['type'] = _type
    ent.properties['size'] = size
    ent.properties['color'] = color
    ent.properties['material'] = material
    ent.properties['location'] = location
    ent.properties['name'] = name
    ent.properties['surname'] = surname
    ent.properties['nickname'] = nickname

    if location is not None:
        location[1].objects.append(ent)

    remove_none_values(ent.properties)

    return ent


def build_player(world, var_name, size=None, _type=None, color=None, material=None, location=None,
                 name=None, surname=None, nickname=None):
    """ Builds an Entity and adds the attribute player. The player can perform actions in the environment."""
    player = build_entity(world, var_name, size, _type, color, material, location, name, surname, nickname)
    player.attributes['player'] = None

    return player


def build_place(world, var_name, size=None, _type=None, color=None, material=None):
    """ Builds an Entity that refers to an open or enclosed space that can hold objects.
        There are a few differences between a container and a place:

            - the container might be part of a place or a different container.
            - the place is always static, and the container can be moved.
            - the place might require a door to be opened first, and
              the present containers are simplified and can be opened directly.
              In the future, this simplification can be changed, and containers might have a lid or/and latch.

    """
    place = build_entity(world, var_name, size, _type, color, material)
    place.properties['location'] = ['in', place]
    place.attributes['static'] = None
    place.attributes['place'] = None

    return place


def build_book(world, var_name, size=None, color=None, material=None, location=None):
    """ Builds an Entity with type book that can be opened. """
    book = build_entity(world, var_name, size, 'book', color, material, location)
    book.attributes['openable'] = None

    return book


def build_window(world, var_name, size=None, color=None, material=None, location=None):
    """ Builds an Entity that has a type window. """
    window = build_entity(world, var_name, size, 'window', color, material, location)
    window.attributes['static'] = None
    window.attributes['openable'] = None

    return window


def build_bed(world, var_name, size=None, color=None, material=None, location=None):
    """ Builds an Entity that has type bed. The beds built here are static and hollow."""

    bed = build_entity(world, var_name, size, 'bed', color, material, location)
    bed.attributes['static'] = None
    bed.attributes['supporter'] = None
    bed.attributes['hollow'] = None

    return bed


def build_table(world, var_name, size=None, color=None, material=None, location=None):
    """ The tables created in this function are assumed too heavy to be carried by a single person and are made static.
        Not all tables have to be static.
    """
    table = build_entity(world, var_name, size, 'table', color, material, location)
    table.attributes['hollow'] = None
    table.attributes['supporter'] = None
    table.attributes['static'] = None

    return table


def build_door(world, var_name, size=None, color=None, material=None, location=None, door_to=None):
    """ Builds an entity with an attribute door. Additionally, the door_to property can be added to indicate
     where the door leads (usually, the door connects two places).

     For now, the location of the door is ['in', <place>] instead of ['between', place1, place2].
     This can be modified in the future.
     """
    door = build_entity(world, var_name, size, None, color, material, location)
    if door_to is not None:
        door.properties['door_to'] = door_to
    door.properties['type'] = 'door'
    door.attributes['openable'] = None
    door.attributes['static'] = None

    return door

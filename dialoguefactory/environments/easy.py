#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides the function for creating the simulated training environment.
"""


from ..environment import entities as env
from . import builders
from . import world as tworld


def build_world():
    """ Build the entities of the easy world.
        In the easy world, only <x> rooms are used, and <y> directions for the rooms.
        There are a total of <z> objects.
    """
    undo_changes = []
    world = tworld.World(undo_changes=undo_changes, init=False)
    barn = env.Entity(world)
    main_path = env.Entity(world)
    well = env.Entity(world)
    living_room = env.Entity(world)
    kitchen = env.Entity(world)
    bedroom = env.Entity(world)
    bathroom = env.Entity(world)
    basement = env.Entity(world)

    ''' DEFINE THE AGENTS '''

    player = builders.build_player(world, 'player', 'medium', 'person', location=['in', barn],
                                    name='Gretel', surname='Mustermann', nickname='honey')
    player.attributes[('main', 'player')] = None
    player2 = builders.build_player(world, 'player2', 'small', 'person', location=['in', barn],
                                    name='Hans', surname='Doe', nickname='peanut')
    inv = builders.build_player(world, 'inv', ['very', 'big'], 'person', location=['in', basement],
                                name='Max', nickname='uncle')
    bear = builders.build_player(world, 'bear', _type='bear', color='orange', location=['in', barn],
                                 name='Andy', nickname='fluffy')
    dog = builders.build_player(world, 'dog', _type='dog',  location=['in', kitchen],
                                name='Hannah', nickname='coco')

    ''' DEFINE THE ENTITIES '''
    toys_container = builders.build_entity(world, 'toys_container', _type=["toys", "drawer"],
                                           color='red', location=['in', bedroom])
    toys_container.attributes['container'] = None
    toys_container.attributes['supporter'] = None
    toys_container.attributes['openable'] = None
    toys_container.attributes['open'] = None

    small_container = builders.build_entity(world, 'small_container', _type=["toys", "drawer"], color='green',
                                            location=['in', toys_container])
    small_container.attributes['container'] = None
    small_container.attributes['openable'] = None

    inner_container = builders.build_entity(world, 'inner_container', _type='box', material='cardboard',
                                            location=['in', small_container])
    inner_container.attributes['container'] = None
    inner_container.attributes['locked'] = None
    inner_container.properties['location'] = ['in', small_container]

    rug = builders.build_entity(world, 'rug', _type='rug', location=['in', kitchen])
    rug.attributes['hollow'] = None

    small_ball = builders.build_entity(world, 'small_ball', 'small', 'ball', 'red', location=['in', small_container])
    big_ball = builders.build_entity(world, 'big_ball', 'big', 'ball', 'green', location=['in', toys_container])
    small_apple = builders.build_entity(world, 'small_apple', 'small', 'apple', 'red', location=['in', main_path])
    big_apple = builders.build_entity(world, 'big_apple', 'big', 'apple', 'green', location=['in', main_path])
    chicken = builders.build_entity(world, 'chicken', _type='chicken', location=['in', well])

    kitchen_table = builders.build_table(world, 'kitchen_table', material='plastic', location=['in', kitchen])
    kitchen_window = builders.build_window(world, "kitchen_window", "small", "green", "wood", ["in", kitchen])
    kitchen_window.attributes['open'] = None

    carrot = builders.build_entity(world, 'carrot', _type='carrot', color='orange', location=['on', kitchen_table])

    food_drawer = builders.build_entity(world, 'food_drawer', color="green",
                                        _type=["food", "drawer"], location=['in', kitchen])
    food_drawer.attributes['openable'] = None
    food_drawer.attributes['hollow'] = None
    food_drawer.attributes['container'] = None
    food_drawer.attributes['static'] = None

    shelf1 = builders.build_entity(world, 'shelf1', _type="shelf", color="brown", material="plastic",
                                   location=['in', food_drawer])
    shelf1.attributes['supporter'] = None
    cardboard_container = builders.build_entity(world, 'cardboard_container', size="big",
                                                material="cardboard", location=['on', shelf1])
    cardboard_container.attributes['container'] = None
    cardboard_container.attributes['open'] = None
    flour_bag = builders.build_entity(world, 'flour_bag', _type="bag", size="small",
                                      material="cotton", color="white", location=['in', cardboard_container])
    flour_bag.attributes['container'] = None
    flour_bag.attributes['openable'] = None

    sugar_bowl = builders.build_entity(world, 'sugar_bowl', _type="bowl", size="small",
                                       material="plastic", color="white", location=['in', cardboard_container])
    sugar_bowl.attributes['container'] = None
    sugar_bowl.attributes['open'] = None

    white_sugar_cube = builders.build_entity(world, 'white_sugar_cube', _type="cube", size=["very", "small"],
                                             material="sugar", color="white", location=['in', sugar_bowl])

    brown_sugar_cube = builders.build_entity(world, 'brown_sugar_cube', _type="cube", size=["very", "small"],
                                             material="sugar", color="brown", location=['in', sugar_bowl])

    main_door = builders.build_door(world, 'main_door', size="medium",
                                    material='plastic', location=['in', kitchen], door_to=living_room)

    liv_room_door = builders.build_door(world, 'liv_room_door', material='metal', location=['in', living_room])
    liv_room_door.attributes['locked'] = None

    bathroom_door = builders.build_door(world, 'bathroom_door', 'big', 'red', 'wood', ['in', bathroom])
    bathroom_door.attributes['locked'] = None
    bathroom_door.properties['nickname'] = ['privacy', 'portal']

    barn_door = builders.build_door(world, 'barn_door', 'small', 'brown', location=['in', barn])
    barn_door.attributes['locked'] = None

    bedroom_hall_door = builders.build_door(world, 'bedroom_hall_door', 'big', 'brown', location=['in', bedroom])
    bedroom_hall_door.attributes['locked'] = None

    bedroom_home_door = builders.build_door(world, 'bedroom_home_door', 'big',
                                            material='plastic', location=['in', bedroom])
    bedroom_home_door.attributes['locked'] = None

    ''' DEFINE ROOMS '''

    barn.properties['type'] = ['family', 'barn']
    barn.properties['var_name'] = 'barn'
    barn.properties['location'] = ['in', barn]
    barn.properties['south'] = main_path
    barn.properties[('north', 'obstacle')] = barn_door
    barn.attributes['static'] = None
    barn.attributes['place'] = None

    living_room.properties['type'] = ['living', 'room']
    living_room.properties['size'] = 'big'
    living_room.properties['var_name'] = 'living_room'
    living_room.properties['location'] = ['in', living_room]
    living_room.properties['west'] = kitchen
    living_room.properties[('west', 'obstacle')] = main_door
    living_room.properties[('north', 'obstacle')] = liv_room_door
    living_room.properties['east'] = bedroom
    living_room.properties['south'] = main_path
    living_room.attributes['static'] = None
    living_room.attributes['place'] = None
    living_room.properties['nickname'] = ['tranquility', 'room']

    main_path.properties['type'] = ['porch', 'path']
    main_path.properties['var_name'] = 'main_path'
    main_path.properties['location'] = ['in', main_path]
    main_path.properties['south'] = well
    main_path.properties['west'] = barn
    main_path.properties['north'] = living_room
    main_path.attributes['static'] = None
    main_path.attributes['place'] = None

    well.properties['type'] = 'well'
    well.properties['var_name'] = 'well'
    well.properties['location'] = ['in', well]
    well.properties['north'] = main_path
    well.attributes['static'] = None
    well.attributes['place'] = None

    kitchen.properties['type'] = 'kitchen'
    kitchen.properties['var_name'] = 'kitchen'
    kitchen.properties['location'] = ['in', kitchen]
    kitchen.properties['west'] = living_room
    kitchen.properties[('west', 'obstacle')] = main_door
    kitchen.properties['south'] = basement
    kitchen.properties['material'] = 'wood'
    kitchen.attributes['static'] = None
    kitchen.attributes['place'] = None

    bedroom.properties['type'] = 'bedroom'
    bedroom.properties['var_name'] = 'bedroom'
    bedroom.properties['material'] = 'plaster'
    bedroom.properties['location'] = ['in', bedroom]
    bedroom.properties['west'] = living_room
    bedroom.properties['south'] = bathroom
    bedroom.properties[('southeast', 'obstacle')] = bedroom_hall_door
    bedroom.properties[('east', 'obstacle')] = bedroom_home_door
    bedroom.attributes['static'] = None
    bedroom.attributes['place'] = None

    bathroom.properties['type'] = 'bathroom'
    bathroom.properties['var_name'] = 'bathroom'
    bathroom.properties['location'] = ['in', bathroom]
    bathroom.properties[('east', 'obstacle')] = bathroom_door
    bathroom.properties['north'] = bedroom
    bathroom.attributes['static'] = None
    bathroom.attributes['place'] = None

    basement.properties['type'] = 'basement'
    basement.properties['var_name'] = 'basement'
    basement.properties['north'] = kitchen
    basement.properties['location'] = ['in', basement]
    basement.attributes['place'] = None
    basement.attributes['static'] = None

    obj_list = [barn, main_path, well, living_room, bedroom,
                bathroom, kitchen, basement, rug, small_ball,
                big_ball, small_apple, big_apple, chicken,
                toys_container, small_container, carrot, player, player2, inv, dog, bear,
                kitchen_table, kitchen_window, main_door, liv_room_door, bathroom_door, barn_door,
                bedroom_hall_door, bedroom_home_door, inner_container, food_drawer, shelf1,
                cardboard_container, flour_bag, sugar_bowl, white_sugar_cube, brown_sugar_cube]

    world.basic_init(obj_list=obj_list)

    world.colors.append('blue')
    world.names.append('Jim')
    world.player_names.append('Jim')
    world.nicknames.append('lovebug')
    world.player_nicknames.append('lovebug')


    return world

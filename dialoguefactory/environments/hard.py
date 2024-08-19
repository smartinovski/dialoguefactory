#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides the function for creating the extension of the training environment. It additionally provides
a function for merging the training and extension environment.
"""
import itertools
import random
import copy

from . import builders
from . import world as tworld
from ..language import sentences as tsentences
from ..environment import descriptions
from ..state import kn_updaters


def merge_worlds(dia_generator, hard_world):
    """ Merges the easy world (dia_generator.world) with the hard world
    """

    easy_world = dia_generator.world

    easy_world.liv_room_door.properties['door_to'] = hard_world.library
    easy_world.living_room.properties['north'] = hard_world.library
    hard_world.library.properties['west'] = easy_world.living_room
    hard_world.library.properties[('west', 'obstacle')] = easy_world.liv_room_door

    easy_world.bathroom_door.properties['door_to'] = hard_world.play_room
    easy_world.bathroom.properties['east'] = hard_world.play_room
    hard_world.play_room.properties['southwest'] = easy_world.bathroom
    hard_world.play_room.properties[('southwest', 'obstacle')] = easy_world.bathroom_door

    easy_world.barn_door.properties['door_to'] = hard_world.guest_room
    easy_world.barn.properties['north'] = hard_world.guest_room
    hard_world.guest_room.properties['north'] = easy_world.barn
    hard_world.guest_room.properties[('north', 'obstacle')] = easy_world.barn_door

    easy_world.bedroom_home_door.properties['door_to'] = hard_world.home_office
    easy_world.bedroom.properties['east'] = hard_world.home_office
    easy_world.bedroom_hall_door.properties['door_to'] = hard_world.hall
    easy_world.bedroom.properties['southeast'] = hard_world.hall

    hard_world.home_office.properties['south'] = easy_world.bedroom
    hard_world.home_office.properties[('south', 'obstacle')] = easy_world.bedroom_home_door
    hard_world.hall.properties['north'] = easy_world.bedroom
    hard_world.hall.properties[('north', 'obstacle')] = easy_world.bedroom_hall_door

    easy_world_objs = copy.copy(easy_world.obj_list)
    old_desc = [obj.generate_description() for obj in easy_world.obj_list]

    # Finds all entities before the worlds are merged
    empty_entities = find_empty_entities(dia_generator)

    easy_world.expand_world(hard_world)

    update_seen_location(dia_generator, hard_world, empty_entities)

    dia_generator.init_agent_policy_db(hard_world.players)
    dia_generator.init_user_policy_db(hard_world.players)
    dia_generator.init_agent_auto_policy_db(hard_world.players)
    dia_generator.init_user_auto_policy_db(hard_world.players)

    clarify_colliding_desc(dia_generator, easy_world_objs, old_desc)

    for obj in easy_world.obj_list:
        if "type" in obj.properties and obj.properties["type"] == "door":
            if 'locked' in obj.attributes:
                del obj.attributes['locked']
                dia_generator.execute_utters([tsentences.be(obj, "is", "not", "locked")], skip_env=True)


def find_empty_entities(dia_generator):
    """ Finds all entities in the world that are empty. """
    empty_entities = []
    for ent in dia_generator.world.obj_list:
        for lp in dia_generator.world.location_positions:
            if len(ent.objects) == 0 and dia_generator.knowledge_base.check(tsentences.have((ent, None),
                                                                                            ('has', None),
                                                                                            ('not', None),
                                                                                            ('items', None),
                                                                                            ([lp, ent], None))):
                empty_entities.append(ent)
    return empty_entities


def update_seen_location(dia_generator, hard_world, empty_entities):
    """  Update the new world entities that their location is not any of the empty objects of the easy world. """

    for ent in hard_world.obj_list:
        for empty_ent in empty_entities:
            for lp in dia_generator.world.location_positions:
                kn_updaters.property_update_alt(dia_generator.knowledge_base, ent, "location", [lp, empty_ent], "not")


def clarify_colliding_desc(dia_generator, easy_world_objs, old_desc):
    """ Creates new unique descriptions for the old entities in the new world.

        Some entities from the old world and new world can have same properties and attributes. Therefore,
        the description of an old entity can be subset of the description of the new entity.
        """
    for idx, obj in enumerate(easy_world_objs):
        seen, not_seen, partially_seen = obj.select_unique_descriptions()
        if len(seen) == 0 and len(partially_seen) > 0:
            num_overlap = []
            for desc in partially_seen:
                num_overlap.append(len(set(desc.elements).intersection(set(old_desc[idx].elements))))
            max_overlap_idx = num_overlap.index(max(num_overlap))
            dia_generator.execute_utters([tsentences.be((obj, obj.describe(old_desc[idx].elements)),
                                                        "is",
                                                        None,
                                                        (obj, obj.describe(partially_seen[max_overlap_idx].elements)))],
                                         skip_env=True)


def check_description_collisions(dia_generator, hard_world, changeable_properties=None, players_only=False):
    """ Checks whether some entities from the easy world can have same description as the ones in the hard world.
        The collisions can happen because some of the entity's properties are changeable
        This function simulates the changes of the entities done in the easy world and later checks if there are
        any collisions with the descriptions of the hard world entities.

        Parameters
        ----------
        dia_generator : DialogueGenerator
            The dialogue generator that contains the training environment (easy_world).
        hard_world : World
            The testing environment.
        changeable_properties : list
            A list of strings representing the properties that can change.
        players_only : bool
            Whether to check for all objects in the easy/hard world or just for players.
            It is useful to check for players only where you have names, nicknames and surnames.

        Returns
        -------
        collisions : list
            A list of tuples. Each tuple has two values, the entities that can have potentially two equal descriptions.
    """
    import copy

    if changeable_properties is None:
        if not players_only:
            changeable_properties = ['color', 'size']
        else:
            changeable_properties = ['name', 'nickname', 'surname']
    easy_world = dia_generator.world
    vals = dict()
    for prop in changeable_properties:
        vals[prop] = copy.copy(getattr(easy_world, prop + "s"))
    if players_only:
        easy_objs_before_merging = copy.copy(easy_world.players)
        hard_objs_before_merging = copy.copy(hard_world.players)
    else:
        easy_objs_before_merging = copy.copy(easy_world.obj_list)
        hard_objs_before_merging = copy.copy(hard_world.obj_list)
    merge_worlds(dia_generator, hard_world)

    for obj in easy_objs_before_merging+hard_objs_before_merging:
        for prop in obj.properties:
            obj.prop_seen[prop] = obj.properties[prop]
        for attr in obj.attributes:
            obj.attr_seen[attr] = None

    all_combinations = []
    for r in range(len(changeable_properties) + 1):
        all_combinations.extend(itertools.combinations(changeable_properties, r))

    def check_collisions(objs, objs_other):
        collisions = []
        for obj in objs:
            for combination in all_combinations:
                old_prop = copy.copy(obj.properties)
                old_prop_seen = copy.copy(obj.prop_seen)
                cart_product = list(itertools.product(*[vals[prop] for prop in combination]))
                for comb_vals in cart_product:
                    for idx, prop in enumerate(combination):
                        obj.properties[prop] = comb_vals[idx]
                        obj.prop_seen[prop] = comb_vals[idx]
                    if obj.generate_description(relaxed=False) is not None:
                        for objj in objs_other:
                            desc = objj.generate_description(relaxed=False)
                            if desc is None and (obj.properties['var_name'], objj.properties['var_name']) not in collisions:
                                collisions.append((obj.properties['var_name'], objj.properties['var_name']))
                                break
                obj.properties.clear()
                obj.properties.update(old_prop)
                obj.prop_seen.clear()
                obj.prop_seen.update(old_prop_seen)
        return collisions

    final_collisions = []
    random.shuffle(easy_objs_before_merging)
    random.shuffle(hard_objs_before_merging)
    final_collisions += check_collisions(easy_objs_before_merging, hard_objs_before_merging)

    return final_collisions


def compute_unique_list(_list):
    """ Computes a list with unique elements. This function is used when
        the built-in function set is not applicable
        due to non-hashable elements.
    """
    new_list = []
    for elem in _list:
        if elem not in new_list:
            new_list.append(elem)
    return new_list


def build_world():
    """ Creates the hard world and all of its objects. """
    undo_changes = []
    world = tworld.World(undo_changes=undo_changes, init=False)
    ''' DEFINE ROOMS '''
    library = builders.build_place(world, 'library', _type='library')
    play_room = builders.build_place(world, 'play_room', _type=['play', 'room'])
    hall = builders.build_place(world, 'hall', _type='hall')
    yard = builders.build_place(world, 'yard', 'big', 'yard')
    home_office = builders.build_place(world, 'home_office', 'medium', 'office', 'white')
    guest_room = builders.build_place(world, 'guest_room', 'medium', ['guest', 'room'], 'orange')

    ''' DEFINE DOORS '''
    hall_outside_door = builders.build_door(world, 'hall_outside_door', None, 'orange', 'wood', ['in', hall], yard)
    hall_outside_door.properties['nickname'] = ['freedom', 'frame']

    library.properties['northeast'] = home_office
    home_office.properties['southwest'] = library
    yard.properties['south'] = guest_room
    yard.properties['north'] = hall
    yard.properties[('north', 'obstacle')] = hall_outside_door
    guest_room.properties['northeast'] = yard
    hall.properties['east'] = yard
    hall.properties[('east', 'obstacle')] = hall_outside_door
    hall.properties['west'] = play_room
    play_room.properties['northwest'] = hall

    red_table = builders.build_table(world, 'red_table', color='red', location=['in', library])
    red_table.properties['nickname'] = ['whisper', 'table']

    black_chair = builders.build_entity(world, 'black_chair', 'medium', 'chair', 'black', 'wood', ['in', library])
    brown_chair = builders.build_entity(world, 'brown_chair', 'medium', 'chair', 'brown', 'wood', ['in', library])
    brown_chair.properties["nickname"] = "squeaky"

    books_drawer = builders.build_entity(world, 'book_shelves', None, ['books', 'drawer'], None, None, ['in', library])
    books_drawer.attributes['static'] = None
    books_drawer.attributes['supporter'] = None
    books_drawer.attributes['container'] = None
    books_drawer.attributes['open'] = None

    books_shelf1 = builders.build_entity(world, 'books_shelf1', _type="shelf", size="medium",
                                          location=['in', books_drawer])
    books_shelf1.attributes['supporter'] = None
    books_shelf1.properties['nickname'] = ['saga', 'shelf']
    books_shelf2 = builders.build_entity(world, 'books_shelf2', _type="shelf",
                                         color="red", material="wood", location=['in', books_drawer])
    books_shelf2.attributes['supporter'] = None
    books_shelf2.properties['nickname'] = ['inspiration', 'isle']

    book1 = builders.build_book(world, 'book1', 'small', 'black', 'paper', ['on', books_shelf1])
    book1.properties["name"] = ["The", "Hobbit"]

    book2 = builders.build_book(world, 'book2', 'small', 'blue', 'hardcover', ['on', books_shelf2])
    book2.properties["name"] = ["Harry", "Potter"]

    book3 = builders.build_book(world, 'book3', 'big', 'black', 'paper', ['under', red_table])
    book3.properties["name"] = ["Alice", "in", "Wonderland"]
    book3.attributes["open"] = None

    mat = builders.build_entity(world, 'mat', None, 'mat', 'blue', 'wood', ['in', play_room])
    mat.properties['name'] = ['magic', 'mat']
    mat.properties['nickname'] = ['flying', 'mat']
    mat.attributes['hollow'] = None

    window1 = builders.build_window(world, "window1", "medium", "transparent", "glass", ['in', play_room])
    window1.attributes['open'] = None

    toy_apple = builders.build_entity(world, 'toy_apple', 'small', ['toy', 'apple'], 'red', None, ['in', play_room])
    toy_ball = builders.build_entity(world, 'toy_ball', 'small', ['toy', 'ball'], location=['in', play_room])

    umbrella = builders.build_entity(world, 'umbrella', 'medium', 'umbrella', 'blue', 'leather', ['in', hall])
    umbrella.attributes["openable"] = None
    umbrella.attributes["open"] = None

    shoe1 = builders.build_entity(world, 'shoe1', 'medium', 'shoe', 'blue', 'leather', ['in', hall])
    shoe1.attributes["open"] = None

    shoe2 = builders.build_entity(world, 'shoe2', 'medium', 'shoe', 'red', 'leather', ['in', hall])
    shoe2.attributes["open"] = None

    apple_tree = builders.build_entity(world, 'apple_tree', None, ['apple', 'tree'], location=['in', yard])
    apple_tree.attributes["static"] = None

    shoe_box = builders.build_entity(world, 'shoe_box', None, 'box', None, 'wood', ['in', yard])
    shoe_box.attributes['container'] = None
    shoe_box.attributes['open'] = None

    shoe3 = builders.build_entity(world, 'shoe3', 'medium', 'shoe', 'brown', 'leather', ['in', shoe_box])
    shoe3.attributes["open"] = None

    leaf = builders.build_entity(world, 'leaf', 'small', 'leaf', 'green', None, ['in', yard])

    summer_bed = builders.build_bed(world, 'summer_bed', 'medium', 'white', None, ['in', yard])
    del summer_bed.attributes['static']
    desk = builders.build_table(world, 'desk', None, 'blue', 'wood', ['in', home_office])
    del desk.attributes['static']
    note = builders.build_entity(world, 'note', None, 'note', None, 'paper', ['on', desk])

    desk_chair = builders.build_entity(world, 'chair', None, 'chair', None, 'plastic', ['in', home_office])
    desk_chair.attributes['supporter'] = None
    desk_chair.attributes['hollow'] = None

    guest_room_bed = builders.build_bed(world, 'guest_room_bed', 'big', 'red', 'metal', ['in', guest_room])
    del guest_room_bed.attributes['hollow']
    guest_window = builders.build_window(world, 'guest_window', None, 'red', 'metal', ['in', guest_room])
    guest_desk = builders.build_table(world, 'guest_desk', 'small', None, 'wood', ['in', guest_room])
    del guest_desk.attributes['static']

    piece_of_paper = builders.build_entity(world, 'piece_of_paper', 'small', ['piece', 'of', 'paper'],
                                           'white', 'paper', ['under', guest_desk])
    pen = builders.build_entity(world, 'pen', 'small', 'pen', 'blue', None, ['under', guest_desk])

    programmer = builders.build_player(world, 'programmer', color="red", _type="person", location=['in', guest_room])
    programmer.properties['name'] = 'Ada'
    programmer.properties['surname'] = 'Mustermann'
    programmer.properties['nickname'] = 'honey'

    cabin = builders.build_place(world, "cabin", size='big', _type='cabin', material='metal')
    cabin.properties['location'] = ['in', cabin]

    cabin_desk = builders.build_table(world, "cabin_desk", color="black", material="metal", location=["in", cabin])
    del cabin_desk.attributes['static']
    terminal = builders.build_entity(world, "terminal", _type="computer",
                                     color="black", material="metal", location=["on", cabin_desk])

    captain = builders.build_player(world, "captain", location=['in', cabin])
    captain.properties['nickname'] = 'Captain'

    space_living_room = builders.build_place(world, "space_living_room", material="metal", _type=['living', 'room'])
    space_window = builders.build_window(world, "space_window", color="blue",
                                         material="plastic", location=["in", space_living_room])
    space_window.attributes['locked'] = None

    cat = builders.build_player(world, 'cat', color="brown", _type="cat", location=['in', space_living_room])
    cat.properties['name'] = 'Otto'
    cat.properties['nickname'] = 'tuxedo'
    cat.properties['surname'] = 'Doe'

    space_bedroom = builders.build_place(world, "space_bedroom", material="plastic", _type='bedroom')
    cabin_bedroom_door = builders.build_door(world, "cabin_bedroom_door", material="cardboard",
                                             size="medium", location=['in', cabin], door_to=space_bedroom)
    space_living_room.properties['east'] = space_bedroom
    space_bedroom.properties['west'] = space_living_room
    space_bedroom.properties['east'] = cabin
    space_bedroom.properties[('east', 'obstacle')] = cabin_bedroom_door

    spaceship_bed = builders.build_bed(world, "spaceship_bed", 'small', material="wood", location=['in', space_bedroom])
    del spaceship_bed.attributes['static']
    del spaceship_bed.attributes['hollow']
    pillow = builders.build_entity(world, "pillow", _type="pillow", material="cotton", location=["on", spaceship_bed])

    cabin.properties['west'] = space_bedroom
    cabin.properties[('west', 'obstacle')] = cabin_bedroom_door

    obj_list = [library, red_table, black_chair, brown_chair, books_drawer, books_shelf1, books_shelf2, book1, book2,
                book3, play_room, mat, window1, toy_apple, toy_ball, hall, umbrella, shoe1, shoe2, yard,
                hall_outside_door, apple_tree, shoe_box, shoe3, leaf, summer_bed, home_office, desk, note,
                desk_chair, guest_room, guest_room_bed, guest_window, guest_desk, piece_of_paper, pen, programmer, cat,
                cabin, cabin_desk, terminal, captain, space_living_room, space_window, space_bedroom,
                spaceship_bed, pillow, cabin_bedroom_door
                ]

    desc_obj = descriptions.Description1(cand_elements=['type',
                                                        'size',
                                                        'color',
                                                        'open',
                                                        'locked',
                                                        'material',
                                                        'static',
                                                        'container',
                                                        'hollow',
                                                        'supporter',
                                                        'place'])
    world.all_description_objects.append(desc_obj)

    world.basic_init(obj_list=obj_list)

    world.colors.append('yellow')
    world.names.append('Bella')
    world.player_names.append('Bella')
    world.nicknames.append(['cuddle', 'bunny'])
    world.player_nicknames.append(['cuddle', 'bunny'])
    world.surnames.append('Smith')
    world.player_surnames.append('Smith')

    return world

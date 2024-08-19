#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists all functions the environment uses to provide feedback to the player.
"""
import copy

from ..language import helpers as lhelpers
from ..language import sentences as tsentences
from ..language import components as lc

from . import helpers as em_helpers
from ..state import kn_helpers


def go(player, direction, from_location=None):
    """
    Returns the environment response when a player tries moving in a direction from a certain location.

    Parameters
    ----------
    player : Entity
        The player that tries moving.
    direction : str
        The direction of movement. This can be north, east, northeast, ... and so on.
        If the string is not a direction or the direction is not present in player.properties['location']
        a negative response is returned.
    from_location : Entity
        The location where the player is.
        If the from_location is not the correct one, a negative feedback is provided.


    Returns
    -------
    log : list
        A list of valid responses.

    """
    if from_location is None:
        from_location = player.properties["location"][1]

    can_not_go_res = tsentences.go(player,
                                   'can', 'not', 'go',
                                   direction)

    log = []

    visibility = player.validate_reachability(player, from_location, can_not_go_res)
    log += visibility

    obstacle = player.properties['location'][1].properties.get((direction, 'obstacle'))

    if obstacle is not None:
        obs_loc = tsentences.be([player.properties['location'][1], "'s", direction, 'obstacle'], 'is', None, obstacle)
        meta_dir_exists = tsentences.have(from_location, 'has', None, ['direction', direction])
        player_loc = tsentences.be([player, "'s", "location"], "is", None, player.properties['location'])

        if 'type' in obstacle.properties and obstacle.properties['type'] == 'door' and 'open' not in obstacle.attributes:
            res_not_open = tsentences.be(obstacle, 'is', 'not', 'open')
            if 'locked' in obstacle.attributes:
                res_locked = tsentences.be(obstacle, 'is', None, 'locked')
                cont_res = tsentences.cont([can_not_go_res,  obs_loc, res_locked])
                cont_res.meta_sent.append(meta_dir_exists)
                cont_res.meta_sent.append(player_loc)

                log.append(cont_res)

            elif 'openable' not in obstacle.attributes:
                res_not_openable = tsentences.be(obstacle, 'is', 'not', 'openable')
                cont_res = tsentences.cont([can_not_go_res, obs_loc, res_not_openable])
                cont_res.meta_sent.append(meta_dir_exists)
                cont_res.meta_sent.append(player_loc)

                log.append(cont_res)

            else:
                cont_res = tsentences.cont([can_not_go_res, obs_loc, res_not_open])
                cont_res.meta_sent.append(meta_dir_exists)
                cont_res.meta_sent.append(player_loc)

                log.append(cont_res)
    if player.world.check_val_is_key('direction', direction) is False:
        log.append(tsentences.be(direction, "is", "not", "direction"))
    elif direction not in player.properties['location'][1].properties:
        player_loc = tsentences.be([player, "'s", "location"], "is", None, player.properties['location'])
        dir_not_exists = tsentences.have(player.properties['location'][1], 'has', 'not', ['direction', direction])
        cont_res = tsentences.cont([can_not_go_res, dir_not_exists])
        cont_res.meta_sent.append(player_loc)
        log.append(cont_res)
    else:
        new_location = player.properties['location'][1].properties[direction]

    if len(log) == 0:
        new_location.objects.append(player)
        old_location = player.properties['location'][1]
        old_location_objs = copy.copy(old_location.objects)
        old_location.objects.remove(player)
        player.properties['location'][1] = new_location

        def undo(pla=player, old_loc=old_location, old_loc_objs=old_location_objs):
            pla.properties['location'][1].objects.remove(pla)
            pla.properties['location'][1] = old_loc
            del pla.properties['location'][1].objects[:]
            pla.properties['location'][1].objects.extend(old_loc_objs)

        player.undo_changes.append(undo)
        intro_location_res = look(new_location, player, 'in', player.properties['location'])
        player_moved_res = tsentences.go(player,
                                         None,
                                         None,
                                         'goes',
                                         direction,
                                         ['from', old_location])

        response = [player_moved_res] + [intro_location_res]
        log = [tsentences.cont(response)]
    return log


def opens(entity, player, location=None, location_position=None):
    """
    Returns the environment response after the player tries opening the entity at the location.

    To successfully open the entity, the entity has to be a door or a container that is openable, and that is not locked.
    Furthermore, the entity has to be closed. Otherwise, a negative feedback is returned.

    Parameters
    ----------
    entity : Entity
        The entity that is opened.
    player : Entity
        The player that tries opening the entity.
    location : Entity
        The location where the entity is found.
    location_position : str
        The location position where the entity is found. For example: on, in, under

    Returns
    -------
    log : list
        The list of valid responses.

    """
    if location is None:
        location = entity.properties["location"][1]
    if location_position is None:
        location_position = entity.properties["location"][0]

    prepos_location = [location_position, location]
    can_not_open = tsentences.opens(player,
                                    'can',
                                    'not',
                                    'open',
                                    entity
                                    )

    log = []
    visibility = entity.validate_reachability(player, location, can_not_open)
    log += visibility

    if entity.properties['location'] != prepos_location:
        item_not_loc_position = tsentences.be([entity, "'s", 'location'], 'is', 'not', prepos_location)
        res = tsentences.cont([can_not_open, item_not_loc_position])
        log.append(res)

    if "openable" not in entity.attributes:
        res = tsentences.be(entity,
                            "is",
                            "not",
                            "openable")

        res = tsentences.cont([can_not_open, res])
        log.append(res)

    if "locked" in entity.attributes:
        res = tsentences.be(entity,
                            "is",
                            None,
                            "locked")
        res = tsentences.cont([can_not_open, res])
        log.append(res)

    if "open" in entity.attributes:
        res = tsentences.be(entity, "is", None, "open")
        res = tsentences.cont([can_not_open, res])
        log.append(res)

    if len(log) == 0:
        res = tsentences.opens(player,
                               None,
                               None,
                               "opens",
                               entity)
        entity.attributes["open"] = None
        list_res = [res]

        res = tsentences.cont(list_res)

        def undo(ent=entity):
            del ent.attributes["open"]
        entity.undo_changes.append(undo)
        log.append(res)

    return log


def closes(entity, player, location, location_position):
    """
    Returns the environment response after the player tries closing the entity at a location.

    To successfully close the entity,
    the entity has to be a door or a container that is openable, and that is not locked.
    Furthermore, the entity has to be open. Otherwise, a negative feedback is returned.

    Parameters
    ----------
    entity : Entity
        The entity that is closed.
    player : Entity
        The player that tries closing the entity.
    location : Entity
        The location where the entity is found.
    location_position : str
        The location position where the entity is found. For example: on, in, under

    Returns
    -------
    log : list
        The list of valid responses.

    """
    prepos_location = [location_position, location]
    can_not_close = tsentences.close(player,
                                     'can',
                                     'not',
                                     'close',
                                     entity)
    log = []

    visibility = entity.validate_reachability(player, location, can_not_close)
    log += visibility

    if entity.properties['location'] != prepos_location:
        res = tsentences.be([entity, "'s", 'location'], 'is', 'not', prepos_location)
        res = tsentences.cont([can_not_close, res])
        log.append(res)

    if "openable" not in entity.attributes:
        res = tsentences.be(entity,
                            "is",
                            "not",
                            "openable")

        res = tsentences.cont([can_not_close, res])
        log.append(res)

    if "locked" in entity.attributes:
        res = tsentences.be(entity,
                            "is",
                            None,
                            "locked")
        res = tsentences.cont([can_not_close, res])
        log.append(res)

    if "open" not in entity.attributes:
        res = tsentences.be(entity, "is", "not", "open")
        res = tsentences.cont([can_not_close, res])
        log.append(res)

    if len(log) == 0:
        del entity.attributes["open"]
        res = tsentences.close(player,
                               None,
                               None,
                               "closes",
                               entity)

        def undo(ent=entity):
            ent.attributes["open"] = None
        entity.undo_changes.append(undo)
        log.append(res)

    return log


def get(entity, player, location, location_position):
    """
    Returns the environment response after the player tries getting the entity at the location.

    Parameters
    ----------
    entity : Entity
        The entity that the player tries taking.
    player : Entity
        The player that tries taking the entity.
    location : Entity
        The location where the entity is found.
    location_position : str
        The location position where the entity is found. For example: on, in, under

    Returns
    -------
    list
        The list of valid responses. If the entity is not gettable, a negative response is returned.

    """

    prepos_location = [location_position, location]

    can_not_get_res = tsentences.get(player,  'can', 'not', 'get', entity)

    log = []
    visibility = entity.validate_reachability(player, location, can_not_get_res)
    log += visibility

    if entity.properties['location'] != prepos_location:
        res = tsentences.be([entity, "'s", 'location'], 'is', 'not', prepos_location)
        res = tsentences.cont([can_not_get_res, res])
        log.append(res)

    if 'static' in entity.attributes:
        res = tsentences.be(entity, 'is', None, 'static')
        res = tsentences.cont([can_not_get_res, res])
        log.append(res)

    if 'player' in entity.attributes:
        res = tsentences.be(entity, 'is', None, 'player')
        getting_players = tsentences.get(rel="getting", entity="players")
        del getting_players.parts[-1]
        res1 = tsentences.permit(action_allowed=getting_players, neg="not", rel="permitted")

        res = tsentences.cont([can_not_get_res, res, res1])
        log.append(res)

    if entity.properties['location'] == ['in', player]:
        res = tsentences.be([entity, "'s", 'location'], "is", None, ['in', player])
        res = tsentences.cont([can_not_get_res, res])
        log.append(res)

    if len(log) == 0:
        old_loc_position = entity.properties['location'][0]
        player.objects.append(entity)
        old_loc_objects = copy.copy(location.objects)
        location.objects.remove(entity)
        entity.properties['location'][1] = player
        entity.properties['location'][0] = "in"
        res = tsentences.get(player, None, None, 'gets', entity)

        def undo(ent=entity, old_location=location, old_loc_pos=old_loc_position, old_loc_objs=old_loc_objects):
            ent.properties['location'][1].objects.remove(ent)
            ent.properties['location'][1] = old_location
            ent.properties['location'][0] = old_loc_pos
            del old_location.objects[:]
            old_location.objects.extend(old_loc_objs)
        entity.undo_changes.append(undo)

        log.append(res)

    return log


def drop(entity, player, location, location_position):
    """
    Returns the environment response after the player tries dropping the entity at the location.

    Parameters
    ----------
    entity : Entity
        The entity that the player tries dropping.
    player : Entity
        The player that tries dropping the entity.
    location : Entity
        It represents the location where the entity should be dropped.
    location_position : str
        The preposition refers to the target location. For example: in, on, under.

    Returns
    -------
    list
        The list of valid responses. If the entity can not be dropped, a negative response is returned.

    """

    can_not_drop_res = tsentences.drop(player, 'can', 'not', 'drop', entity)

    log = []

    visibility = location.validate_reachability(player, location, can_not_drop_res)

    log += visibility

    if entity.properties['location'] != ['in', player]:
        item_not_inventory_res = tsentences.be([entity, "'s", 'location'], 'is', 'not', ['in', player])
        log.append(tsentences.cont([can_not_drop_res, item_not_inventory_res]))
    if entity == location:
        dropping_players = tsentences.drop(rel="dropping", entity=["the", "item", "in", "on", "or", "under", "itself"])
        del dropping_players.parts[-1]
        not_permitted = tsentences.permit(action_allowed=dropping_players, neg="not", rel="permitted")
        log.append(tsentences.cont([can_not_drop_res, not_permitted]))

    loc_path = em_helpers.item_path(location)
    if entity in loc_path:
        sub_log = []
        for ent in loc_path:
            if ent == entity:
                break
            sub_log.append(tsentences.be([ent, "'s", "location"], "is", None, ent.properties["location"]))
        if len(sub_log) > 0:
            log.append(tsentences.cont([can_not_drop_res]+sub_log))
    if location_position == 'in':
        if 'container' not in location.attributes and 'place' not in location.attributes:
            item_is_not_container = tsentences.be(location, 'is', 'not', 'container')
            item_is_not_place = tsentences.be(location, 'is', 'not', 'place')
            log.append(tsentences.cont([can_not_drop_res, item_is_not_container, item_is_not_place]))
        elif 'container' in location.attributes and entity > location:
            log.append(tsentences.cont([can_not_drop_res,
                                        tsentences.be([entity, "'s", "size"], "is", None, entity.properties['size']),
                                        tsentences.be([location, "'s", "size"], "is", None, location.properties['size']),
                                        ]))

    elif location_position == 'on':
        if 'supporter' not in location.attributes:
            item_is_not_supporter = tsentences.be(location, 'is', 'not', 'supporter')
            log.append(tsentences.cont([can_not_drop_res, item_is_not_supporter]))
    elif location_position == 'under':
        if 'hollow' not in location.attributes:
            item_is_not_hollow = tsentences.be(location, 'is', 'not', 'hollow')
            log.append(tsentences.cont([can_not_drop_res, item_is_not_hollow]))
    else:
        list_loc_pos = ['in', 'on', 'under']
        entity.random_gen.shuffle(list_loc_pos)
        loc_pos_res = tsentences.be(['The', 'location', 'position'],
                                    'is',
                                    'not',
                                    (set(list_loc_pos), lhelpers.convert_obj_to_part(em_helpers.join_el_conn(list_loc_pos,
                                                                                                             "or"))))
        log.append(loc_pos_res)

    if len(log) == 0:
        old_loc_objects = copy.copy(player.objects)
        player.objects.remove(entity)
        location.objects.append(entity)
        entity.properties['location'][1] = location
        old_loc_pos = entity.properties['location'][0]
        entity.properties['location'][0] = location_position
        drop_res = tsentences.drop(player,
                                   None,
                                   None,
                                   'drops',
                                   entity,
                                   [location_position, location])

        def undo(enti=entity, old_location=player, old_location_position=old_loc_pos, old_loc_objs=old_loc_objects):
            enti.properties['location'][1].objects.remove(enti)
            enti.properties['location'][1] = old_location
            enti.properties['location'][0] = old_location_position
            del old_location.objects[:]
            old_location.objects.extend(old_loc_objs)

        entity.undo_changes.append(undo)
        log.append(drop_res)

    return log


def change(entity, player, element_key, element_val):
    """
    Changes the entity.properties[element_key] to element_val if possible.
      

    The properties that can be changed are indicated in world.change_action_properties. Also, it is checked if changing
    the item's property will make two item descriptions the same.
    For example, if John Mustermann wants to change the name to Jim and there
    is already a person named Jim Mustermann this would not be possible.
    For color and size, the item has to initially be taken by the player.
    This resembles a person picking up something before coloring it (or changing the item's size).


    Parameters
    ----------
    entity: Entity
        The entity in which the property is going to be changed.
    player : Entity
        The player that tries to change the entity.
    element_key : str or tuple
        The property key to be potentially changed.
    element_val : any
        The new property value.

    Returns
    -------
    list
        The list of valid responses.

    """

    if isinstance(element_key, tuple):
        element_key_list = list(element_key)
    else:
        element_key_list = [element_key]

    log = []
    if isinstance(element_val, list):
        can_not = tsentences.change(player,  'can', 'not', 'change', [entity, "'s"]+element_key_list, ['to']+element_val)
    else:
        can_not = tsentences.change(player,  'can', 'not', 'change', [entity, "'s"]+element_key_list, ['to']+[element_val])

    if element_key not in entity.world.change_action_properties:
        el_key = ['the']+list(element_key) if isinstance(element_key, (set, tuple)) else ['the', element_key]

        changing_not_allow = tsentences.permit(tsentences.change(rel="changing",
                                                                 thing_changing=el_key),
                                               "not",
                                               "permitted")
        del changing_not_allow.parts[0].parts[-1]
        log.append(tsentences.cont([can_not, changing_not_allow]))

    if element_key in ['name', 'surname', 'nickname']:
        if 'player' not in entity.attributes:
            sent1 = tsentences.be(entity, "is", "not", "player")
            log.append(tsentences.cont([can_not, sent1]))
        else:
            list_vals = getattr(entity.world, "player_"+element_key+"s")
            if element_val not in list_vals:
                sent1 = tsentences.be(element_val,
                                      "is",
                                      "not",
                                      ["player", element_key])
                log.append(tsentences.cont([can_not, sent1]))

    if element_key in entity.world.change_action_properties:
        if isinstance(element_key, tuple):
            list_vals = getattr(entity.world, "_".join(element_key)+"s")
        else:
            list_vals = getattr(entity.world, element_key+"s")
        if element_val not in list_vals:
            sent1 = tsentences.be(element_val,
                                  "is",
                                  "not",
                                  list(element_key) if isinstance(element_key, tuple) else element_key)
            log.append(tsentences.cont([can_not, sent1]))

    if element_key in ['size', 'color'] and entity not in player.objects:
        sent1 = tsentences.be([entity, "'s", 'location'], 'is', 'not', ['in', player])
        sent2 = tsentences.permit(action_allowed=tsentences.change(rel="changing",
                                                                   thing_changing=['the', 'item', "'s", element_key]),
                                  rel="permitted")
        del sent2.parts[-1]
        sent21 = tsentences.be(['if', 'item'], 'is', None, ['in', 'player'])
        sent2.describers[0].args['AM-ADV'] = lc.Arg(sent21, sent21)
        sent2.parts.append(sent21)
        log.append(tsentences.cont([can_not, sent1, sent2]))

    old_val = entity.properties.get(element_key, None)

    if old_val == element_val:
        sent = tsentences.be([entity, "'s"]+element_key_list, 'is', None, element_val)
        log.append(tsentences.cont([can_not, sent]))

    prev_player_desc = player.describe()
    prev_item_desc = entity.describe()
    entity.properties[element_key] = element_val
    old_prop_val = entity.prop_seen.get(element_key, None)
    entity.prop_seen[element_key] = element_val

    def undo(ent=entity, old_value=old_val, elem_key=element_key):
        if old_value is None:
            del ent.properties[elem_key]
        else:
            ent.properties[elem_key] = old_value

    def undo_prop_seen(ent=entity, elem_key=element_key, old_prop_value=old_prop_val):
        if old_prop_value is None:
            del ent.prop_seen[elem_key]
        else:
            ent.prop_seen[elem_key] = old_prop_value

    all_conflicting = []

    for wobj in entity.world.obj_list:
        if element_key in wobj.properties and wobj.properties[element_key] == element_val:
            desc = wobj.generate_description(relaxed=False)

            if desc is None and wobj not in all_conflicting:
                all_conflicting.append(wobj)

    if len(all_conflicting) > 0:
        undo()
        undo_prop_seen()
        for obj in all_conflicting:
            if not isinstance(element_val, list):
                sent = tsentences.be(['The', 'change', 'from', entity] + element_key_list + ['to', element_val],
                                     "is",
                                     None,
                                     ["conflicting", "with", obj])
            else:
                sent = tsentences.be(['The', 'change', 'from', entity] + element_key_list + ['to'] + element_val,
                                     "is",
                                     None,
                                     ["conflicting", "with", obj])
            obj_is_val = tsentences.be([obj, "'s", element_key], "is", None, element_val)
            sent.meta_sent.append(obj_is_val)
            log.append(tsentences.cont([can_not, sent]))
    else:
        if len(log) == 0:
            undo_prop_seen()
            entity.undo_changes.append(undo)
            element_key_part = lhelpers.convert_obj_to_part(element_key_list)
            if isinstance(element_val, list):
                sent = tsentences.change((player, prev_player_desc),  None, None, 'changes',
                                         ([entity, "'s"]+element_key_list,
                                          [prev_item_desc, lc.Word("'s")]+element_key_part),
                                         ['to'] + element_val)

            else:
                sent = tsentences.change((player, prev_player_desc),  None, None, 'changes',
                                         ([entity, "'s"]+element_key_list,
                                          [prev_item_desc, lc.Word("'s")]+element_key_part),
                                         ['to', element_val])

            meta_sent = tsentences.be([entity, "'s"]+element_key_list, 'is', None, element_val)
            sent.meta_sent.append(meta_sent)
            log.append(sent)
        else:
            undo_prop_seen()
            undo()
    return log


def objects_loc_pos(entity, location_preposition):
    """ Returns the entity's objects that have a specific location preposition.

        For example, if the carrot's location is ['on', kitchen_table] then the carrot's location preposition is 'on'.
        If the <entity> is the kitchen_table and the location_preposition is "on", then the carrot will be part of the
        returned objects.
    """
    holder_objects = list()
    for obj in entity.objects:
        if obj.properties['location'][0] == location_preposition:
            holder_objects.append(obj)

    if len(holder_objects) > 1:
        entity.random_gen.shuffle(holder_objects)
        num_items = entity.random_gen.randint(1, len(holder_objects))
        holder_objects = holder_objects[0:num_items]
    set_objects = set(holder_objects)

    if len(holder_objects) == 1:
        holder_objects = holder_objects[0]
        set_objects = list(set_objects)[0]
    elif len(holder_objects) == 0:
        holder_objects = None
        set_objects = None

    return holder_objects, set_objects


def look_place(entity, player, location_preposition):
    """
    Returns the environment response after a player looks in a place.

    Parameters
    ----------
    entity : Entity
        The entity that the player looks in. The entity has to be a place (have attribute 'place').
    player : Entity
        The player that looks.
    location_preposition : str
        The preposition has to be 'in' in order to return a non-empty response.

    Returns
    -------
    list
        A list comprising one sentence indicating the objects that the player sees in the place.
    """

    if 'place' not in entity.attributes or location_preposition != 'in':
        return []

    log = []
    objects, set_objects = objects_loc_pos(entity, location_preposition)

    if objects is None:
        place_is_empty_res = tsentences.have(entity,
                                             'has',
                                             'not',
                                             'items',
                                             [location_preposition, entity])
        log.append(place_is_empty_res)
    else:
        log.append(tsentences.see(player,
                                  None,
                                  'sees',
                                  (set_objects,
                                   lhelpers.convert_obj_to_part(em_helpers.join_el_conn(objects, ",")))))

    return log


def look_supporter(entity, location_preposition):
    """
    Returns the environment response after a player looks on top of the entity.

    Parameters
    ----------
    entity : Entity
        The entity that the player looks on. The entity has to have the attribute 'supporter'.
    location_preposition : str
        The preposition has to be 'on' in order to return a non-empty response.

    Returns
    -------
    list
        A list comprising a single sentence outputting what items the entity has on top of it or outputting that the entity
        contains no items.

    """
    if 'supporter' not in entity.attributes or location_preposition != 'on':
        return []
    supporter_objects, set_objects = objects_loc_pos(entity, location_preposition)
    if supporter_objects is not None:

        contains_res = tsentences.have(entity,
                                       'has',
                                       None,
                                       (set_objects,
                                        lhelpers.convert_obj_to_part(em_helpers.join_el_conn(supporter_objects, ","))),
                                       [location_preposition, entity])
        return [contains_res]

    does_not_have = tsentences.have(entity,
                                    'has',
                                    'not',
                                    'items',
                                    [location_preposition, entity])
    return [does_not_have]


def look_container(entity, location_preposition, can_not_look_res):
    """
    Returns the environment response after a player looks in the container entity.

    Parameters
    ----------
    entity : Entity
        The entity that the player looks in. The entity has to be a supporter (have attribute 'container').
    location_preposition : str
        The preposition has to be 'in' in order to return a non-empty response.
    can_not_look_res : Sentence
        The sentence "<player> can not look in <entity>" is used if looking in the container is not possible.
        For example, this can happen if the container is not opened or the container is locked.

    Returns
    -------
    list
        A list comprising a single sentence outputting what items the entity has in it or outputting that the entity
        contains no items.

    """
    if 'container' not in entity.attributes or location_preposition != 'in':
        return []
    if 'locked' in entity.attributes:
        container_is_locked = tsentences.be(entity, 'is', None, 'locked')
        res = [can_not_look_res, container_is_locked]
        return res

    if 'open' in entity.attributes:
        container_objects, set_objects = objects_loc_pos(entity, location_preposition)
        if container_objects is not None:
            contains_res = tsentences.have(entity,
                                           'has',
                                           None,
                                           (set_objects,
                                            lhelpers.convert_obj_to_part(em_helpers.join_el_conn(container_objects, ","))),
                                           [location_preposition, entity])
            return [contains_res]
        container_is_empty_res = tsentences.have(entity,
                                                 'has',
                                                 'not',
                                                 'items',
                                                 [location_preposition, entity])
        return [container_is_empty_res]

    container_is_closed_res = tsentences.be(entity, 'is', 'not', 'open')
    return [can_not_look_res, container_is_closed_res]


def look_hollow(entity, location_preposition):
    """
    Returns the environment response after a player looks under a hollow entity.

    Parameters
    ----------
    entity : Entity
        The entity should have an attribute hollow.
    location_preposition : str
        The location position should be 'under', otherwise empty list is returned.

    Returns
    -------
    list
        A comprising a single sentence outputting what items the entity has under it or outputting that the entity
        has no items under.
    """

    if 'hollow' not in entity.attributes or location_preposition != 'under':
        return []
    objects_under, set_objects = objects_loc_pos(entity, location_preposition)
    if objects_under is not None:
        contains_res = tsentences.have(entity,
                                       'has',
                                       None,
                                       (set_objects,
                                        lhelpers.convert_obj_to_part(em_helpers.join_el_conn(objects_under, ","))),
                                       [location_preposition, entity])
        return [contains_res]

    does_not_have = tsentences.have(entity,
                                    'has',
                                    'not',
                                    'items',
                                    [location_preposition, entity])
    return [does_not_have]


def look_object_response(entity, player, location_position, can_not_look_res):
    """
    Finds the suitable response when the player looks in/on/under the entity depending on the entity's properties and attributes.
    For example, if the entity is a table (which is a supporter) and the location preposition is 'on',
    then the look_supporter function is called, and the items that are on top of the table are given
    as part of the environmental response.

    If there is no suitable response found, the sentence: There is nothing special about <entity> is returned.

    Parameters
    ----------
    entity : Entity
        The entity that the player looks in/on/under.
    player : Entity
        The player that performs the look action.
    location_position : str
        A location preposition: in, on, or under.
    can_not_look_res : Sentence
        The sentence is used if looking at the entity is not possible. For example,
        "<player> can not look <location_preposition> entity"

    Returns
    -------
    log : list
        A list of one or multiple sentences. These sentences represent a single response (not multiple valid ones).
        Inside the :func:`look() <dialoguefactory.environment.actions.look>` function, the sentences are merged
        into a single one using the function :func:`cont() <dialoguefactory.language.sentences.cont>`.
    """
    log = []
    look_res = tsentences.look(player,
                               None,
                               None,
                               'looks',
                               [location_position, entity]
                               )

    if 'type' in entity.properties and entity.properties['type'] == 'door' and location_position == 'at':
        if 'open' not in entity.attributes:
            res = tsentences.be(entity, "is", "not", "open")
        else:
            res = tsentences.be(entity, "is", None, "open")

        log += [res]

    place_res = look_place(entity, player, location_position)
    if len(place_res) > 0:
        return [look_res] + place_res

    log += look_inventory(entity, location_position)
    log += look_supporter(entity, location_position)
    log += look_container(entity, location_position, can_not_look_res)
    log += look_hollow(entity, location_position)

    if len(log) == 0:
        if location_position == 'in':
            for attr in ['container', 'place', 'player']:
                if attr not in entity.attributes:
                    res = tsentences.be(entity, 'is', 'not', attr)
                    log += [res]
        elif location_position == 'on':
            if 'supporter' not in entity.attributes:
                item_is_not_supporter = tsentences.be(entity, 'is', 'not', 'supporter')
                log += [item_is_not_supporter]
        elif location_position == 'under':
            if 'hollow' not in entity.attributes:
                item_is_not_hollow = tsentences.be(entity, 'is', 'not', 'hollow')
                log += [item_is_not_hollow]
        if len(log) != 0:
            log.insert(0, can_not_look_res)
        else:
            nothing_special_res = tsentences.be((None, lc.Word('There')),
                                                'is',
                                                None,
                                                ['nothing', 'special', 'about', entity]
                                                )

            log = [nothing_special_res]

    if not em_helpers.check_can_not(log, "look"):
        log.insert(0, look_res)
    return log


def look_inventory(entity, location_preposition):
    """
    Returns the environment response after a player looks in another player's inventory or in its own inventory.

    Parameters
    ----------
    entity : Entity
        The entity should have an attribute player.
    location_preposition : str
        The location position should be 'in', and it refers to looks in <entity>.

    Returns
    -------
    response : list
        A list of single sentence outputting what items the player contains or outputting that the player
        has no items.  If the location position is not 'in', an empty response is returned.
    """
    if "player" not in entity.attributes or location_preposition != 'in':
        response = []
    elif len(entity.objects) > 0:
        visible_objects, set_objects = objects_loc_pos(entity, location_preposition)
        inventory_contains_res = tsentences.have(entity,
                                                 'has',
                                                 None,
                                                 (set_objects,
                                                  lhelpers.convert_obj_to_part(em_helpers.join_el_conn(visible_objects, ","))),
                                                 ['in', entity]
                                                 )
        response = [inventory_contains_res]
    else:
        inventory_is_empty_res = tsentences.have(entity,
                                                 'has',
                                                 'not',
                                                 'items',
                                                 ['in', entity])
        response = [inventory_is_empty_res]
    return response


def look(entity, player, position, location):
    """
    Returns the environment response after the player looks (in/on/under) the entity at the specified location.

    Please refer to look_object_response for more information.

    Parameters
    ----------
    entity : Entity
        The entity that the player looks in/on/under.
    player : Entity
        The player looking in/on/under the entity.
    position : str
        The location preposition ('in', 'on', 'under').
    location : list
        The location is a list of two values: a location preposition (string) and a location (Entity).
        The location refers to where the entity is located.

    Returns
    -------
    log : list
        A list of valid responses

    """
    can_not_look = tsentences.look(player,
                                   'can',
                                   'not',
                                   'look',
                                   [position, entity]
                                   )

    visibility = entity.validate_reachability(player, location[1], can_not_look)
    log = []
    log += visibility

    if entity.properties['location'] != location:
        item_not_loc_position = tsentences.be([entity, "'s", 'location'], 'is', 'not', location)
        log.append(tsentences.cont([can_not_look, item_not_loc_position]))

    partial_log = look_object_response(entity, player, position, can_not_look)
    if can_not_look in partial_log:
        log.append(tsentences.cont(partial_log))
    else:
        if len(log) == 0:
            log = [tsentences.cont(partial_log)]

    return log

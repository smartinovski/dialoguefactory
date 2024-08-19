#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the functions that update the KnowledgeBase.
"""

from ..language import components as lc
from ..language import describers as tdescribers
from ..language import sentences as tsentences

from . import kn_helpers
from . import kn_parsers

from ..environment import entities as em


def basic_update(kb_state, sent):
    """
    Add the sentence to the list of factual sentences (in the sent_db) and
    remove the opposite sentence if it exists. The sentence has to come from a trusted source.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base to be potentially updated.
    sent : Sentence
        The sentence that is considered to be added.

    Returns
    -------
    None.

    """

    if sent not in kb_state.sent_db:
        kb_state.sent_db.add(sent)

        def undo_add(know_base=kb_state, sentence=sent):
            know_base.sent_db.discard(sentence)

        kb_state.undo_changes.append(undo_add)

    opposite_sent = kn_helpers.create_oppos_sent(sent)
    if opposite_sent in kb_state.sent_db:
        kb_state.sent_db.remove(opposite_sent)

        def undo_remove(know_base=kb_state, sentence=opposite_sent):
            know_base.sent_db.add(sentence)

        kb_state.undo_changes.append(undo_remove)


def property_update(kb_state, sent):
    """
    Extract the entity, property key, property value, and the negation from the following sentence:

    ..

        <entity> 's' <property_key> is <property_value>

        or

        <entity> is <attribute>

    and calls the :func:`property_update_alt() <dialoguefactory.state.kn_updaters.property_update_alt>` function.
    In case the updater can extract additional information from the sentence,
    it updates the knowledge base with further information, too.
    For example, if a door is locked, it means that the door is not open as well.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base to be updated.
    sent : Sentence
        The sentence in the aforementioned forms.

    Returns
    -------
    None.

    """

    mem = kn_helpers.check_prop(sent)
    if mem is not None:
        ent, pkey, pval, pneg = mem
        property_update_alt(kb_state, ent, pkey, pval, pneg)

        ent = getattr(kb_state.world, ent.get_property("var_name"), None)
        if ent is not None:
            if pkey is None:
                if pval == 'locked' and pneg is None and 'locked' in ent.attributes:
                    property_update_alt(kb_state, ent, None, "open", "not")
            else:
                if pkey == 'type' and pneg is None and ent.properties['type'] == pval:
                    if 'place' in ent.attributes:
                        if 'location' in ent.properties:
                            property_update_alt(kb_state, ent, "location", ent.properties['location'], None)
    return None


def property_update_alt(kb_state, ent, pkey, pval, pneg):
    """
    Updates one of the following dictionaries:

    ..

        :attr:`ent.prop_seen <dialoguefactory.environment.entities.Entity.prop_seen>`,
        :attr:`ent.prop_seen_neg <dialoguefactory.environment.entities.Entity.prop_seen_neg>`,

        :attr:`ent.attr_seen <dialoguefactory.environment.entities.Entity.attr_seen>`,
        :attr:`ent.attr_seen_neg <dialoguefactory.environment.entities.Entity.attr_seen_neg>`

    where each of the entities is taken from kb_state.world in case the entity is a copy.
    entity.prop_seen and entity.attr_seen are updated if the property
    or the attribute is observed by one of the agents. The _neg version is updated if it's seen
    that the entity's pkey is not pval or the entity does not contain the attribute.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base is used to fetch the world.
    ent : Entity
        The entity to be updated.
    pkey : str or None
        The property key if a property is updated. For an attribute, this value is None.
    pval : any
        The property value if a property is updated. Otherwise, it represents an attribute.
    pneg : str or None
        If the pneg is present, the _neg version of the dictionaries is updated.

    Returns
    -------
    None.

    """
    if isinstance(ent, em.Entity):
        world_ent = getattr(kb_state.world, ent.get_property("var_name"), None)
    else:
        world_ent = None

    if world_ent is None:
        return None

    if pkey is not None:

        if not ((isinstance(pkey, str) or isinstance(pkey, tuple)) and pkey in world_ent.properties
                and ((pneg is None and world_ent.properties[pkey] == pval)
                     or (pneg is not None and world_ent.properties[pkey] != pval))):
            return None

        if pneg is None:
            kn_helpers.add_prop_seen(kb_state, world_ent, pkey, pval)
            kn_helpers.remove_prop_seen_neg(kb_state, world_ent, pkey, pval)
        else:
            kn_helpers.add_prop_seen_neg(kb_state, world_ent, pkey, pval)
            if pkey in world_ent.prop_seen and world_ent.prop_seen[pkey] == pval:
                kn_helpers.remove_prop_seen(kb_state, world_ent, pkey)

    else:
        if not ((isinstance(pval, str) or isinstance(pval, tuple))
                and ((pneg is None and pval in ent.attributes) or (pneg is not None and pval not in ent.attributes))):
            return None

        if pneg is None:
            kn_helpers.add_attr_seen(kb_state, world_ent, pval, None)
            kn_helpers.remove_attr_seen(kb_state, world_ent, pval, "not")

        else:
            kn_helpers.add_attr_seen(kb_state, world_ent, pval, pneg)
            kn_helpers.remove_attr_seen(kb_state, world_ent, pval, None)
    return None


def update_elem_exists(kb_state, sent):
    """
    Checks whether the sentence is in the form described in kn_parsers.elem_exists_parse
    and if so, extracts the arguments and calls the update_elem_exists_alt function.

    """
    parsed = kn_parsers.elem_exists_parse(sent)
    if parsed is not None:
        ent, elem, pneg = parsed
        update_elem_exists_alt(kb_state, ent, elem, pneg)


def update_elem_exists_alt(kb_state, ent, elem, pneg):
    """
    Updates one of the following dictionaries:

        :attr:`ent.elem_exists <dialoguefactory.environment.entities.Entity.elem_exists>` or
        :attr:`ent.elem_not_exists <dialoguefactory.environment.entities.Entity.elem_not_exists>`

    This happens when the agent observes that the entity has/hasn't a property or an attribute (element).
    The information is checked for its truthfulness before the update is made.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base is used to fetch the world.
    ent : Entity
        The entity to be updated.
    elem : str
        The property or attribute that the entity has/hasn't. An example can be
        'color' (property) or 'locked' (attribute)
    pneg : str
        If pneg is not None, then the entity.elem_not_exists is updated

    Returns
    -------
    None.

    """
    world_ent = getattr(kb_state.world, ent.get_property("var_name"), None)
    if world_ent is None:
        return None
    cond = False
    if elem in world_ent.properties or elem in world_ent.attributes:
        cond = True

    cond = cond if pneg is None else not cond
    if cond:

        if pneg is None:
            if elem not in world_ent.elem_exists:
                world_ent.elem_exists.add(elem)

                def undo_exists(entity=world_ent, element=elem):
                    entity.elem_exists.discard(element)

                kb_state.undo_changes.append(undo_exists)

            if elem in world_ent.elem_not_exists:
                world_ent.elem_not_exists.discard(elem)

                def undo_not_exists(entity=world_ent, element=elem):
                    entity.elem_not_exists.add(element)
                kb_state.undo_changes.append(undo_not_exists)

        else:
            if elem not in world_ent.elem_not_exists:
                world_ent.elem_not_exists.add(elem)

                def undo_not_exists(entity=world_ent, element=elem):
                    entity.elem_not_exists.discard(element)
                kb_state.undo_changes.append(undo_not_exists)

            if elem in world_ent.elem_exists:
                world_ent.elem_exists.discard(elem)

                def undo_elem_exists(entity=world_ent, element=elem):
                    entity.elem_exists.add(element)
                kb_state.undo_changes.append(undo_elem_exists)

    return None


def have_update(kb_state, sent):
    """
    Marks the location of the entities that belong to a possessor as observed.

    The sentence is in the form described in kn_parsers.have_parse.
    It also marks the location of the entities as exclusive,
    meaning they do not belong to any other entity in the world.
    If the possessor does not have entities, the location of all objects in the world
    is marked that it is not in the possessor's possession.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base to be updated.
    sent : Sentence
        The sentence form is described in kn_parsers.have_parse

    Returns
    -------
    None.

    """
    mem = kn_parsers.have_parse(sent)
    if mem is None:
        return

    owner, possession, neg, loc = mem
    if loc is None:
        loc = ['in', owner]

    if possession == "items" and neg is not None:
        all_objects = kb_state.world.obj_list
        for obj in all_objects:
            property_update_alt(kb_state, obj, "location", loc, "not")
    else:
        if isinstance(possession, set):
            possession = list(possession)
        elif not isinstance(possession, list):
            possession = [possession]

        for obj in possession:
            property_update_alt(kb_state, obj, "location", loc, neg)

        if neg is None:
            all_objects = kb_state.world.obj_list
            for obj in all_objects:
                if obj not in possession:
                    property_update_alt(kb_state, obj,  "location", loc, "not")


def go_updater(kb_state, sent):
    """
    Marks the player's location as observed if the following sentence appears:

    ..

        <player> goes <direction> <start_point>

    Also, it marks the <start_point>'s direction as observed.
    For the sentence: The bear goes south from the barn to the main path,
    the last seen location of the bear is updated (bear.prop_seen['location']=main_path),
    and also it updates that the barn
    has direction south to the main path (barn.prop_seen['south']=main_path)

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base.
    sent : Sentence
        The sentence in the form above.

    Returns
    -------
    None.

    """
    if len(sent.describers) > 0 and len(sent.describers) == 3:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) == "go" and lc.verb_tense(rel) in lc.PRESENT_TENSES:
            player = describer.get_arg("Arg-PPT")
            direction = describer.get_arg("AM-DIR")
            start_point = describer.get_arg("Arg-DIR")

            mapped_desc = tdescribers.go((player, None), (None, None), (None, None), (rel, None),
                                         (direction, None), (start_point, None))
            if mapped_desc == describer:
                if not (isinstance(start_point, list) and start_point[0] == "from"
                        and isinstance(start_point[1], em.Entity)):
                    return None
                player_look = sent.describers[1].get_arg("Arg-PPT")
                thing_looked = sent.describers[1].get_arg("Arg-GOL")
                rel_look = sent.describers[1].get_arg("Rel")
                if lc.verb_inf(rel_look.lower()) == "look" and lc.verb_tense(rel_look) in lc.PRESENT_TENSES:
                    look_desc = tdescribers.look((player_look, None), (None, None), (None, None),
                                                 (rel_look, None), (thing_looked, None))
                    if (look_desc == sent.describers[1] and player == player_look and isinstance(direction, str)
                            and thing_looked[1] == start_point[-1].properties[direction]):
                        if direction is not None and player is not None:
                            property_update_alt(kb_state, start_point[-1], direction,
                                                start_point[1].properties[direction], None)

                        property_update_alt(kb_state, player, "location", thing_looked, None)
    return None


def get_updater(kb_state, sent):
    """
    Marks the location of the taken item as observed. The location of the player getting the item is marked as well.
    The sentence should be in the following form:

    ..

        <player> gets <entity> (from_location)

    For example, Andy gets the spoon from the table.

    Parameters
    ----------
    kb_state : KnowledgeBase
        The knowledge base.
    sent : Sentence
        The sentence in the form above.

    Returns
    -------
    None.

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "get" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return

        player = describer.get_arg("Arg-PAG")
        thing_gotten = describer.get_arg("Arg-PPT")
        giver = describer.get_arg("Arg-DIR")
        mapped_sent = lc.Sentence()
        mapped_desc = tdescribers.get((player, None), (None, None), (None, None), (rel, None),
                                      (thing_gotten, None), (giver, None))
        mapped_sent.describers.append(mapped_desc)
        if mapped_sent == sent:
            if all(map(isinstance, [player, thing_gotten], [em.Entity, em.Entity])):
                property_update_alt(kb_state, thing_gotten, "location", ["in", player], None)


def drop_updater(kb_state, sent):
    """
    Marks the location of the dropped item as observed. The location of the player dropping the item is marked as well.
    The sentence should be in the following form:

    ..

        <player> drops <entity> <at_location>

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "drop" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return

        player = describer.get_arg("Arg-PAG")
        thing_dropped = describer.get_arg("Arg-PPT")
        location = describer.get_arg("Arg-GOL")
        mapped_sent = lc.Sentence()
        mapped_desc = tdescribers.drop((player, None), (None, None), (None, None), (rel, None),
                                       (thing_dropped, None), (location, None))
        mapped_sent.describers.append(mapped_desc)
        if mapped_sent == sent:
            if (all(map(isinstance, [player, thing_dropped, location], [em.Entity, em.Entity, list]))
                    and len(location) == 2 and isinstance(location[-1], em.Entity)
                    and location[-2] in kb_state.world.location_positions):
                for ent in [player, thing_dropped]:
                    property_update_alt(kb_state, ent, "location", location, None)


def see_updater(kb_state, sent):
    """ Marks the location of the player and the items that the player sees as observed.
        The sentence should be in the following form:

        ..

            <player> sees <entity_1>, ... , <entity_n> <at_location>

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "see" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return

        player = describer.get_arg("Arg-PAG")
        things_seen = describer.get_arg("Arg-PPT")
        location = describer.get_arg("AM-LOC")

        mapped_sent = lc.Sentence()
        mapped_desc = tdescribers.see((player, None), (None, None), (rel, None),
                                      (things_seen, None), (location, None))
        mapped_sent.describers.append(mapped_desc)
        if mapped_sent == sent:
            if isinstance(things_seen, set):
                things_seen = list(things_seen)
            elif not isinstance(things_seen, (set, tuple, list)):
                things_seen = [things_seen]
            if (isinstance(player, em.Entity)
                    and isinstance(location, list)
                    and len(location) == 2
                    and isinstance(location[-1], em.Entity)
                    and location[-2] in kb_state.world.location_positions):

                for ent in things_seen + [player]:
                    property_update_alt(kb_state, ent, "location", location, None)


def look_updater(kb_state, sent):
    """
    Marks the location of the player and the item that it looks as observed.
    The sentence should be in the following form:

    ..

        <player> looks (preposition) <at_entity>

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "look" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return
        player = describer.get_arg("Arg-PPT")
        thing_looked = describer.get_arg("Arg-GOL")
        mapped_desc = tdescribers.look((player, None), (None, None), (None, None),
                                       (rel, None), (thing_looked, None))
        if describer == mapped_desc:

            if (isinstance(thing_looked, list)
                    and thing_looked[0] in kb_state.world.location_positions
                    and all(map(isinstance, [thing_looked[1], player], [em.Entity, em.Entity]))):
                for ent in [player, thing_looked[1]]:
                    property_update_alt(kb_state, ent, "location", thing_looked, None)
            if len(sent.describers) == 2:
                added = False
                if sent.describers[1].get_arg("AM-LOC") is None:
                    sent.describers[1].args["AM-LOC"] = lc.Arg(thing_looked)
                    added = True
                see_sent = lc.Sentence()
                see_sent.describers.append(sent.describers[1])
                see_updater(kb_state, see_sent)

                if added:
                    del sent.describers[1].args["AM-LOC"]


def opens_updater(kb_state, sent):
    """ If the sentence is in the format:

        ..

            <player> opens <entity_opened>

        , the <entity_opened> is marked as open and openable as well.
    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "open" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return

        opener = describer.get_arg("Arg-PAG")
        thing_opened = describer.get_arg("Arg-PPT")

        mapped_sent = lc.Sentence()
        mapped_desc = tdescribers.opens((opener, None), (None, None), (None, None),
                                        (rel, None), (thing_opened, None))
        mapped_sent.describers.append(mapped_desc)
        if mapped_sent == sent:
            if all(map(isinstance, [opener, thing_opened], [em.Entity, em.Entity])):
                property_update_alt(kb_state, thing_opened, None, "open", None)
                property_update_alt(kb_state, thing_opened, None, "openable", None)


def close_updater(kb_state, sent):
    """ If the sentence is in the format:

        ..

            <player> closes <entity_closed>

        the <entity_closed> is marked as not open and openable as well.
    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")

        if lc.verb_inf(rel.lower()) != "close" or lc.verb_tense(rel) not in lc.PRESENT_TENSES:
            return
        closer = describer.get_arg("Arg-PAG")
        thing_closed = describer.get_arg("Arg-PPT")
        location = describer.get_arg("AM-LOC")

        mapped_sent = lc.Sentence()
        mapped_desc = tdescribers.close((closer, None), (None, None), (None, None),
                                        (rel, None), (thing_closed, None), (location, None))
        mapped_sent.describers.append(mapped_desc)
        if mapped_sent == sent:
            if all(map(isinstance, [closer, thing_closed], [em.Entity, em.Entity])):
                property_update_alt(kb_state, thing_closed, None, "open", "not")
                property_update_alt(kb_state, thing_closed, None, "openable", None)


def change_updater(kb_state, sent):
    """

    Checks whether the sentence is in the following format, and if so, it adds it in the database:

    ..

        Changing <element_key> is not permitted.

    where <element_key> is part of the changeable properties
    (:attr:`world.change_action_properties <dialoguefactory.environments.world.World.change_action_properties>`)
    Before adding the sentence, its truthfulness is verified.

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        arg_ppt = describer.get_arg("Arg-PPT")
        if arg_ppt is None:
            return None
        changable_properties = kb_state.world.change_action_properties
        if isinstance(arg_ppt, lc.Sentence):
            element_key = arg_ppt.describers[0].get_arg("Arg-PPT")
            if tsentences.permit(tsentences.change(rel="changing", thing_changing=element_key), "not", "permitted") == sent and element_key not in changable_properties:
                basic_update(kb_state, sent)


def val_is_key_updater(kb_state, sent):
    """ Adds one of the following sentences in the database:

        ..

            <property_value> is (not) <property_key>

            or

            <str> is (not) direction.

        For example, "medium is not a color".
        The sentence is first checked for its truthfulness.
    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        arg_ppt = describer.get_arg("Arg-PPT")
        arg_prd = describer.get_arg("Arg-PRD")
        am_neg = describer.get_arg("AM-NEG")
        if (arg_ppt is None or arg_prd is None or
                sent != tsentences.be((arg_ppt, None), ("is", None), (am_neg, None), (arg_prd, None))):
            return None
        if isinstance(arg_prd, list):
            arg_prd = tuple(arg_prd)
        additional_prds = [('player', prop) for prop in ['name', 'nickname', 'surname']]
        if arg_prd not in kb_state.world.all_properties+['direction']+additional_prds:
            return None
        kn_checked = kb_state.world.check_val_is_key(arg_prd, arg_ppt)
        if kn_checked is True:
            if am_neg != "not":
                basic_update(kb_state, sent)
        elif kn_checked is False:
            if am_neg == "not":
                basic_update(kb_state, sent)


def permit_updater(kb_state, sent):
    """ Adds one of the following sentences in the database:

        - Changing the item's <element_key> is permitted if the item is in the player.
        - Getting players is not permitted.
        - Dropping the item in, on, or under itself is not permitted.

    where element_key is 'color' or 'size'.

    """
    if len(sent.describers) > 0:
        describer = sent.describers[0]
        rel = describer.get_arg("Rel")
        if rel == 'permitted':
            getting_players = tsentences.permit(tsentences.get(rel=("getting", None), entity=("players", None)),
                                                neg=("not", None), rel=("permitted", None))

            def gen_permit_sent(element_key):
                changing_elem_key = tsentences.permit(action_allowed=tsentences.change(rel=("changing", None),
                                                                                       thing_changing=(
                                                                                       ['the', 'item', "'s", element_key],
                                                                                       None)),
                                                      rel=("permitted", None))

                if_item_player = tsentences.be((['if', 'item'], None), ('is', None), (None, None),
                                               (['in', 'player'], None))
                changing_elem_key.describers[0].args['AM-ADV'] = lc.Arg(if_item_player, if_item_player)
                changing_elem_key.parts.append(if_item_player)
                return changing_elem_key

            changing_permit_sents = [gen_permit_sent("color"), gen_permit_sent("size")]
            dropping_items = tsentences.drop(rel=("dropping", None),
                                             entity=(["the", "item", "in", "on", "or", "under", "itself"], None),
                                             )
            dropping_not_permitted = tsentences.permit(action_allowed=dropping_items,
                                                       neg=("not", None),
                                                       rel=("permitted", None))

            if sent in [getting_players]+changing_permit_sents+[dropping_not_permitted]:
                basic_update(kb_state, sent)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the functions that help with the implementation of the policies.
"""
import copy

from . import goals as tgoals
from ..language import desc_mappers
from ..state import kn_checkers
from ..language import sentences as tsentences
from ..language import components as lc

from ..language import helpers as shelpers
from ..environment import helpers as em_helpers
from ..environment import actions
from ..environment import entities as em


def compute_policy_steps(policy, item,  can_not_action_res,
                         target_location, prepos_location, action_func,
                         action_params, action_res, action_step):
    """
    Computes the next policy steps and the goal for the agent, given the current context.

    Computes the agent's response to the user request:

        <policy.player> <action> (preposition) <item> <preposition> <location>

    The general algorithm works in such a way that if the player has the knowledge that it can not execute the action,
    then it has to provide a response in the following form:

        <policy.player> says: neg_res

    In case multiple neg_res are possible, they are prioritized in the following way:

        1. The neg_res is because the <action> can not be executed for a specific reason.
        2. The neg_res is because the item's location is not revealed.
        3. The neg_res is because the GoItemPolicy returned negative response
           (due to an obstacle or when the path is not revealed)

    For example, if the request is: Hannah, get the static toys container,
    and it was previously revealed that static items are not gettable,
    it is not important whether the location of the toys container is revealed nor whether
    there is a path to the toys container since the entity is not gettable anyway.

    Note that in each of the 1..3 cases, there might be multiple responses as well. For this reason,
    the goal :func:`goals.multiple_correct() <dialoguefactory.policies.goals.multiple_correct>` is used.

    If the <action> can be executed by the agent, then it utters the next step
    that leads the agent closer to the goal. During the dialogue turn, just the
    first step is taken, so it suffices to provide a single step.


    Parameters
    ----------
    policy : ActionPolicy
        An instance of the ActionPolicy where this function is called to compute the next steps.
    item : Entity
        The <item> in the user request.
    can_not_action_res : Sentence
        A sentence in the form: <policy.player> can not (preposition) <action> <item> <preposition> <location>
    target_location : Entity
        This is the location where the agent should go to act on the item.
        For example, for the action get, this is the item's location, and for the
        action drop, this is the location where the item should be dropped.
    prepos_location : list
        A list consisting of two elements, namely preposition (in, on, under) and location (Entity)
        This is the location where the item is supposedly at. Note that sometimes, prepos_location
        might not be the same as the target location. For example, the request can be: get the item <from_wrong_location>
        The prepos_location is allowed to be None as well.
    action_func : function
        A function that comes from the module environment.actions and is used to get the environment response.
    action_params : dict or tuple
        A dictionary mapping param_name: param_value, containing the parameters of the action_func or an ordered tuple
        (param_value1, param_value2 ...)
    action_res : Sentence
        A sentence in the form: <policy.player> <action> (preposition) <item> <preposition> <location>.
        It is used for checking whether the environment returns a positive response.
    action_step : Sentence
        The step in the form: <policy.player> tries (preposition) <action> <item> <preposition> <location>

    Returns
    -------
    steps : list
        The agent's next response. The list is in case multiple responses are valid.
    goal : Goal
        The goal of the agent's policy.

    """
    steps, goal = None, None

    prec_items = [policy.player, item]
    if prepos_location is not None:
        prec_items.append(prepos_location[1])

    prec_steps, prec_goal = prec_action_item(policy.dialogue, policy.player, prec_items, can_not_action_res)

    go_steps, go_goal = policy.go_location_policy.task(item, prepos_location, False)

    target_loc = target_location.top_location()
    loc_is_rev = tsentences.be(([policy.player, "'s", 'location'], None),
                               ('is', None),
                               (None, None),
                               (['in', target_loc], None))

    if policy.dialogue.dia_generator.knowledge_base.check(loc_is_rev):
        go_steps = []
        go_goal = tgoals.Goal(lambda: 1)

    sloc = policy.player.properties['location'][1].top_location()
    tloc = target_loc

    state = policy.dialogue.dia_generator.world.save_state()
    make_item_reachable(policy.player, sloc, tloc, policy.dialogue.dia_generator.world)
    open_all_containers(policy.player, item, policy.dialogue.dia_generator.world)
    orig_res = action_func(*action_params)
    policy.dialogue.dia_generator.world.recover_state(state)

    if action_res != shelpers.reduce_sentences([orig_res[0]])[0]:
        flattened_res = extract_reasons(orig_res)
        steps_checked, steps_not_checked = compute_say_steps(flattened_res,
                                                             orig_res,
                                                             policy.player,
                                                             policy.dialogue.dia_generator.knowledge_base)

        if len(steps_checked) > 0:
            steps = steps_checked
            goal = tgoals.Goal(tgoals.multiple_correct,
                               policy.dialogue,
                               policy.player,
                               steps_not_checked + steps_checked,
                               len(policy.dialogue.get_utterances()) - 1)
            return steps, goal

    state = policy.dialogue.dia_generator.world.save_state()
    make_item_reachable(policy.player, sloc, tloc, policy.dialogue.dia_generator.world)
    orig_res = action_func(*action_params)
    policy.dialogue.dia_generator.world.recover_state(state)

    substeps = []
    if action_res != shelpers.reduce_sentences([orig_res[0]])[0]:
        candidates_open = []
        curr_loc = item.properties['location'][1]

        flag_open = True
        while True:
            if "open" not in curr_loc.attributes:
                is_locked = tsentences.be((curr_loc, None),
                                          ("is", None),
                                          (None, None),
                                          ("locked", None))
                is_not_openable = tsentences.be((curr_loc, None),
                                                ("is", None),
                                                ("not", None),
                                                ("openable", None))
                if (policy.dialogue.dia_generator.knowledge_base.check(is_locked) is True or
                        policy.dialogue.dia_generator.knowledge_base.check(is_not_openable) is True):
                    flag_open = False

                    break
                candidates_open.insert(0, curr_loc)
            if 'location' in curr_loc.properties:
                new_loc = curr_loc.properties['location'][1]
                if new_loc == new_loc.properties['location'][1]:
                    break
                else:
                    curr_loc = new_loc
            else:
                break
        if flag_open:
            for item_loc in candidates_open:
                res3 = tsentences.be((item_loc, None), ("is", None), (None, None), ("container", None))
                res1 = tsentences.be((item_loc, None), ("is", None), (None, None), ("openable", None))
                res2 = tsentences.be((item_loc, None), ("is", None), ("not", None), ("open", None))
                if (prec_steps is None and policy.dialogue.dia_generator.knowledge_base.check(res3) is not False and
                        policy.dialogue.dia_generator.knowledge_base.check(res1) and
                        policy.dialogue.dia_generator.knowledge_base.check(res2)):
                    open_step = tsentences.tries(policy.player, None, None, "tries",
                                                 tsentences.opens(rel="opening",
                                                                  thing_opened=item_loc,
                                                                  prepos_location=copy.copy(item_loc.properties['location']),
                                                                  speaker=policy.player),
                                                 policy.player)
                    substeps.append(open_step)
        if len(substeps) == 0:

            flattened_res = extract_reasons(orig_res)
            steps_checked, steps_not_checked = compute_say_steps(flattened_res,
                                                                 orig_res,
                                                                 policy.player,
                                                                 policy.dialogue.dia_generator.knowledge_base)

            goal_multiple = tgoals.Goal(tgoals.multiple_correct,
                                        policy.dialogue,
                                        policy.player,
                                        steps_not_checked+steps_checked,
                                        len(policy.dialogue.get_utterances()) - 1
                                        )
            if len(steps_checked) > 0:
                steps = steps_checked
                goal = goal_multiple

                # The item can be still opened but the real reason is that it is not revealed.
                # This is part of validate visibility if the item is inside container and the container is
                # inside another container.

                if prec_steps is not None:
                    if "container" in item.properties["location"][1].attributes:
                        for step in steps:
                            inner_sentences = shelpers.reduce_sentences([step.describers[0].get_arg('Arg-PPT')])[1:]

                            for sent in inner_sentences:
                                if sent == desc_mappers.be(sent.describers) and sent.describers[0].get_arg('Arg-PRD') in ['open', 'openable', 'locked']:
                                    subj = sent.describers[0].get_arg("Arg-PPT")
                                    curr_loc = check_loc(policy.dialogue.dia_generator.knowledge_base,
                                                         item,
                                                         item.properties['location'])
                                    if curr_loc is not None:
                                        loc_path = []
                                        while True:
                                            if curr_loc == curr_loc.properties['location'][1]:
                                                break
                                            loc_path.append(curr_loc)
                                            curr_loc = curr_loc.properties['location'][1]

                                        if isinstance(subj, em.Entity) and subj not in prec_items and subj in loc_path:
                                            steps = prec_steps
                                            goal = prec_goal
                                            break
            else:
                if prec_steps is not None:
                    steps, goal = prec_steps, prec_goal
                elif len(go_steps) > 0 and desc_mappers.say([go_steps[0].describers[0]]) == go_steps[0] and em_helpers.check_can_not(shelpers.reduce_sentences([go_steps[0].describers[0].get_arg('Arg-PPT')]), "go"):
                    steps, goal = go_steps, go_goal
                    add_can_not(can_not_action_res, goal.args[2])
                else:
                    steps = go_steps if len(go_steps) > 0 else [action_step]

                    # The steps_not_checked will be checked after the environment provides the negative response
                    # So the agent has to utter the reason why the action can not be completed.

                    goal = goal_multiple
    if steps is None:
        if prec_steps is not None:
            steps, goal = prec_steps, prec_goal
        if len(go_steps) > 0 and desc_mappers.say([go_steps[0].describers[0]]) == go_steps[0] and em_helpers.check_can_not(shelpers.reduce_sentences([go_steps[0].describers[0].get_arg('Arg-PPT')]), "go"):
            steps, goal = go_steps, go_goal
            add_can_not(can_not_action_res, goal.args[2])
        else:
            substeps += [action_step]

    if goal is None:
        sub_goal = tgoals.Goal(tgoals.correct_steps_sublist, policy.dialogue,
                               policy.player, substeps,
                               len(policy.dialogue.get_utterances()) - 1)
        goal = tgoals.Goal(tgoals.goal_and, [go_goal, sub_goal])
        steps = go_steps if len(go_steps) > 0 else [substeps[0]]

    return steps, goal


def make_item_reachable(player, sloc, tloc, world):
    """ The player's path is cleared of obstacles in order to see if there is another reason
        the player can not act upon the item.

        Parameters
        ----------
        player : Entity
            The agent whose policy calls this function.
        sloc : Entity
            The starting point of the agent.
        tloc : Entity
            The finishing point of the agent.
        world : World
            The world is used to fetch the path from sloc to tloc.

        Returns
        -------
        None


    """
    if (sloc, tloc) in world.all_paths:
        dirs = world.all_paths[(sloc, tloc)]
    else:
        dirs = []

    for direction in dirs:
        player_loc = player.properties['location'][1]
        obs = None
        undo = lambda: None
        if (direction, 'obstacle') in player_loc.properties:
            obs = player_loc.properties[(direction, 'obstacle')]
            if 'locked' in obs.attributes:
                del obs.attributes['locked']

                def undo(obstacle=obs):
                    obstacle.attributes['locked'] = None

            if 'type' in obs.properties and obs.properties['type'] == 'door':
                actions.opens(obs, player, obs.properties['location'][1], obs.properties['location'][0])
        actions.go(player, direction)
        undo()


def open_all_containers(player, item, world):
    """ If the item is potentially located in a container, it opens/unlocks the container. Additionally, it opens all containers
        on the way until the top location is reached (if that container is part of another container).

        For actions.opens to work, we have to open the innermost container first.

        Parameters
        ----------
        player : Entity
            The agent whose policy calls this function.
        item : Entity
            The starting point of the agent.
        world : World
            The world is used to save the changes made when opening or unlocking the containers.

        Returns
        -------
        None
    """
    curr_loc = item.properties["location"][1]
    all_locations = [curr_loc]

    while True:
        if curr_loc == curr_loc.properties['location'][1]:
            break
        curr_loc = curr_loc.properties['location'][1]

        all_locations.insert(0, curr_loc)

    for loc in all_locations:
        if "locked" in loc.attributes:
            del loc.attributes['locked']

            def undo(obs=loc):
                obs.attributes['locked'] = None
            world.undo_changes.append(undo)

        if "open" not in loc.attributes:
            actions.opens(loc, player)


def compute_say_steps(flattened_env_res, orig_env_res, player, knowledge_base):
    """
    Creates "player says <environment_response>" sentences from the
    environment's responses (orig_res)

    Furthermore, it separates them into two lists, depending on
    whether the reduced environment sentences (flattened_res)
    are seen/known by the player (steps_checked) or not (steps_not_checked).

    Parameters
    ----------
    flattened_env_res : list of lists
        The environment can return multiple valid responses. flattened_env_res is
        all the responses reduced.
    orig_env_res : list
        The environment's responses.
    player : Entity
        The player that produces the steps.
    knowledge_base : KnowledgeBase
        The knowledge base is used to check whether the agent has seen the environment responses in the past.

    Returns
    -------
    steps_checked : list
        The steps that the player is aware of.
    steps_not_checked : list
        The steps that the player is not aware of.

    """
    steps_checked = []
    steps_not_checked = []
    for idx, res in enumerate(flattened_env_res):
        orig_env_res[idx].speaker = player
        step = tsentences.say(player,
                              None,
                              'says',
                              orig_env_res[idx],
                              speaker=player)
        if knowledge_base.multi_check(res):
            steps_checked.append(step)
        else:
            steps_not_checked.append(step)

    return steps_checked, steps_not_checked


def add_can_not(can_not_action_res, steps):
    """
    Add the can_not_action_res to the list of the following sentences:

        player says: <inner_sentence>

    so that the resulting one is:

        player says: <can_not_action_res>. <inner_sentence>

    """
    for step in steps:
        inner_step = step.describers[0].get_arg('Arg-PPT')
        inner_reduced = shelpers.reduce_sentences([inner_step])
        new_step = tsentences.cont([can_not_action_res]+inner_reduced)
        step.describers[0].args['Arg-PPT'].value = new_step
        step.describers[0].args['Arg-PPT'].part = new_step
        step.parts[-1] = new_step


def extract_reasons(orig_env_res):
    """
    Extract the reasons why some action can not be done.
    The orig_env_res is a list of sentences having the following format:

        player can not <action> ... <reason_why>

    """
    flattened_res = []
    for res in orig_env_res:
        reduced = shelpers.reduce_sentences([res])[1:]
        flattened_res.append(reduced)
    return flattened_res


def find_last_command(dialogue):
    """
    Find the last user request from the list of dialogue utterances.
    """
    dialogue_utterances = dialogue.get_utterances()
    for idx in range(len(dialogue_utterances) - 1, - 1, - 1):
        utter = dialogue_utterances[idx]
        if desc_mappers.say(utter.describers) == utter:
            describer = utter.describers[0]
            sentence = describer.get_arg('Arg-PPT')
            if sentence.trusted_source and sentence == sentence.run_customizer('request_mapping'):
                return utter

    return None


def extract_inner_sent(say_sentence):
    """ Extract the request from the following sentence:

            player says: <request_sent>

        Make sure it comes from a trusted source.
    """

    if say_sentence is None:
        return None
    describer = say_sentence.describers[0]
    sentence = describer.get_arg('Arg-PPT')

    return sentence


def check_path(know_base, iloc, directions, dir_idx, tloc):
    """
    Checks whether the path from the intermediate location to the target location (tloc) is revealed to
    the agent.

    Parameters
    ----------
    know_base : KnowledgeBase
        The knowledge base is used to check whether the agent knows that
        the intermediate location has a direction that brings the agent one step closer to the target location.
    iloc : Entity
        The intermediate location.
    directions : list
        The list of directions that make up the path.
    dir_idx : int
        The current index in the directions list that shows how to transition from iloc to the next location.
    tloc : Entity
        The target location.

    Returns
    -------
    Sentence or None
        If the path is not revealed, a sentence is returned. Otherwise, None is returned.

    """
    if dir_idx >= len(directions):
        return None

    pkey = directions[dir_idx]
    pval = iloc.properties[pkey]
    is_seen = kn_checkers.property_check_alt(know_base, iloc, pkey, pval, None)

    if is_seen:
        further_check = check_path(know_base, pval, directions, dir_idx+1, tloc)
        if further_check is None:
            return None
        else:
            return tsentences.path_reveal(pval, tloc, 'not', 'revealed')

    return tsentences.path_reveal(iloc, tloc, 'not', 'revealed')


def check_loc(know_base, item, item_loc):
    """ Checks whether the agent has seen where the item is located.
        The checking is done recursively so in case the item's location is in a container or another place
        those locations are checked as well.

        Parameters
        ----------
        know_base : KnowledgeBase
            The knowledge base stores the information that the agent has seen.
        item : Entity
            The item that location is checked.
        item_loc : Entity
            The location of the item.

        Returns
        -------
        Entity or None
            The first non-revealed location on the way to the top location.
            Otherwise, None is returned.


    """

    is_seen = kn_checkers.property_check_alt(know_base, item, 'location', item_loc, None)
    if item_loc[1] == item and is_seen:
        return None

    if is_seen:
        further_check = check_loc(know_base, item_loc[1], item_loc[1].properties["location"])
        if further_check is None:
            return None
        else:
            return item_loc[1]
    return item


def path_revealed(dialogue, player, sloc, tloc, neg_res):
    """ Check whether the path from the source loc (sloc) to the
        target location (tloc) is revealed to the player.
        In case it's not, a negative response (neg_res) is returned.

        Parameters
        ----------
        dialogue : Dialogue
            The dialogue that the player is part of.
        player : Entity
            The agent whose policy calls this function.
        sloc : Entity
            The starting point.
        tloc : Entity
            The finishing point.
        neg_res : Sentence, optional
            A sentence indicating the action can not be completed. For example,
            John can not get the cat.

        Returns
        -------
        steps : list or None
            If the path is revealed, None is returned. Otherwise, returns a list comprising a single sentence saying
            why the path is not revealed.


    """
    combination = (sloc, tloc)
    know_base = dialogue.dia_generator.knowledge_base

    if combination in know_base.world.all_paths:
        dirs = know_base.world.all_paths[combination]
        step = check_path(know_base, sloc, dirs, 0, tloc)

    else:
        path_not_exist = True
        for direction in dialogue.dia_generator.world.directions:
            for place in dialogue.dia_generator.world.places:
                if kn_checkers.check_elem_exists_alt(know_base, place, direction, None) is None:
                    path_not_exist = False
                    break

            if path_not_exist is False:
                break
        if path_not_exist:
            step = tsentences.be((None, lc.Word('There')),
                                 'is',
                                 None,
                                 ['no', 'path', 'from', sloc, 'to', tloc]
                                 )
        else:
            step = tsentences.path_reveal(sloc, tloc, 'not', 'revealed')

    if step is not None:
        step = tsentences.cont([neg_res, step], player)
        step = tsentences.say(neg_res.speaker, None, 'says', step, speaker=player)
        steps = [step]
        return steps
    return None


def prec_action_item(dialogue,
                     player,
                     items,
                     neg_response=None):
    """
    For all items, it checks whether the player is aware of their locations.

    This function is used in the agents' policies.

    Parameters
    ----------
    dialogue : Dialogue
        The dialogue is needed to create the goal which might be part of the dialogue.
    player : Entity
        The agent whose policy calls this function.
    items : list
        The items whose locations are checked.
    neg_response : Sentence, optional
        A sentence indicating the action can not be completed. For example,
        John can not get the cat.

    Returns
    -------
    steps : list or None
        The list of valid responses. If all items' locations are revealed, None is returned.
    goal : Goal or None
        If all items' locations are revealed, None is returned. Otherwise,
        the agent's goal is to output one sentence saying which
        item's location is not revealed.


    """
    know_base = dialogue.dia_generator.knowledge_base
    steps = []

    for item in items:
        item_loc_not_rev = check_loc(know_base, item, item.properties["location"])
        if item_loc_not_rev is not None:
            step = tsentences.be([item_loc_not_rev, "'s", 'location'], 'is', 'not', 'revealed')
            if step not in steps:
                if neg_response is not None:
                    step = tsentences.cont([neg_response, step], speaker=player)
                steps.append(tsentences.say(player, None, 'says', step, speaker=player))
    goal = tgoals.Goal(tgoals.multiple_correct,
                       dialogue,
                       player,
                       steps,
                       len(dialogue.get_utterances()) - 1
                       )

    if len(steps) == 0:
        steps, goal = None, None
    return steps, goal


def reduce_and_check_say(steps, target_sent):
    """ Reduces the sentences in the steps (check Sentence.reduce) and checks whether at least one of the sentences
        is in the format:
            <player> says: neg_sent

    Parameters
    ----------
    steps : list
        A list of sentences.
    target_sent : Sentence
        The inner sentence that is checked if it exists.

    Returns
    -------
    found_flag : bool
        True if the neg_sent is found in one of the sentences. Otherwise, False.
    """
    reduced_steps = shelpers.reduce_sentences(steps)
    found_flag = False

    for rstep in reduced_steps:
        if len(rstep.describers) == 1:

            if rstep.describers[0].get_arg("Rel") == "says":
                inner_sent = rstep.describers[0].get_arg("Arg-PPT")
                if inner_sent == target_sent:
                    found_flag = True
                    break
    return found_flag

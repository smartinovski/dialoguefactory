#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the policies that the agent uses respond to the dialogue.
"""

import copy
import random

from . import policies_helpers as phelpers
from ..language import helpers as lhelpers
from ..environment import helpers as em_helpers

from . import base_policies as bpolicies
from . import goals as tgoals
from ..state import kn_checkers

from ..language import queries
from ..language import sentences as tsentences
from ..language import describers as tdescribers

from ..language import components as lc
from ..environment import entities as em
from ..environment import actions


class GoLocationPolicy(bpolicies.ActionPolicy):
    """
    This class represents the agent's policy when the user asks the agent to go to an object's location.

    Attributes
    ----------
    go_dir_policy : GoDirectionPolicy
        This policy is used to compute the directions to the object's location.

    """
    def __init__(self, go_dir_policy, player=None, dialogue=None):
        super().__init__(player, None, dialogue)
        self.go_dir_policy = go_dir_policy

    def parse(self, last_user_command):
        """ Parses the user request that comes from the policy user_policies.GoLocPolicy
            in order to extract the necessary parameters to call self.task.
            Later it calls self.task with the extracted parameters to compute the agent's valid utterances and the goal.

            Parameters
            ----------
            last_user_command : Sentence
                One of the following requests (queries.go):

                    - <agent>, go to (a) <object>
                    - then <agent>, go to (a) <object>

                The second sentence is used in the AndPolicy.

            Returns
            -------
            steps : list
                The valid utterances.
            goal : Goal
                The goal of the agent self.player.
        """
        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "go":
            return None, None

        end_point_arg = describer.get_arg('Arg-GOL', _type=0)
        end_point = end_point_arg.value if end_point_arg else None
        go_to_location_query = queries.go(describer.get_arg("AM-TMP"),
                                          self.player,
                                          None, 'go', None, None, end_point)

        steps, goal = None, None
        if last_user_command == go_to_location_query:

            if (len(end_point) == 3 and isinstance(end_point[-1], em.BaseEntity)
                    and end_point[-2] == 'a'):
                can_not_go_res = tsentences.go(self.player, 'can', 'not', 'go',
                                               None, None, ['to', 'a', end_point[-1]], self.player)
                neg_res_func = lambda item, player=self.player: tsentences.go(player, 'can', 'not', 'go',
                                                                              None, None, ['to', item], player)
                steps, goal = self.one_task(end_point[-1],
                                            can_not_go_res,
                                            neg_res_func,
                                            last_user_command)
            elif len(end_point) == 2 and isinstance(end_point[1], em.Entity) and end_point[0] == 'to':
                steps, goal = self.task(getattr(self.dialogue.dia_generator.world,
                                                end_point[-1].get_property('var_name'),
                                                None))

        return steps, goal

    def task(self, item, prepos_location=None, preconditions=True):
        """
        Computes the steps that are necessary for self.player to
        successfully go to the location of the item. Furthermore, it
        computes the goal of self.player.


        Parameters
        ----------
        item : Entity
            The item's top location is used as the target location for the agent.
        prepos_location : list, optional
            If the prepos location is not None it is used as the target location for the agent.
            This is done in requests like get the apple in the kitchen and even though the location
            of the apple is not revealed, the kitchen's location is known.
        preconditions : bool, optional
            If True it checks whether all necessary entities for accomplishing the task have
            their location revealed.

        Returns
        -------
        steps : list
            The list of possible utterances for the agent self.player.
        goal : Goal
            The goal of the agent self.player.

        """
        can_not_go_res = tsentences.go(self.player, 'can', 'not', 'go',
                                       None, None, ['to',  item], self.player)

        prec_steps, prec_goal = None, None
        if preconditions:
            prec_items = [self.player, item]
            if prepos_location is not None:
                prec_items.append(prepos_location[1])

            prec_steps, prec_goal = phelpers.prec_action_item(self.dialogue, self.player,
                                                              prec_items, can_not_go_res)

        if prepos_location is None:
            target_loc = item.top_location()
        else:
            target_loc = prepos_location[1].top_location()

        source_loc = self.player.properties['location'][1]
        if (source_loc, target_loc) in self.dialogue.dia_generator.world.all_paths:
            dirs = self.dialogue.dia_generator.world.all_paths[(source_loc, target_loc)]
        else:
            dirs = None
        if dirs is not None and len(dirs) == 0:
            step = tsentences.be([self.player, "'s", 'location'], 'is', None, ['in', target_loc])
            say_step = tsentences.cont([can_not_go_res, step])
            say_step = tsentences.say(self.player, None, "says", say_step, speaker=self.player)

            if prec_steps is not None and self.dialogue.dia_generator.knowledge_base.check(step) is not True:
                steps = prec_steps
            else:
                steps = [say_step]
            goal = tgoals.Goal(tgoals.multiple_correct,
                               self.dialogue,
                               self.player,
                               steps,
                               len(self.dialogue.get_utterances()) - 1
                               )
        else:
            pr_steps = phelpers.path_revealed(self.dialogue, self.player,
                                              source_loc, target_loc, can_not_go_res)

            neg_responses = []
            steps_checked, steps_unchecked = [], []

            if dirs is not None and len(dirs) > 0:
                state = self.dialogue.dia_generator.world.save_state()
                for direction in dirs:
                    player_loc = self.player.properties['location'][1]
                    obs = None
                    list_undos = []
                    if (direction, 'obstacle') in player_loc.properties:
                        obs = player_loc.properties[(direction, 'obstacle')]
                        check_obstacle = kn_checkers.property_check_alt(self.dialogue.dia_generator.knowledge_base,
                                                                        player_loc,
                                                                        (direction, "obstacle"),
                                                                        obs,
                                                                        None
                                                                        )
                        x_is_door = kn_checkers.property_check_alt(self.dialogue.dia_generator.knowledge_base,
                                                                   obs,
                                                                   "type",
                                                                   "door",
                                                                   None)

                        if 'type' in obs.properties and obs.properties['type'] == 'door' and 'locked' in obs.attributes:
                            res = actions.go(self.player, direction)
                            neg_responses += res
                            del obs.attributes['locked']

                            def undo(obstacle=obs):
                                obstacle.attributes['locked'] = None

                            list_undos.append(undo)

                        if 'type' in obs.properties and obs.properties['type'] == 'door' and 'open' not in obs.attributes:
                            # this is only for doors
                            # if there is a door (indicated with the if above) and the agent does not know
                            # if its open, it should just go through.
                            if check_obstacle and x_is_door is not True:
                                res = actions.go(self.player, direction)
                                neg_responses += res
                            obs.attributes["open"] = None

                            def undo(obstacle=obs):
                                del obstacle.attributes['open']

                            list_undos.append(undo)

                    # here it might be the case that player is not at from_loc
                    # in case you use the optional arg from_loc in actions.go.
                    res = actions.go(self.player, direction)
                    # in case it does not progress further.
                    reduced_res = lhelpers.reduce_sentences([res[0]])

                    for und in reversed(list_undos):
                        und()

                    if em_helpers.check_can_not(reduced_res, "go"):
                        break

                if len(neg_responses) > 0:
                    reasons = phelpers.extract_reasons(neg_responses)

                    steps_checked, steps_unchecked = phelpers.compute_say_steps(reasons,
                                                                                neg_responses,
                                                                                self.player,
                                                                                self.dialogue.dia_generator.knowledge_base)
                if em_helpers.check_can_not(res, "go"):
                    reasons = phelpers.extract_reasons(res)

                    sc, su = phelpers.compute_say_steps(reasons,
                                                        res,
                                                        self.player,
                                                        self.dialogue.dia_generator.knowledge_base)
                    steps_checked += sc
                    steps_unchecked += su
                self.dialogue.dia_generator.world.recover_state(state)

            if prec_steps is None and pr_steps is None:
                if len(steps_checked) > 0:
                    steps = []
                    steps += steps_checked
                    phelpers.add_can_not(can_not_go_res, steps)

                    goal = tgoals.Goal(tgoals.multiple_correct,
                                       self.dialogue,
                                       self.player,
                                       steps_checked+steps_unchecked,
                                       len(self.dialogue.get_utterances()) - 1)

                else:
                    steps, _ = self.go_dir_policy.task(dirs[0])
                    if len(steps_unchecked) == 0:
                        goal = tgoals.Goal(tgoals.go_to_loc_goal, self.dialogue, self.player,
                                           target_loc, len(self.dialogue.get_utterances()) - 1)
                    else:
                        goal = tgoals.Goal(tgoals.multiple_correct,
                                           self.dialogue,
                                           self.player,
                                           steps_unchecked,
                                           len(self.dialogue.get_utterances()) - 1
                                           )
            else:
                if prec_steps is not None:
                    steps = prec_steps
                else:
                    steps = pr_steps
                goal = tgoals.Goal(tgoals.multiple_correct,
                                   self.dialogue,
                                   self.player,
                                   steps,
                                   len(self.dialogue.get_utterances()) - 1
                                   )
        return steps, goal

    def replace_dialogue(self, new_dialogue):
        """ Replaces the dialogue with a new dialogue. """
        super().replace_dialogue(new_dialogue)
        self.go_dir_policy.replace_dialogue(new_dialogue)

    def save_state(self):
        """ Saves the policy state that changes with time. """
        parent_state = super().save_state()
        go_dir_state = self.go_dir_policy.save_state()

        return parent_state, go_dir_state

    def recover_state(self, state):
        """ Recovers the policy state that changes with time. """
        parent_state, go_dir_state = state
        super().recover_state(parent_state)
        self.go_dir_policy.recover_state(go_dir_state)


class GoDirectionPolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user asks the agent to go in a direction.

        Attributes
        ----------
        initial_loc : Entity
            This is the location where the agent should try going in a specific direction.
    """
    def __init__(self, player=None, dialogue=None):
        super().__init__(player, None, dialogue)
        self.initial_loc = None

    def parse(self, last_user_command):
        """
        Parses the user request outputted from the policy user_policies.GoDirectionPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.go):

                - <agent>, go <direction>
                - then <agent>, go <direction>

            The second sentence is encountered in the user_policies.AndPolicy, and it is parsed in the agent_policies.AndPolicy

        Returns
        -------
        steps : list
            The valid utterances.
        goal : Goal
            The goal of the agent self.player.

        """
        describer = last_user_command.describers[0]
        direction = describer.get_arg('AM-DIR')
        if describer.get_arg("Rel", _type=0).infinitive != "go":
            return None, None

        go_to_direction_query = queries.go(describer.get_arg("AM-TMP"),
                                           self.player,  None, 'go', direction)
        steps, goal = None, None

        if last_user_command == go_to_direction_query:
            steps, goal = self.task(direction, last_user_command)

        return steps, goal

    def task(self, direction, last_user_command=None):
        """
        Computes the steps and the goal necessary for self.player
        successfully going in a specific direction.

        Parameters
        ----------
        direction : str
            The direction in which self.player is headed.
        last_user_command : Sentence
            The user's request is asking self.player to go <direction>.
            Refer to self.parse for the format of the sentence.
            If there is a new request, the initial location of the self.player is changed.

        """

        if last_user_command is not None:
            if self.prev_user_command is None or id(self.prev_user_command) != id(last_user_command):
                self.prev_user_command = last_user_command
                self.initial_loc = self.player.properties['location'][1]
            initial_loc = self.initial_loc
        else:
            initial_loc = self.player.properties['location'][1]

        tries_go_step = tsentences.tries(self.player, None, None, "tries",
                                         tsentences.go(rel='going',
                                                       direction=direction,
                                                       speaker=self.player),
                                         self.player)

        if direction in initial_loc.properties and initial_loc.properties[direction] == self.player.properties['location'][1]:
            player_moved_res = tsentences.go(self.player,
                                             None,
                                             None,
                                             'went',
                                             direction,
                                             ['from', initial_loc])

            steps = [tsentences.say(self.player, None, "says",
                                    player_moved_res, speaker=self.player)]
            goal_multiple = tgoals.Goal(tgoals.multiple_correct,
                                        self.dialogue,
                                        self.player,
                                        steps,
                                        len(self.dialogue.get_utterances()) - 1
                                        )
            return steps, goal_multiple

        state = self.dialogue.dia_generator.world.save_state()
        player_w = getattr(self.dialogue.dia_generator.world, self.player.properties['var_name'], None)
        orig_res = actions.go(player_w, direction, initial_loc)
        self.dialogue.dia_generator.world.recover_state(state)

        go_step = tsentences.go(self.player,
                                None,
                                None,
                                'goes',
                                direction,
                                ['from', initial_loc])

        steps = None
        goal = None

        if go_step != lhelpers.reduce_sentences([orig_res[0]])[0]:
            flattened_res = phelpers.extract_reasons(orig_res)
            if (direction, "obstacle") in initial_loc.properties:
                door = initial_loc.properties[(direction, "obstacle")]
                player_loc = tsentences.be([self.player, "'s", "location"], "is", None, ['in', initial_loc])
                obstacle_present = tsentences.be([initial_loc, "'s", direction, "obstacle"], 'is', None, door)
                door_closed = tsentences.be(door, 'is', 'not', 'open')
                door_not_locked = tsentences.be(door, 'is', None, 'locked')
                x_is_door = tsentences.be([door, "'s", "type"], 'is', None, 'door')

            if ((direction, "obstacle") in initial_loc.properties and
                self.dialogue.dia_generator.knowledge_base.multi_check([player_loc, obstacle_present, door_closed, x_is_door])
                    and self.dialogue.dia_generator.knowledge_base.check(door_not_locked) is not True):
                open_step = tsentences.tries(self.player, None, None, "tries",
                                             tsentences.opens(rel="opening",
                                                              thing_opened=door,
                                                              speaker=self.player),
                                             self.player)

                steps = [open_step]

            else:
                steps_checked, steps_not_checked = phelpers.compute_say_steps(flattened_res,
                                                                              orig_res,
                                                                              self.player,
                                                                              self.dialogue.dia_generator.knowledge_base)

                goal_multiple = tgoals.Goal(tgoals.multiple_correct,
                                            self.dialogue,
                                            self.player,
                                            steps_checked+steps_not_checked,
                                            len(self.dialogue.get_utterances()) - 1
                                            )

                if len(steps_checked) > 0:
                    player_loc = tsentences.be(([self.player, "'s", "location"], None),
                                               ("is", None),
                                               (None, None),
                                               (['in', initial_loc], None))
                    player_loc_checked = self.dialogue.dia_generator.knowledge_base.check(player_loc)
                    steps = []
                    # If the sentence contains the player's location, but the location is not revealed.
                    # this is just for the steps, the goal stays the same.
                    for step in steps_checked:
                        inner_step = step.describers[0].get_arg("Arg-PPT")
                        if player_loc in inner_step.meta_sent:
                            if player_loc_checked:
                                steps.append(step)
                        else:
                            steps.append(step)
                    if len(steps) > 0:
                        steps = steps_checked
                        goal = goal_multiple
                    else:
                        steps = None
                if steps is None:
                    steps = [tries_go_step]
                    goal = goal_multiple

        if steps is None:
            steps = [tries_go_step]
        if goal is None:
            goal = tgoals.Goal(tgoals.sent_in_reduced, self.dialogue, go_step, None, len(self.dialogue.get_utterances())-1)

        return steps, goal


class LookItemPolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user requests the agent to look at an item. """

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.LookItemPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.look):

                - <agent>, look <preposition> (a) <entity> <entity_location>
                - then <agent>, look <preposition> (a) <entity> <entity_location>

            where <preposition> is world.location_positions and <entity_location> is the location of the <entity>.
            The <entity_location> is the entity's location, and it is a list of two values:
            the first is a preposition in/on/under and the second value is an Entity.
            The second type of user request is encountered in the user_policies.AndPolicy and
            it is parsed in the agent_policies.AndPolicy


        """

        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "look":
            return None, None

        thing_looked_arg = describer.get_arg('Arg-GOL', _type=0)
        thing_looked = thing_looked_arg.value if thing_looked_arg else None
        location_arg = describer.get_arg('AM-LOC', _type=0)
        location = location_arg.value if location_arg else None
        look_query = queries.look(describer.get_arg("AM-TMP"),
                                  self.player, None, 'look', thing_looked, location)

        steps, goal = None, None
        if last_user_command == look_query:
            prepos = None
            if isinstance(thing_looked, list) and isinstance(thing_looked[-1], em.BaseEntity):
                thing_looked_entity = thing_looked[-1]
                if location is not None:
                    location = [location[0], getattr(self.dialogue.dia_generator.world, location[1].get_property("var_name"))]
                if (len(thing_looked) == 3
                        and isinstance(thing_looked[-1], em.BaseEntity)
                        and thing_looked[-2] == 'a'):
                    prepos = thing_looked[-3]
                    neg_res = tsentences.look(self.player,
                                              'can',
                                              'not',
                                              'look',
                                              [prepos, 'a', thing_looked_entity],
                                              None,
                                              self.player)

                    def neg_res_func(item, prepos=prepos, player=self.player):
                        res = tsentences.look(player,
                                              'can',
                                              'not',
                                              'look',
                                              [prepos, item],
                                              None,
                                              player)
                        return res

                    steps, goal = self.one_task(thing_looked_entity, neg_res, neg_res_func, last_user_command,
                                                thing_looked_prepos=prepos,
                                                prepos_location=location)
                elif (len(thing_looked) == 2
                      and isinstance(thing_looked[-1], em.Entity)
                      and thing_looked[-2] in self.dialogue.dia_generator.world.location_positions):
                    thing_looked_entity = getattr(self.dialogue.dia_generator.world, thing_looked_entity.get_property("var_name"))
                    prepos = thing_looked[-2]
                    steps, goal = self.task(thing_looked_entity, prepos, location)

        return steps, goal

    def task(self, item, thing_looked_prepos, prepos_location=None):
        """
        Computes the steps and the goal necessary for self.player
        successfully looking in/on/under an item.

        Parameters
        ----------
        item : Entity
            The entity that player looks at.
        thing_looked_prepos : str
            The preposition where the player looks. For example, this can be
            in/on/under. See world.location_positions
        prepos_location : list, optional
            The location of the item. The location does not necessarily have to be the top location.
            (read more env_main.top_loc)

        """
        can_not_look_res = tsentences.look(self.player,
                                           'can',
                                           'not',
                                           'look',
                                           [thing_looked_prepos, item],
                                           speaker=self.player)

        if prepos_location is not None:
            target_location = prepos_location
        else:
            target_location = copy.copy(item.properties['location'])

        action_params = (item, self.player, thing_looked_prepos, target_location)
        look_res = tsentences.look(self.player,
                                   None,
                                   None,
                                   'looks',
                                   [thing_looked_prepos, item]
                                   )

        look_step = tsentences.tries(self.player, None, None, "tries",
                                     tsentences.look(rel='looking',
                                                     thing_looked=[thing_looked_prepos,
                                                                   item],
                                                     item_location=target_location,
                                                     speaker=self.player),
                                     self.player)
        steps, goal = phelpers.compute_policy_steps(self, item, can_not_look_res, target_location[1], prepos_location,  actions.look, action_params, look_res, look_step)

        return steps, goal


class DropItemPolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user asks the agent to drop an entity at a specific location. """

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.DropPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.drop):

                - <agent>, drop (a) <entity> <target_location>
                - then <agent>, drop (a) <entity> <target_location>

            where the <target_location> is a list of two values: the first is a preposition in/on/under and
            the second value is an Entity.
            The second sentence form is used in the user_policies.AndPolicy.

        """
        dropper = self.player
        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "drop":
            return None, None

        thing_dropped_arg = describer.get_arg('Arg-PPT', _type=0)
        thing_dropped = thing_dropped_arg.value if thing_dropped_arg else None
        location_arg = describer.get_arg('Arg-GOL', _type=0)
        location = location_arg.value if location_arg else None
        drop_query = queries.drop(describer.get_arg("AM-TMP"), dropper, None, 'drop', thing_dropped, location)
        steps, goal = None, None
        if last_user_command == drop_query:
            if location is not None:
                location = [location[0],
                            getattr(self.dialogue.dia_generator.world, location[1].get_property("var_name"))]
            if (isinstance(thing_dropped, list)
                    and isinstance(thing_dropped[-1], em.BaseEntity) and thing_dropped[-2] == 'a'):

                thing_dropped_entity = thing_dropped[-1]
                neg_res = tsentences.drop(self.player, 'can', 'not', 'drop',
                                          ['a', thing_dropped_entity],
                                          location, self.player)

                def neg_res_func(item, player=self.player):
                    res = tsentences.drop(player, 'can', 'not', 'drop',
                                          item,
                                          speaker=self.player)
                    return res

                steps, goal = self.one_task(thing_dropped_entity,
                                            neg_res,
                                            neg_res_func,
                                            last_user_command,
                                            prepos_location=location)
            elif isinstance(thing_dropped, em.Entity):
                thing_dropped_entity = getattr(self.dialogue.dia_generator.world, thing_dropped.get_property("var_name"))
                steps, goal = self.task(thing_dropped_entity, location)
        return steps, goal

    def task(self, item, prepos_location=None):
        """
        Computes the steps and the goal necessary for self.player
        successfully dropping the item at the target location.

        Parameters
        ----------
        item : Entity
            The entity to be dropped by self.player at the location.
        prepos_location : list, optional
            If provided, prepos_location is the target location where the item should be dropped.
            Otherwise, the target location will be the player's location.
            The prepos_location is a list of two values: the first is a preposition in/on/under, and the
            second value is an Entity.

        """
        can_not_drop_res = tsentences.drop(self.player,
                                           'can', 'not', 'drop',
                                           item, speaker=self.player)

        if prepos_location is None:
            target_location = copy.copy(self.player.properties["location"])
        else:
            target_location = prepos_location

        action_params = (item, self.player, target_location[1], target_location[0])

        drop_step = tsentences.tries(self.player, None, None, "tries",
                                     tsentences.drop(rel='dropping',
                                                     entity=item,
                                                     prepos_location=target_location,
                                                     speaker=self.player),
                                     speaker=self.player)
        drop_res = tsentences.drop(self.player, None, None, 'drops', item, target_location)
        steps, goal = phelpers.compute_policy_steps(self, item, can_not_drop_res, target_location[1], prepos_location,
                                                    actions.drop, action_params, drop_res, drop_step)

        return steps, goal


class OpenCloseItemPolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user asks the agent to open or close an entity """

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.OpenItemPolicy or user_policies.CloseItemPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.open or queries.close):

                - <agent>, <action> (a) <entity> <entity_location>
                - then <agent>, <action> (a) <entity> <entity_location>

            where the <entity_location> is the entity's location, and it is a list of two values:
            the first is a preposition in/on/under, and the second value is an Entity.
            The <action> can be either open or close.
            The second sentence is encountered in the user_policies.AndPolicy.

        """

        describer = last_user_command.describers[0]
        rel = describer.get_arg("Rel", _type=0).infinitive
        if rel not in ["open", "close"]:
            return None, None
        entity_arg = describer.get_arg('Arg-PPT', _type=0)
        entity = entity_arg.value if entity_arg else None
        location_arg = describer.get_arg('AM-LOC', _type=0)
        location = location_arg.value if location_arg else None

        if rel == "open":
            query_func = queries.opens
            action = "open"
        else:
            query_func = queries.close
            action = "close"
        query_res = query_func(describer.get_arg("AM-TMP"), self.player, None, rel, entity, location)

        steps, goal = None, None
        if last_user_command == query_res:
            if location is not None:
                location = [location[0], getattr(self.dialogue.dia_generator.world, location[1].get_property("var_name"))]

            if isinstance(entity, list) and isinstance(entity[-1], em.BaseEntity) and entity[-2] == 'a':
                if action == "open":
                    can_not_res_func = tsentences.opens
                else:
                    can_not_res_func = tsentences.close

                can_not_res = can_not_res_func(self.player,
                                               'can',
                                               'not',
                                               action,
                                               ['a', entity[-1]],
                                               location,
                                               self.player)

                def neg_res_func(item, action=action, player=self.player):
                    res = can_not_res_func(player,
                                           'can',
                                           'not',
                                           action,
                                           item,
                                           None,
                                           player)
                    return res

                steps, goal = self.one_task(entity[-1],
                                            can_not_res,
                                            neg_res_func,
                                            last_user_command,
                                            prepos_location=location,
                                            action=action)

            elif isinstance(entity, em.Entity):
                entity = getattr(self.dialogue.dia_generator.world, entity.get_property("var_name"))
                steps, goal = self.task(entity, action, location)
        return steps, goal

    def task(self, item,  action, prepos_location=None):
        """
        Computes the steps and the goal necessary for self.player
        successfully opening or closing the item at the target location.

        Parameters
        ----------
        item : Entity
            The item that is closed or opened.
        action : str
            The action open or close that is acted upon the item.
        prepos_location : list
            The location of the item. The location does not necessarily have to be the top location.

        """
        steps, goal = None, None
        if action in ["open", "close"]:

            if action == "open":
                res_func = tsentences.opens
                action_func = actions.opens
            else:
                res_func = tsentences.close
                action_func = actions.closes

            can_not_res = res_func(self.player, 'can', 'not',
                                   action, item, speaker=self.player)

            if prepos_location is not None:
                target_location = prepos_location
            else:
                target_location = copy.copy(item.properties['location'])
            action_step = res_func(None, None, None,
                                   lc.retrieve_inflection(action, 'VBG'), item,
                                   target_location, speaker=self.player)
            action_step = tsentences.tries(self.player, None, None,
                                           "tries", action_step, speaker=self.player)

            action_third_person = lc.retrieve_inflection(action, 'VBZ')
            action_res = res_func(self.player, None, None,
                                  action_third_person, item,
                                  speaker=self.player)

            action_params = (item, self.player, target_location[1], target_location[0])
            steps, goal = phelpers.compute_policy_steps(self, item, can_not_res, target_location[1], prepos_location,
                                                        action_func, action_params, action_res, action_step)

        return steps, goal


class GetItemPolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user asks the agent to get an entity """

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.GetItemPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.open or queries.close):

                - <agent>, get (a) <entity> <entity_location>
                - then <agent>, get (a) <entity> <entity_location>

            where the <entity_location> is the entity's location, and it is a list of two values:
            the first is a preposition in/on/under, and the second value is an Entity.
            The second sentence is encountered in the user_policies.AndPolicy.

        """
        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "get":
            return None, None
        getter = self.player
        thing_got_arg = describer.get_arg('Arg-PPT', _type=0)
        thing_got = thing_got_arg.value if thing_got_arg else None
        location_arg = describer.get_arg('Arg-DIR', _type=0)
        location = location_arg.value if location_arg else None
        get_query = queries.get(describer.get_arg("AM-TMP"), getter,  None, 'get', thing_got, location)
        steps, goal = None, None
        if last_user_command == get_query:

            if location is not None:
                location = [location[0], getattr(self.dialogue.dia_generator.world, location[1].get_property("var_name"))]

            if (isinstance(thing_got, list) and isinstance(thing_got[-1], em.BaseEntity)
                    and thing_got[-2] == 'a'):

                thing_got_entity = thing_got[-1]

                can_not_get_res = tsentences.get(self.player,
                                                 'can',
                                                 'not',
                                                 'get',
                                                 ['a', thing_got_entity],
                                                 location,
                                                 self.player)

                def neg_res_func(item, player=self.player):
                    res = tsentences.get(player,
                                         'can',
                                         'not',
                                         'get',
                                         item,
                                         speaker=player)
                    return res

                steps, goal = self.one_task(thing_got_entity,
                                            can_not_get_res,
                                            neg_res_func,
                                            last_user_command,
                                            prepos_location=location)
            elif isinstance(thing_got, em.Entity):
                thing_got_entity = getattr(self.dialogue.dia_generator.world, thing_got.get_property('var_name'))
                steps, goal = self.task(thing_got_entity, location)
        return steps, goal

    def task(self, item, prepos_location=None):
        """

        Computes the steps and the goal necessary for self.player
        successfully getting the item at the target location.

        Parameters
        ----------
        item : Entity
            The entity to be taken by the agent.
        prepos_location : list
            The location of the item. The location does not necessarily have to be the top location. (read more entity.top loc)
            The entity's location is a list of two values:
            the first is a preposition in/on/under, and the second value is an Entity.

        """
        can_not_get_res = tsentences.get(self.player,
                                         'can',
                                         'not',
                                         'get',
                                         item,
                                         speaker=self.player)

        if prepos_location is None:
            target_location = copy.copy(item.properties["location"])
        else:
            target_location = prepos_location

        get_step = tsentences.tries(self.player,
                                    None,
                                    None,
                                    "tries",
                                    tsentences.get(rel='getting',
                                                   entity=item,
                                                   prepos_location=target_location,
                                                   speaker=self.player),
                                    self.player)
        get_res = tsentences.get(self.player, None, None, 'gets', item)
        action_params = (item, self.player, target_location[1], target_location[0])

        steps, goal = phelpers.compute_policy_steps(self, item, can_not_get_res, target_location[1],
                                                    prepos_location, actions.get, action_params, get_res, get_step)

        return steps, goal


class IsItemPolicy(bpolicies.IsItem):
    """ The agent's policy when the user asks the agent whether an item has
        a specific property pair (key, value).

    """

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.IsItemPropertyPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            A sentence representing a request (queries.be). The sentence should be in the format:
                <agent>, Is (a) <item> 's <property_key> <property_val>?
                or
                then <agent>, Is (a) <item> 's <property_key> <property_val>?
        """

        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "Be":
            return None, None
        item_prop_key = describer.get_arg('Arg-PPT')

        steps, goal = None, None

        property_val = describer.get_arg('Arg-PRD')

        matching_sent = lc.Sentence()
        matching_desc = tdescribers.be((item_prop_key, None),
                                       ('Is', None),
                                       (None, None),
                                       (property_val, None)
                                       )
        matching_desc.args['AM-DIS'] = lc.Arg(self.player)
        am_tmp = describer.get_arg('AM-TMP', _type=0)
        if am_tmp is not None:
            matching_desc.args['AM-TMP'] = am_tmp

        matching_sent.describers += [matching_desc]
        if matching_sent == last_user_command:

            if isinstance(item_prop_key, list):
                if (len(item_prop_key) >= 3 and item_prop_key[1] == "'s"
                        and isinstance(item_prop_key[0], em.Entity)):
                    item = item_prop_key[0]
                    property_key = item_prop_key[2:]
                    item = getattr(self.dialogue.dia_generator.world, item.get_property('var_name'))
                    steps, goal = self.task(item, property_key, property_val)
                elif (len(item_prop_key) >= 4 and
                      item_prop_key[0] == "a" and
                      isinstance(item_prop_key[1], em.BaseEntity) and
                      item_prop_key[2] == "'s"
                      ):
                    item = item_prop_key[1]
                    property_key = item_prop_key[3:]

                    def neg_res_func(item, player=self.player, property_key=property_key, property_val=property_val):
                        statement = lc.Sentence(speaker=player)
                        desc = tdescribers.be(([item, "'s"]+property_key, None),
                                              ('is', None),
                                              (None, None),
                                              (property_val, None))
                        statement.describers += [desc]
                        dont_know_res = tsentences.know(player, "not", "know", statement, speaker=player)
                        return dont_know_res

                    prop_val_part = lhelpers.convert_obj_to_part(property_val)
                    prop_key_part = lhelpers.convert_obj_to_part(property_key)
                    neg_response = lc.Sentence([lc.Word('whether'),
                                                lc.Word('a'),
                                                item.describe(),
                                                lc.Word("'s")] +
                                                prop_key_part +
                                                [lc.Word('is'), prop_val_part],
                                                speaker=self.player)
                    desc = tdescribers.be((['a', item, "'s"]+property_key, neg_response.parts[1:4+len(property_key)]),
                                          ('is', neg_response.parts[4+len(property_key)]),
                                          (None, None),
                                          (property_val, prop_val_part))
                    neg_response.describers += [desc]
                    dont_know_res = tsentences.know(self.player, "not", "know", neg_response, speaker=self.player)

                    is_not_res = tsentences.be((None, lc.Word("There")), "is", "not",
                                               ['a', item, "with"]+property_key +
                                               (list(property_val) if isinstance(property_val, (set, tuple, list)) else [property_val]), speaker=self.player)
                    steps, goal = self.one_task(item, is_not_res, dont_know_res, neg_res_func, last_user_command,
                                                property_key=property_key,
                                                property_val=property_val)

        return steps, goal

    def task(self, item, property_key, property_val):
        """
        Computes the steps and the goal necessary for self.player
        successfully answering the question: Is <item> <property_key> <property_val>?

        Parameters
        ----------
        item : Entity
            The item whose property existence (property key, property value) is checked.
        property_key : list
            The property key. For example, ['color'] or ['north', 'obstacle']
        property_val : any
            The property value that is tested. For example, 'red' or world.guest_room

        """

        property_key_list = property_key
        if len(property_key) == 1:
            property_key = property_key[0]
        else:
            property_key = tuple(property_key)
        knob_state = self.dialogue.dia_generator.knowledge_base
        is_seen_pos = kn_checkers.property_check_alt(knob_state,
                                                     item,
                                                     property_key,
                                                     property_val,
                                                     None)

        property_val_part = lhelpers.convert_obj_to_part(property_val)

        prop_sent = tsentences.be(property_val,
                                  "is",
                                  "not",
                                  property_key_list if isinstance(property_key, tuple) else property_key,
                                  speaker=self.player)
        if knob_state.check(prop_sent):
            say_sent = tsentences.say(self.player, None, "says", prop_sent, speaker=self.player)
            steps = [say_sent]

            goal = tgoals.Goal(tgoals.multiple_correct, self.dialogue, self.player,
                               steps, len(self.dialogue.get_utterances()) - 1)
        elif is_seen_pos is None:
            property_key_part = lhelpers.convert_obj_to_part(property_key_list)

            statement = lc.Sentence([lc.Word('whether'),
                                     item.describe(),
                                     lc.Word("'s")]+property_key_part+[lc.Word('is'), property_val_part],
                                    speaker=self.player)
            desc = tdescribers.be(([item, "'s"]+property_key_list, [statement.parts[1], lc.Word("'s"),
                                  statement.parts[2:2+len(property_key_list)]]),
                                  ('is', statement.parts[2+len(property_key_list)]),
                                  (None, None),
                                  (property_val, statement.parts[4]))
            statement.describers += [desc]
            dont_know_res = tsentences.know(self.player, "not", "know", statement, speaker=self.player)
            say_sent = tsentences.say(self.player, None, "says", dont_know_res, speaker=self.player)

            multiple_steps = [say_sent]

            if self.dialogue.dia_generator.world.check_val_is_key(property_key, property_val):
                prop_val_not = tsentences.say(self.player, None, "says", prop_sent, speaker=self.player)
                multiple_steps.append(prop_val_not)
            if property_key in item.properties:
                if item.properties[property_key] == property_val:
                    neg = None
                else:
                    neg = "not"

                sent = tsentences.be([item, "'s"]+property_key_list, "is", neg,
                                 (property_val, property_val_part), speaker=self.player)

                say_sent = tsentences.say(self.player, None, "says", sent, speaker=self.player)
                multiple_steps.append(say_sent)
            goal = tgoals.Goal(tgoals.multiple_correct,
                               self.dialogue,
                               self.player,
                               multiple_steps,
                               len(self.dialogue.get_utterances()) - 1
                               )
            steps = multiple_steps

        else:
            if is_seen_pos:
                neg = None
            else:
                neg = "not"
            sent = tsentences.be([item, "'s"]+property_key_list, "is", neg,
                                 (property_val, property_val_part), speaker=self.player)
            say_sent = tsentences.say(self.player, None, "says", sent, speaker=self.player)
            steps = [say_sent]
            goal = tgoals.Goal(tgoals.multiple_correct, self.dialogue, self.player,
                               steps, len(self.dialogue.get_utterances()) - 1)
        return steps, goal


class IsItemAttributePolicy(bpolicies.IsItem):
    """ The agent's policy when the user asks the agent whether an item has
        a specific attribute.

    """
    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.IsItemAttributePolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            A sentence representing a request (queries.be). The sentence should be in one of the following formats:

                - <agent>, Is (a) <item> <attribute>?
                - then <agent>, Is (a) <item> <attribute>?

            where <attribute> can be a string or a tuple. For example, Hannah, is the metal door open?


        """

        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "Be":
            return None, None
        item = describer.get_arg('Arg-PPT')
        attribute = describer.get_arg('Arg-PRD')
        steps, goal = None, None

        matching_sent = lc.Sentence()
        matching_desc = tdescribers.be((item, None),
                                       ('Is', None),
                                       (None, None),
                                       (attribute, None))

        matching_desc.args['AM-DIS'] = lc.Arg(self.player)
        matching_sent.describers = [matching_desc]

        am_tmp = describer.get_arg('AM-TMP', _type=0)
        if am_tmp is not None:
            matching_desc.args['AM-TMP'] = am_tmp

        if matching_sent == last_user_command:
            if isinstance(item, em.Entity) and isinstance(attribute, (str, list)):
                item = getattr(self.dialogue.dia_generator.world, item.get_property('var_name'))
                steps, goal = self.task(item, attribute)
            elif isinstance(item, list) and len(item) == 2 and item[0] == 'a' and isinstance(item[1], em.BaseEntity):
                def neg_res_func(item, player=self.player, attribute=attribute):
                    statement = lc.Sentence(speaker=player)
                    desc = tdescribers.be((item, None),
                              ('is', None),
                              (None, None),
                              (attribute, None))
                    statement.describers += [desc]
                    dont_know_res = tsentences.know(player, "not", "know", statement, speaker=player)
                    return dont_know_res

                attribute_part = lhelpers.convert_obj_to_part(attribute)

                statement = lc.Sentence([lc.Word('whether'),
                                         lc.Word('a'),
                                         item[1].describe(),
                                         lc.Word('is'),
                                         attribute_part],
                                        speaker=self.player)
                desc = tdescribers.be((item, statement.parts[1:3]),
                                      ('is', None),
                                      (None, None),
                                      (attribute, attribute_part))
                statement.describers = [desc]
                dont_know_res = tsentences.know(self.player, "not", "know", statement, speaker=self.player)

                is_not_res = tsentences.be((None, lc.Word("There")), "is", "not",
                                           item +['with', 'attribute', attribute], speaker=self.player)

                steps, goal = self.one_task(item[1], is_not_res, dont_know_res, neg_res_func, last_user_command,
                                            attribute=attribute)

        return steps, goal

    def task(self, item, attribute):
        """
        Computes the steps and the goal necessary for self.player
        successfully answering the question: Is <item> <attribute>?

        Parameters
        ----------
        item : Entity
            The item whose attribute existence is checked.
        attribute : str or tuple
            The attribute is a single value, unlike the property, which consists of a key, value pair.
            A few examples of attributes are: 'static', 'open', and 'locked'.

        """
        attr_casted = attribute
        if isinstance(attribute, list):
            attribute = tuple(attribute)

        dialogue = self.dialogue
        kb_state = dialogue.dia_generator.knowledge_base
        is_seen_pos = kn_checkers.property_check_alt(kb_state, item, None, attribute, None)

        attribute_part = lhelpers.convert_obj_to_part(attr_casted)
        if is_seen_pos is None:

            statement = lc.Sentence([lc.Word('whether'),
                                     item.describe(),
                                     lc.Word('is'),
                                     attribute_part],
                                    speaker=self.player)

            desc = tdescribers.be((item, statement.parts[1]),
                                  ('is', None),
                                  (None, None),
                                  (attr_casted, attribute_part))
            statement.describers = [desc]
            dont_know_res = tsentences.know(self.player, "not", "know", statement, speaker=self.player)
            say_sent = tsentences.say(self.player, None, "says", dont_know_res, speaker=self.player)
            steps = [say_sent]
            multiple_steps = [say_sent]
            if attribute in item.attributes:
                neg = None
            else:
                neg = "not"
            sent = tsentences.be(item, "is", neg, (attr_casted, attribute_part), speaker=self.player)
            say_sent = tsentences.say(self.player, None, "says", sent, speaker=self.player)
            multiple_steps.append(say_sent)
            goal = tgoals.Goal(tgoals.multiple_correct,
                               self.dialogue,
                               self.player,
                               multiple_steps,
                               len(self.dialogue.get_utterances()) - 1
                               )
            if self.dialogue is not None:
                random_gen = self.dialogue.random_gen
            else:
                random_gen = random.Random()

            if random_gen.choices([0, 1], weights=[0.8, 0.2], k=1)[0] == 1:
                steps.append(say_sent)
        else:
            if is_seen_pos:
                neg = None
            else:
                neg = "not"
            sent = tsentences.be(item, "is", neg, (attr_casted, attribute_part), speaker=self.player)
            say_sent = tsentences.say(self.player, None, "says", sent, speaker=self.player)
            steps = [say_sent]
            goal = tgoals.Goal(tgoals.multiple_correct, dialogue, self.player,
                               steps, len(self.dialogue.get_utterances()) - 1)
        return steps, goal


class ChangePolicy(bpolicies.ActionPolicy):
    """ The agent's policy when the user asks the agent to change an item's property.

        Attributes
        ----------
        get_policy : GetItemPolicy
            This policy is used if changing the item's property requires first getting it.
            This might be the case when coloring the item with a new color.
    """

    def __init__(self, player=None, get_policy=None, dialogue=None):
        super().__init__(player, None, dialogue)
        self.get_policy = get_policy

    def parse(self, last_user_command):
        """
        Parses the sentence last_user_command and checks if it matches the user
        request outputted from the policy user_policies.ChangePropPolicy.
        Then it returns the list of possible utterances and the goal of the agent self.player.

        Parameters
        ----------
        last_user_command : Sentence
            One of the following requests (queries.change):

                - <agent>, change (a) <entity> 's <property_key> to <new_val>
                - then <agent>, change (a) <entity> 's <property_key> to <new_val>

            The second sentence is encountered in the user_policies.AndPolicy.


        """
        describer = last_user_command.describers[0]
        if describer.get_arg("Rel", _type=0).infinitive != "change":
            return None, None
        thing_changing_arg = describer.get_arg('Arg-PPT', _type=0)
        thing_changing = thing_changing_arg.value if thing_changing_arg else None
        end_state_arg = describer.get_arg('Arg-PRD', _type=0)
        end_state = end_state_arg.value if end_state_arg else None

        change_query = queries.change(describer.get_arg("AM-TMP"), self.player,  None, 'change', thing_changing, end_state)
        steps, goal = None, None
        if last_user_command == change_query:
            if isinstance(thing_changing, list) and isinstance(end_state, list) and end_state[0] == "to":
                if (isinstance(thing_changing, list) and isinstance(thing_changing[1], em.BaseEntity) and
                        thing_changing[2] == "'s" and thing_changing[0] == 'a'):
                    can_not_change_res = tsentences.change(self.player,
                                                           'can',
                                                           'not',
                                                           'change',
                                                           copy.copy(thing_changing),
                                                           end_state,
                                                           None,
                                                           self.player)

                    def neg_res_func(item, player=self.player, thing_changing=copy.copy(thing_changing[3:]), end_state=end_state):
                        res = tsentences.change(player,
                                                'can',
                                                'not',
                                                'change',
                                                [item, "'s"]+thing_changing,
                                                end_state,
                                                speaker=self.player)
                        return res

                    steps, goal = self.one_task(thing_changing[1],
                                                can_not_change_res,
                                                neg_res_func,
                                                last_user_command,
                                                element_key=thing_changing[3:],
                                                end_state=end_state)
                elif (isinstance(thing_changing, list) and isinstance(thing_changing[0], em.Entity) and
                        thing_changing[1] == "'s"):
                    item = getattr(self.dialogue.dia_generator.world, thing_changing[0].get_property('var_name'))
                    steps, goal = self.task(item, thing_changing[2:], end_state)
        return steps, goal

    def task(self, item, element_key, end_state):
        """
        Computes the steps and the goal necessary for self.player
        successfully changing the item's property.

        Parameters
        ----------
        item : Entity
            The item whose property is changed.
        element_key : list
            The property key. For example, ['nickname'] or ['north', 'obstacle']
        end_state : any
            The new property value. For example, 'lovebug' or 'green'.

        """
        element_key_list = element_key
        if len(element_key) == 1:
            element_key = element_key[0]
        else:
            element_key = tuple(element_key)

        steps, goal = None, None
        sent2 = tsentences.permit(action_allowed=tsentences.change(rel="changing",
                                                                   thing_changing=['the', 'item', "'s", element_key]),
                                  rel="permitted")
        sent21 = tsentences.be(['if', 'item'], 'is', None, ['in', 'player'])
        sent2.describers[0].args['AM-ADV'] = lc.Arg(sent21, sent21)
        sent2.parts.append(sent21)

        element_val = end_state[1:]
        if len(element_val) == 1:
            element_val = element_val[0]
        if isinstance(element_val, list):
            can_not_change_res = tsentences.change(self.player,  "can", "not", 'change',
                                                   [item, "'s"]+element_key_list, ['to'] + element_val)
        else:
            can_not_change_res = tsentences.change(self.player,  "can", "not", 'change',
                                                   [item, "'s"]+element_key_list, ['to', element_val])

        loc_is_rev = tsentences.be([item, "'s", 'location'], 'is', None, ['in', self.player])
        get_neg = False
        if element_key in ['color', 'size'] and self.dialogue.dia_generator.knowledge_base.check(sent2) and not self.dialogue.dia_generator.knowledge_base.check(loc_is_rev):

            get_steps, get_goal = self.get_policy.task(item, None)
            if len(get_steps) > 0 and get_steps[0].describers[0].args['Rel'].infinitive == "say" and em_helpers.check_can_not(lhelpers.reduce_sentences([get_steps[0].describers[0].get_arg('Arg-PPT')]), "get"):
                get_neg = True
                phelpers.add_can_not(can_not_change_res, get_goal.args[2])
        else:
            get_steps = []
            get_goal = tgoals.Goal(lambda: 1)

        state = self.dialogue.dia_generator.world.save_state()
        if element_key in ["color", "size"]:
            sloc = self.player.properties['location'][1].top_location()
            tloc = item.properties['location'][1].top_location()
            phelpers.make_item_reachable(self.player, sloc, tloc, self.dialogue.dia_generator.world)
            phelpers.open_all_containers(self.player, item, self.dialogue.dia_generator.world)
            actions.get(item, self.player, item.properties['location'][1], item.properties['location'][0])

        orig_res = actions.change(item, self.player, element_key, element_val)
        self.dialogue.dia_generator.world.recover_state(state)

        tries_step = tsentences.tries(self.player, None, None, "tries",
                                      tsentences.change(None, None, None, "changing",
                                                        [item, "'s"]+element_key_list, end_state, None, self.player),
                                      self.player)

        if isinstance(element_val, list):
            change_res = tsentences.change(self.player,  None, None, 'changes',
                                           [item, "'s"]+element_key_list, ['to'] + element_val)
        else:
            change_res = tsentences.change(self.player,  None, None, 'changes',
                                           [item, "'s"]+element_key_list, ['to', element_val])

        if orig_res[0] != change_res:
            flattened_res = phelpers.extract_reasons(orig_res)
            steps_checked, steps_not_checked = phelpers.compute_say_steps(flattened_res,
                                                                          orig_res,
                                                                          self.player,
                                                                          self.dialogue.dia_generator.knowledge_base)

            correct_steps = steps_checked+steps_not_checked
            goal_multiple = tgoals.Goal(tgoals.multiple_correct,
                                        self.dialogue,
                                        self.player,
                                        correct_steps,
                                        len(self.dialogue.get_utterances()) - 1
                                        )

            if len(steps_checked) > 0:
                steps = steps_checked
                goal = goal_multiple

        if steps is None and goal is None:

            if get_neg:
                steps, goal = get_steps, get_goal
            else:
                sub_goal = tgoals.Goal(tgoals.multiple_correct, self.dialogue,
                                       self.player, [tries_step], len(self.dialogue.get_utterances()) - 1)
                goal = tgoals.Goal(tgoals.goal_and, [get_goal, sub_goal])
                steps = get_steps if len(get_steps) > 0 else [tries_step]

        return steps, goal

    def replace_dialogue(self, new_dialogue):
        """ Replaces the current dialogue with a new one. """
        super().replace_dialogue(new_dialogue)
        self.get_policy.replace_dialogue(new_dialogue)


class AndPolicy:
    """ The agent's policy when the user issues multiple requests for multiple agents.
        The requests should be satisfied in the order given by the user.

        Attributes
        ----------
        prev_user_command : Sentence
            The current user request in the form:

                <user_request1> and then <user_request2> and then ...

            where the <user_request_idx> is a primitive user request. For example:

                Andy, go north, and Hannah, get the red apple

        curr_goal_uidx : int
            The index of the current goal of the agent self.player.
            The index is computed based on the order of the user requests <user_request_idx>.
            For the example above, <user_request1> has index 0, and <user_request2> has index 1.
            The Goal can be fetched using self.utterance_goal[curr_goal_uidx].
        players_in_order : list of Entity-s
            Since the user can issue multiple requests to multiple agents and the agents have to fulfill the requests in
            consecutive order, this list contains all ordered players. The list can contain repeating player entities.
        stop_at : int
            Indicates the index of the last request made to the agent self.player.
            It is the index of the last occurrence of self.player in the players_in_order list.
        utterance_goal : dict
            A mapping from a user request index to a goal.
            It stores all the agent's goals.
        policies_used : list
            The AndPolicy can use other primitive agent's policies in order to compute the steps necessary
            to fulfill the user's request. Since these policies' states can be altered, this field is used to keep
            track of the ones that were used so that later the state can be recovered if needed.
        num_goals : int
            The number of user requests issued to the agent.
            The number of requests equals the number of goals of the agent.
        player : Entity
            The agent.
        dialogue : Dialogue
            The dialogue that the policy is part of.


    """

    def __init__(self, player, dialogue=None):
        self.prev_user_command = None
        self.curr_goal_uidx = None
        self.players_in_order = list()
        self.stop_at = None
        self.utterance_goal = dict()
        self.policies_used = []
        self.num_goals = None
        self.player = player
        self.dialogue = dialogue

    def execute(self, include_goal=False, say_last_user_command=None):
        """ Returns the valid utterances for the agent self.player and optionally the goal.
            The say_last_user_command should be in the format:

                <user> says: <user_request1> and then <user_request2> and then ...
        """
        step, goal = self._and_parse(say_last_user_command)
        if include_goal:
            return step, goal
        return step

    def _and_parse(self, say_last_user_command=None):
        """ Computes the valid steps and the goal of the agent
            for the following user request:
                <user> says: <user_request1> and then <user_request2> and then ...
            where the <user_request_idx> is a primitive user request. For example,
            Andy, go north, and Hannah, get the red apple.
        """
        if not say_last_user_command:
            say_last_user_command = self.dialogue.utterances[0] if len(self.dialogue.utterances) > 0 else None

        policy_database = self.dialogue.dia_generator.agent_policy_database
        last_user_command = phelpers.extract_inner_sent(say_last_user_command)
        if id(self.prev_user_command) != id(last_user_command):
            self.reset()
        if self.prev_user_command is None:
            self.prev_user_command = last_user_command

        if last_user_command is None or len(last_user_command.describers) <= 1:
            return None, None

        self.set_members(last_user_command)
        if self.num_goals == 0 or (self.compute_goal() is not None and self.compute_goal().execute() == 1):
            return None, self.compute_goal()

        if self.dialogue.curr_speaker != self.player:
            return self.recursion_break()

        reduce_say = lhelpers.reduce_sentences([say_last_user_command])
        if self.stop_at is None:
            self.stop_at = len(reduce_say)-1

        for uidx, sent in enumerate(reduce_say[:self.stop_at+1]):
            if isinstance(sent, lc.Sentence):
                inner_sentence = phelpers.extract_inner_sent(sent)
                curr_player = inner_sentence.describers[0].get_arg('AM-DIS')
                if curr_player != self.player:

                    # How does it know that the curr_player is not after the self.player?
                    # Because it is controlled from stop_at and here it returns
                    # immediately when it sees a policy.
                    for pol in self.dialogue.policies[1:]:
                        if curr_player == pol.player:
                            if pol.dialogue != self.dialogue:
                                pol.replace_dialogue(self.dialogue)
                            steps = pol.execute()
                            if steps is not None:
                                return None, self.compute_goal()
                else:
                    steps = None
                    goal = None
                    for pol in policy_database[curr_player]:
                        if pol != self:
                            if pol.dialogue != self.dialogue:
                                pol.replace_dialogue(self.dialogue)
                            steps, goal = pol.execute(include_goal=True, say_last_user_command=sent)
                            if pol not in self.policies_used:
                                self.policies_used.append(pol)
                        if steps is not None:
                            break

                    if steps is None:
                        return None, self.compute_goal()

                    if goal is not None:
                        uidx_goal = self.utterance_goal.get(uidx, None)
                        if uidx_goal is None:
                            self.utterance_goal[uidx] = goal
                            self.curr_goal_uidx = uidx
                        if self.utterance_goal[uidx].execute() != 1:
                            self.utterance_goal[uidx] = goal
                            return steps, self.compute_goal()

        return None, self.compute_goal()

    def compute_goal(self, last_user_command=None):
        """
        Returns the goal of the policy.
        """
        if self.num_goals is None:
            if last_user_command is None:
                last_user_command = self.dialogue.utterances[0]
                if last_user_command is not None:
                    self.set_members(last_user_command)
                else:
                    return None

        # This means that the agent is in the process of responding.
        if len(self.utterance_goal) == 0 and self.num_goals > 0:
            return tgoals.Goal(lambda: 0)

        if self.num_goals == 0:
            return None

        def goals_and_func(pol):
            """ The user can issue multiple requests to the agent.
                Therefore, the agent can have multiple goals.
                If all the agent's goals return 1, then the final goal is 1.
                Otherwise, the goal value is 0 (which means in progress).
            """
            if len(pol.utterance_goal) != pol.num_goals:
                return 0
            goal_res = []
            goals = list(pol.utterance_goal.values())
            for gol in goals:
                if gol.execute() is not None:
                    goal_res.append(gol.execute())

            if len(goal_res) == 0:
                return 0
            return all(goal_res)

        return tgoals.Goal(goals_and_func, **{
            'pol': self,
        })

    def set_members(self, last_user_command):
        """ Sets the number of goals that the agent has to accomplish,
            the players in order of execution of the requests and
            when the agent should stop outputting steps.
        """
        if self.num_goals is None:
            self.num_goals = 0
            del self.players_in_order[:]
            reduce_say = lhelpers.reduce_sentences([last_user_command])
            for uidx, sent in enumerate(reduce_say):
                if isinstance(sent, lc.Sentence):
                    curr_player = sent.describers[0].get_arg('AM-DIS')
                    self.players_in_order.append(curr_player)
                    if self.player == curr_player:
                        self.num_goals += 1
                        self.stop_at = uidx

    def recursion_break(self):
        """ This function breaks the recursion because other players' AndPolicy-ies might call
            this any policy and vice versa. This can cause an infinite recursion.

            This function is called when the other_player has to check whether self.player still has
            steps to output before other_player can provide a response. So self.player will be before
            other_player in the self.players_in_order. This is because other_player only calls the AndPolicy-ies
            from previous players and stops when there are no more user requests assigned to the other_player.
            (indicated by the stop_at field).

            The function works as follows:
                1. If the agent does not have a goal, that means it is not currently satisfying any user requests.
                   Therefore, the next valid step is None. The agent can have previous goals so get_goal() is returned
                   as the goal.
                2. If the current goal is not 1 (not success), then this means that the agent is not yet finished and
                   there are more steps to be computed. The steps are not computed here since this might lead to an infinite
                   recursion again by calling other agent's AndPolicy-ies. Therefore only [lc.Sentence()] is returned to indicate
                   that more steps are coming and that steps are not None.
                3. The current goal is 1 (success), and the self.player has two consecutive requests to fulfill.
                   Since there are more steps to be computed, [lc.Sentence()] is returned to indicate
                   that more steps are coming and that steps are not None.
                4. The current goal is 1 (success), and the self.player has no consecutive requests to fulfill.
                   In this case, None is returned to indicate no more steps are to be expected from self.player
        """
        if self.curr_goal_uidx is not None:
            if self.utterance_goal[self.curr_goal_uidx].execute() == 1:
                if self.curr_goal_uidx + 1 >= len(self.players_in_order) or self.players_in_order[self.curr_goal_uidx + 1] != self.player:
                    steps, goal = None, self.compute_goal()
                else:
                    steps, goal = [lc.Sentence()], self.compute_goal()
            else:
                steps, goal = [lc.Sentence()], self.compute_goal()
        else:
            steps, goal = None, self.compute_goal()

        return steps, goal

    def get_steps(self, say_last_user_command=None):
        """ Returns the next agent steps. """
        steps, _ = self.execute(include_goal=False, say_last_user_command=say_last_user_command)
        return steps

    def get_goal(self, say_last_user_command=None):
        """ Returns the goal of the policy. """
        _, goal = self.execute(include_goal=True, say_last_user_command=say_last_user_command)
        return goal

    def reset(self):
        """ Resets the state that is tied to the user request when a new request comes. """
        self.prev_user_command = None
        self.curr_goal_uidx = None
        self.utterance_goal = dict()
        self.policies_used = []
        self.num_goals = None
        self.players_in_order = list()
        self.stop_at = None

    def replace_dialogue(self, new_dialogue):
        """ Replaces the current dialogue with a new one and resets the state."""
        self.dialogue = new_dialogue
        self.reset()

    def save_state(self):
        """ Saves the state that changes with time """
        state = (self.prev_user_command,
                 copy.copy(self.utterance_goal),
                 self.num_goals,
                 [p.save_state() for p in self.policies_used],
                 copy.copy(self.policies_used),
                 self.dialogue,
                 copy.copy(self.players_in_order),
                 self.stop_at,
                 self.curr_goal_uidx
                 )
        return state

    def recover_state(self, state):
        """ Recovers the state that changes with time """
        self.prev_user_command = state[0]

        self.utterance_goal.clear()
        self.utterance_goal.update(state[1])
        self.num_goals = state[2]

        for idx in range(len(state[4])):
            pol = state[4][idx]
            pol.recover_state(state[3][idx])

        del self.policies_used[:]
        self.policies_used.extend(state[4])

        self.dialogue = state[5]
        del self.players_in_order[:]
        self.players_in_order.extend(state[6])
        self.stop_at = state[7]
        self.curr_goal_uidx = state[8]

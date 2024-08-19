#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the policies that the environment uses to provide feedback to the player.
"""
import logging
from abc import abstractmethod

from ..policies import base_policies as bpolicies
from ..language import components as lc
from ..environment import entities as em
from ..environment import actions
from ..environment import helpers as env_helpers
from ..language import sentences as tsentences
from ..language import desc_mappers

logger = logging.getLogger(__name__)


class EnvPolicy(bpolicies.Policy):
    """ The environment policy provides a response to every player's action.
        The player is None, since the environment is not governed by any entity.
    """
    def __init__(self, dialogue=None):
        super().__init__(None, dialogue)
        self.dialogue = dialogue

    def execute(self, include_goal=False, last_utter=None):
        """
        Returns the environment response as feedback to the last utterance of the agent.

        Parameters
        ----------
        include_goal : bool, optional
            Whether to include the goal of the environment.
        last_utter : Sentence, optional
            If the last utterance is not provided, the last dialogue utterance is taken.

        Returns
        -------
        list
            Returns multiple valid environmental responses.
        None, optional
            The goal of the environment is None, since the goal is currently generated in the
            agent's policy.
        """

        if last_utter is None:
            dia_utterances = self.dialogue.get_utterances()
            if len(dia_utterances) > 0:
                last_utter = dia_utterances[-1]
            else:
                last_utter = None

        if last_utter is None or len(last_utter.describers) == 0 or last_utter.speaker is None:
            responses = None
        else:
            try:
                responses = self.parse(last_utter=last_utter)
            except Exception as err:
                logger.error(err, exc_info=True)
                responses = None
        if include_goal:
            return responses, None
        return responses

    @abstractmethod
    def parse(self, last_utter):
        """
        Parses the utterance into an actions.<action> method call that provides the environment feedback.

        Parameters
        ----------
        last_utter : Sentence
            The utterance to be parsed.

        Returns
        -------
        res : Sentence
            Returns multiple valid environmental responses.
        """

    def get_steps(self, **params):
        """ Returns the valid responses of the environment """
        steps = self.execute(include_goal=False, **params)
        return steps

    def get_goal(self, **params):
        """ Returns the goal of the environment. The environment goal is None since
            the agents have goals.
        """
        return None

    def save_state(self):
        """
        Returns the state from the parent class and additionally the world state.
        The world state is returned since the environment's policies make changes
        in the world.

        """
        if self.dialogue is not None:
            state = self.dialogue.dia_generator.world.save_state()
        else:
            state = None
        return super().save_state(), state

    def recover_state(self, state):
        """ Recovers the parent state and the environment state. """
        super().recover_state(state[0])
        if self.dialogue is not None:
            self.dialogue.dia_generator.world.recover_state(state[1])


class EmptyPolicy(EnvPolicy):
    """ This policy is used when a player issues an empty sentence (that does not contain any verbs or
        describers). """
    def parse(self, last_utter):
        """ Returns a sentence: <speaker> issued an empty response if the last speaker's utterance
            has no describers or no verb.
        """
        describers = last_utter.describers
        result = None
        if len(describers) == 0 or describers[0].get_arg('Rel') is None:
            result = tsentences.issue(last_utter.speaker,
                                      None,
                                      None,
                                      "issued",
                                      ["an", "empty", "response"]
                                      )
        return result


class GoPolicy(EnvPolicy):
    """ This policy is used for providing feedback when a player tries moving in the world."""

    def parse(self, last_utter):
        """
        Parses the player's utterance into an actions.go method call that provides the environmental feedback.
        The utterance has to be in the form:

            <player> tries going <direction> (from_location)
        """
        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)

        if inner_utter is None or player is None:
            return None
        describer = inner_utter.describers[0]
        direction = describer.get_arg('AM-DIR')
        from_location = describer.get_arg('Arg-DIR')

        if inner_utter == tsentences.go(rel=('going', None),
                                        direction=(direction, None),
                                        source_location=(from_location, None)):

            if from_location is not None:
                if (isinstance(from_location, list) and len(from_location) == 2
                        and from_location[0] == "from" and isinstance(from_location[1], em.Entity)):
                    from_location = getattr(world, from_location[1].properties.get("var_name"), from_location)
                else:
                    return None

            if direction is not None and isinstance(direction, str):
                res = actions.go(player, direction, from_location)
                return res
        return None


class GetPolicy(EnvPolicy):
    """ This policy is used for providing feedback when a player tries getting an entity in the world."""

    def parse(self, last_utter):
        """
        Parses the player's utterance into an actions.get method call that provides the environmental feedback.

        The utterance has to be in the form:

            <player> tries getting <entity> <location_preposition> <location>

        The location refers to the entity's location.
        For example, Hannah tries getting the plastic container under the table.
        Here the plastic container's location is under the table.

        """
        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)
        if inner_utter is None or player is None:
            return None
        describer = inner_utter.describers[0]
        entity = describer.get_arg('Arg-PPT')
        prep_location = describer.get_arg('Arg-DIR')
        if (
                inner_utter == tsentences.get(rel=('getting', None),
                                              entity=(entity, None),
                                              prepos_location=(prep_location, None))):
            if isinstance(entity, em.Entity):
                entity = getattr(world, entity.properties.get("var_name"))
            else:
                return None
            if prep_location is None:
                location_position, location = None, None
            elif (isinstance(prep_location, list) and len(prep_location) == 2
                    and isinstance(prep_location[0], str) and isinstance(prep_location[1], em.Entity)):
                location_position = prep_location[0]
                location = getattr(world, prep_location[1].properties.get("var_name"))
            else:
                return None
            res = actions.get(entity, player, location, location_position)
            return res
        return None


class DropPolicy(EnvPolicy):
    """ This policy is used for providing a response when a player tries dropping an entity in the world."""

    def parse(self, last_utter):
        """
            Parses the player's utterance into an actions.drop method call that provides the environmental feedback.
            The utterance has to be in the following form:

                <player> tries dropping <entity> <location_position> <location>

            The location refers to the one where the entity should be dropped.
            For example, The big person tries dropping the small ball in the toy's container.

        """
        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)
        if inner_utter is None or player is None:
            return None
        inner_desc = inner_utter.describers[0]
        entity = inner_desc.get_arg('Arg-PPT')
        prep_location = inner_desc.get_arg('Arg-GOL')

        if (inner_utter == tsentences.drop(rel=('dropping', None),
                                           entity=(entity, None),
                                           prepos_location=(prep_location, None)
                                           )):
            if prep_location is None:
                location_position, location = None, None
            elif (isinstance(prep_location, list) and len(prep_location) == 2
                  and isinstance(prep_location[0], str) and isinstance(prep_location[1], em.Entity)):
                location_position = prep_location[0]
                location = getattr(world, prep_location[1].properties.get("var_name"))
            else:
                return None
            if entity is not None and isinstance(entity, em.Entity):
                entity = getattr(world, entity.properties.get("var_name"))
                res = actions.drop(entity, player, location, location_position)
                return res
        return None


class OpenClosePolicy(EnvPolicy):
    """ The environment policy for providing a response when a player tries opening/closing an entity in the world."""

    def parse(self, last_utter):
        """
            Parses the player's utterance into an actions.open or actions.close method call
            that provides the environment's feedback.

            The utterance has to be in the following form:

                <player> tries <action> <entity> <location_position> <location>

            The action is either opening or closing.
            The location refers to the entity's location.
            For example, John tries opening the wooden door in the kitchen.
        """
        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)
        if inner_utter is None or player is None:
            return None
        inner_desc = inner_utter.describers[0]
        rel = inner_desc.get_arg('Rel')

        if rel == "opening":
            res_func = tsentences.opens
        elif rel == "closing":
            res_func = tsentences.close
        else:
            return None
        entity = inner_desc.get_arg('Arg-PPT')
        if isinstance(entity, em.Entity):
            entity = getattr(world, entity.properties.get("var_name"))
        else:
            return None

        prep_location = inner_desc.get_arg('AM-LOC')
        action_res = res_func((None, None), (None, None), (None, None),
                              (rel, None), (entity, None), (prep_location, None))

        if inner_utter == action_res:
            if prep_location is None:
                location_position, location = None, None
            elif (isinstance(prep_location, list) and len(prep_location) == 2
                  and isinstance(prep_location[0], str) and isinstance(prep_location[1], em.Entity)):
                location_position = prep_location[0]
                location = getattr(world, prep_location[1].properties.get("var_name"))
            else:
                return None
            if rel == "opening":
                res = actions.opens(entity, player, location, location_position)
            else:
                res = actions.closes(entity, player, location, location_position)
            return res
        return None


class LookPolicy(EnvPolicy):
    """ This policy provides a response when a player tries looking at an entity in the world."""

    def parse(self, last_utter):
        """
            Parses the player's utterance into an actions.look method call that provides the environmental feedback.

            The utterance has to be in the form:

                <player> tries looking <location_preposition1> <entity> <location_preposition2> <location>

            The location refers to the entity's location.
            For example, John tries looking in the toys container in the bedroom.
        """

        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)
        if inner_utter is None or player is None:
            return None
        inner_desc = inner_utter.describers[0]
        prep_thing_looked = inner_desc.get_arg('Arg-GOL')
        item_location = inner_desc.get_arg('AM-LOC')

        if (inner_utter == tsentences.look(rel=('looking', None),
                                           thing_looked=(prep_thing_looked, None),
                                           item_location=(item_location, None))):

            if prep_thing_looked is None:
                location_position, location = None, None
                thing_looked = None
            elif (isinstance(prep_thing_looked, list) and len(prep_thing_looked) == 2
                    and isinstance(prep_thing_looked[0], str) and isinstance(prep_thing_looked[1], em.Entity)):
                location_position = prep_thing_looked[0]
                thing_looked = getattr(world, prep_thing_looked[1].properties.get("var_name"))
            else:
                return None

            if thing_looked is not None:
                thing_looked = getattr(world, thing_looked.properties.get("var_name"), None)
                res = actions.look(thing_looked, player, location_position,
                                   [item_location[0], getattr(world, item_location[1].properties.get("var_name"))])
                return res
        return None


class SayPolicy(EnvPolicy):
    """ This policy provides a response when a player says a sentence """

    def parse(self, last_utter):
        """ Checks whether a sentence is in the format <user> says to <agent>: <inner_sentence>
            and if so, it returns an empty sentence with speaker=None.
            speaker=None indicates that the sentence is uttered by the environment.
            The empty sentence is returned because there is no need to implement actions.say.
            The agent can say anything, and the agent's utterance is anyway added to the context.
        """

        describer = last_utter.describers[0]
        user = describer.get_arg('Arg-PAG')
        if user != last_utter.speaker:
            return None

        mapped_sent = desc_mappers.say(last_utter.describers)
        if describer.get_arg("AM-NEG") is None and mapped_sent == last_utter:
            empty_sent = lc.Sentence()
            empty_sent.describers.append(lc.Describer())
            empty_sent.speaker = None
            return empty_sent
        return None


class ChangePolicy(EnvPolicy):
    """ This policy provides a response when a player wants to change an entity's property. """

    def parse(self, last_utter):
        """
            Parses the player's utterance into an actions.change method call that provides the environmental feedback.

            The utterance has to be in the form:

                <player> tries changing <entity> <element_key> <end_state>

            For example, Gretel tries changing the ball's color to orange.
        """
        world = self.dialogue.dia_generator.world
        inner_utter, player = env_helpers.extract_tries_sent(last_utter, world)
        if inner_utter is None or player is None:
            return None
        inner_desc = inner_utter.describers[0]

        thing_changing = inner_desc.get_arg('Arg-PPT')
        end_state = inner_desc.get_arg("Arg-PRD")

        if inner_utter == tsentences.change(rel=("changing", None),
                                            thing_changing=(thing_changing, None),
                                            end_state=(end_state, None)):
            if (isinstance(thing_changing, list) and len(thing_changing) >= 3
                    and isinstance(thing_changing[0], em.Entity) and thing_changing[1] == "'s"):
                element_key = thing_changing[2:]
                if len(element_key) == 1:
                    element_key = element_key[0]
                else:
                    element_key = tuple(element_key)

                item = getattr(world, thing_changing[0].properties.get("var_name"))
                if isinstance(end_state, list) and len(end_state) >= 2 and end_state[0] == "to":
                    if len(end_state[1:]) == 1:
                        end_state = end_state[1]
                    else:
                        end_state = end_state[1:]
                    res = actions.change(item, player, element_key, end_state)
                    return res
        return None


class EnvAutoPolicy(bpolicies.AutoPolicy):
    """ A policy that automatically selects the right policy out of a list of environmental policies. """

    def execute(self, include_goal=False, **params):
        """
            Runs the policy and returns a list of valid environment responses.

            Additionally, the goal is returned if include_goal is set to True.
            If all the policies in self.list_policies return None, then the environment returns:

                <player> issued an unrecognizable command.

        """
        if "last_utter" in params:
            last_utter = params["last_utter"]
        else:
            dia_utterances = self.dialogue.get_utterances()
            if len(dia_utterances) > 0:
                last_utter = dia_utterances[-1]
            else:
                last_utter = None
            params['last_utter'] = last_utter

        if last_utter is not None and last_utter.speaker is not None:
            result = super().execute(include_goal, **params)

            if result is None:
                result = tsentences.issue(last_utter.speaker,
                                          None,
                                          None,
                                          "issued",
                                          ["an", "unrecognizable", "command"]
                                          )
        else:
            result = None

        if include_goal is True and not isinstance(result, tuple):
            result = (result, None)

        return result

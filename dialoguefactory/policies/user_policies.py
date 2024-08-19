#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the user policies that the user uses to respond to the dialogue.
"""

import copy
from abc import ABC, abstractmethod

from ..language import sentences as tsentences
from ..language import queries as tqueries

from . import base_policies as bp


class UserPolicy(bp.Policy, ABC):
    """
    The policy for the user issuing a request.

    The goal is always None since the goal is defined in the agent policy
    (see base_policies.ActionPolicy).

    Attributes
    ----------
    player : Entity
        The user.
    dialogue : Dialogue, optional
        The dialogue where this policy is used. The default is None.

    """

    def execute(self, include_goal=False, **params):
        steps = self.get_steps(**params)
        goal = self.get_goal(**params)
        if include_goal:
            return steps, goal
        else:
            return steps

    def get_goal(self, **params):
        return None


class BaseItemPolicy(UserPolicy, ABC):
    """
    Base policy that covers the user requests in the following format:

    ..

        <player> says: <agent>, <action> (a) <item>

    For example, Andy says: Hans, get a red ball

    Attributes
    ----------
    player : Entity
        The user that issues the request.
    item : Entity
        The item that the user acts upon.
    agent : Entity
        The agent that has to perform the action.
    dialogue : Dialogue, optional
        The dialogue that the policy belongs to. The default is None.

    """
    def __init__(self, player, item=None, agent=None, dialogue=None):
        super().__init__(player, dialogue)
        self.item = item
        self.agent = agent

    @abstractmethod
    def generate_response(self, item, agent_desc_elems, tmp):
        """
        Generate the user request that the agent has to complete.

        Parameters
        ----------
        item : Entity
            The entity that the agent acts upon.
        agent_desc_elems : list
            List of elements, property keys, attributes, or other strings for the agent description.
        tmp : tuple
            The tmp element is used for temporal words/phrases. The first element of the tuple
            can be a string or a list and the second one Word or Phrase.


        Returns
        -------
        Sentence
            The user request.
        """
        pass

    def get_steps(self, **params):
        """
        Get the user request based on the attributes of this class.

        Returns
        -------
        sent : Sentence
            The user request.

        """
        if self.item is None or self.agent is None:
            return None

        sent = None

        player_prev_utters = self.dialogue.get_player_utters(self.player)

        if len(player_prev_utters) < 1:
            item = self.item
            self.agent.describe()
            agent_desc_elems = copy.copy(self.agent.description.elements)
            if agent_desc_elems[0] == "the":
                del agent_desc_elems[0]
            tmp = params.get("tmp", None)
            sent = self.generate_response(item, agent_desc_elems, tmp)
            if sent is not None:
                sent = tsentences.say(self.player, None, 'says',
                                      sent, speaker=self.player)
            self.reset()
        return sent

    def reset(self):
        self.item = None
        self.agent = None

    def save_state(self):
        return self.item, self.agent

    def recover_state(self, state):
        self.item, self.agent = state[0], state[1]


class ActionItemPolicy(BaseItemPolicy, ABC):
    """ Action policy that covers the user requests in the following format:

            <agent>, <action> (a) <item> <location_position> <location>

        For example, Hans, get the red ball in the kitchen.

    """
    def __init__(self, player, item=None, agent=None, location=None, location_position=None,  dialogue=None):
        super().__init__(player, item, agent,  dialogue)
        self.location = location
        self.location_position = location_position

    def reset(self):
        super().reset()
        self.location = None
        self.location_position = None

    def save_state(self):
        return super().save_state(), self.location, self.location_position

    def recover_state(self, state):
        super().recover_state(state[0])
        self.location, self.location_position = state[1], state[2]


class GoDirectionPolicy(UserPolicy):
    """ Action policy that covers the user requests in the following format:

            <player> says: <agent>, go <direction>

        For example, the big person says: John, go north
    """
    def __init__(self, player, agent=None, direction=None, dialogue=None):
        super().__init__(player, dialogue)
        self.agent = agent
        self.direction = direction

    def get_steps(self, **params):
        sent = None
        if self.agent is None or self.direction is None:
            return None

        player_prev_utters = self.dialogue.get_player_utters(self.player)

        if len(player_prev_utters) < 1:
            tmp = params.get("tmp", None)
            self.agent.describe()
            agent_desc_elems = copy.copy(self.agent.description.elements)
            if agent_desc_elems[0] == "the":
                del agent_desc_elems[0]

            request_go_to_direction = tqueries.go(tmp=tmp,
                                                  player=(self.agent, self.agent.describe(agent_desc_elems)),
                                                  rel="go",
                                                  direction=self.direction,
                                                  speaker=self.player)

            sent = tsentences.say(self.player, None, 'says',
                                  request_go_to_direction, speaker=self.player)
            self.reset()

        return sent

    def reset(self):
        self.agent = None
        self.direction = None

    def save_state(self):
        return self.agent, self.direction

    def recover_state(self, state):
        self.agent = state[0]
        self.direction = state[1]


class GoLocationPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, go to (a) item """
    def generate_response(self, item, agent_desc_elems, tmp):

        if "abstract" in item.attributes:
            target_location = ['to', 'a', item]
        else:
            target_location = ['to', item]

        sent = tqueries.go(tmp,
                           (self.agent, self.agent.describe(agent_desc_elems)),
                           rel='go',
                           target_location=target_location,
                           speaker=self.player)

        return sent


class GetItemPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, get (a) item <location_position> <location>"""

    def generate_response(self, item, agent_desc_elems, tmp):
        if "abstract" in item.attributes:
            item = ['a', item]
        if self.location is not None:
            loc_pos = [self.location_position, self.location]
        else:
            loc_pos = None

        sent = tqueries.get(tmp,
                            (self.agent, self.agent.describe(agent_desc_elems)),
                            rel='get',
                            entity=item,
                            prepos_location=loc_pos,
                            speaker=self.player)

        return sent


class DropItemPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, drop (a) item <location_position> <location>"""

    def generate_response(self, item, agent_desc_elems, tmp):
        if "abstract" in item.attributes:
            item = ['a', item]

        if self.location is not None:
            loc_pos = [self.location_position, self.location]
        else:
            loc_pos = None

        sent = tqueries.drop(tmp,
                             (self.agent, self.agent.describe(agent_desc_elems)),
                             rel='drop',
                             entity=item,
                             prepos_location=loc_pos,
                             speaker=self.player)
        return sent


class LookItemPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, look <location_position> (a) item in <location> """

    def generate_response(self, item, agent_desc_elems, tmp):

        if "abstract" in item.attributes:
            item = ['a', item]

        if self.location is not None:
            loc_pos = ['in', self.location]
        else:
            loc_pos = None

        if isinstance(item, list):
            item = [self.location_position] + item
        else:
            item = [self.location_position, item]

        sent = tqueries.look(tmp,
                             (self.agent, self.agent.describe(agent_desc_elems)),
                             rel='look',
                             thing_looked=item,
                             item_location=loc_pos,
                             speaker=self.player)
        return sent


class OpenItemPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, open (a) <item> <location_position> <location> """

    def generate_response(self, item, agent_desc_elems, tmp):

        if "abstract" in item.attributes:
            item = ['a', item]

        if self.location is not None:
            loc_pos = [self.location_position, self.location]
        else:
            loc_pos = None

        sent = tqueries.opens(tmp,
                              (self.agent, self.agent.describe(agent_desc_elems)),
                              rel='open',
                              thing_opened=item,
                              prepos_location=loc_pos,
                              speaker=self.player)
        return sent


class CloseItemPolicy(ActionItemPolicy):
    """ The policy for the user request: <agent>, close (a) item <location_position> <location> """

    def generate_response(self, item, agent_desc_elems, tmp):

        if "abstract" in item.attributes:
            item = ['a', item]

        if self.location is not None:
            loc_pos = [self.location_position, self.location]
        else:
            loc_pos = None

        sent = tqueries.close(tmp,
                              (self.agent, self.agent.describe(agent_desc_elems)),
                              rel='close',
                              thing_closed=item,
                              prepos_location=loc_pos,
                              speaker=self.player)
        return sent


class ChangePropPolicy(BaseItemPolicy):
    """ The policy for the user request: <agent>, change (a) <item> 's <prop_key> to <new_val>
        For example, Jim change the big container color to red.  """

    def __init__(self, player, item=None, agent=None, prop_key=None, new_val=None, dialogue=None):
        super().__init__(player, item, agent, dialogue)
        self.prop_key = prop_key
        self.new_val = new_val

    def generate_response(self, item, agent_desc_elems, tmp):

        if self.prop_key is None or self.new_val is None:
            return None

        if "abstract" in item.attributes:
            item = ['a', item]

        new_val = self.new_val
        if not isinstance(new_val, list):
            new_val = [new_val]

        if isinstance(self.prop_key, tuple):
            prop_key = list(self.prop_key)
        else:
            prop_key = [self.prop_key]
        if isinstance(item, list):
            item = item + ["'s"] + prop_key
        else:
            item = [item, "'s"] + prop_key
        sent = tqueries.change(tmp,
                               (self.agent, self.agent.describe(agent_desc_elems)),
                               rel='change',
                               thing_changing=item,
                               end_state=['to'] + new_val,
                               speaker=self.player)
        return sent

    def reset(self):
        super().reset()
        self.prop_key = None
        self.new_val = None

    def save_state(self):
        return super().save_state(), self.prop_key, self.new_val

    def recover_state(self, state):
        super().recover_state(state[0])
        self.prop_key, self.new_val = state[1], state[2]


class AndPolicy(UserPolicy):
    """ The policy for the user request:

            <player> says: <agent>, <request_1> and <request_2> and ... <request_n>

        where request_idx comes from executing each of the individual user policies
        in self.user_policies and extracting the inner sentence.
    """
    def __init__(self, player, user_policies=None, dialogue=None):
        super().__init__(player, dialogue)
        self.user_policies = list() if user_policies is None else user_policies

    def get_steps(self, **params):
        if len(self.user_policies) == 0 or None in self.user_policies:
            return None

        extract_sentences = []
        player_prev_utters = self.dialogue.get_player_utters(self.player)
        statement = None
        tmp = params.get("tmp", None)
        if len(player_prev_utters) < 1:
            for idx, pol in enumerate(self.user_policies):
                if idx != 0 or tmp is not None:
                    if tmp is None:
                        tmp = "then"
                    utter = pol.execute(tmp=tmp)
                else:
                    utter = pol.execute()
                if utter.describers[0].get_arg('Rel') == "says":
                    extract_sentences.append(utter.describers[0].get_arg('Arg-PPT'))
                    utter.speaker = self.player
            user_stat = tsentences.cont_and(extract_sentences, speaker=self.player)
            statement = tsentences.say(self.player, None, 'says',
                                       user_stat, speaker=self.player)

            self.reset()

        return statement

    def reset(self):
        del self.user_policies[:]

    def replace_dialogue(self, new_dialogue):
        self.dialogue = new_dialogue
        for pol in self.user_policies:
            pol.replace_dialogue(new_dialogue)

    def save_state(self):
        state_pol = []
        for pol in self.user_policies:
            state_pol.append(pol.save_state())
        return copy.copy(self.user_policies), state_pol

    def recover_state(self, state):
        del self.user_policies[:]
        self.user_policies.extend(state[0])
        for idx, pol in enumerate(self.user_policies):
            pol.recover_state(state[1][idx])


class IsItemPropertyPolicy(BaseItemPolicy):
    """ The policy for the user request:

            <player> says: <agent>, Is (a) <item> 's <property_key> <property_val>?

        For example, Andy says: Is the big person's name Andy?
    """
    def __init__(self, player, agent=None, item=None, property_key=None, property_val=None, dialogue=None):
        super().__init__(player, item, agent, dialogue)
        self.property_key = property_key
        self.property_val = property_val

    def generate_response(self, item, agent_desc_elems, tmp):

        if self.property_key is None or self.property_val is None:
            return None
        if isinstance(self.property_key, tuple):
            prop_key = list(self.property_key)
        else:
            prop_key = [self.property_key]

        topic = [item, "'s"] + prop_key

        if 'abstract' in item.attributes:
            topic.insert(0, 'a')

        statement = tqueries.be(tmp,
                                (self.agent, self.agent.describe(agent_desc_elems)),
                                topic,
                                "Is",
                                None,
                                self.property_val
                                )
        return statement

    def reset(self):
        super().reset()
        self.property_key = None
        self.property_val = None

    def save_state(self):
        return super().save_state(), self.property_key, self.property_val

    def recover_state(self, state):
        super().recover_state(state[0])
        self.property_key, self.property_val = state[1], state[2]


class IsItemAttributePolicy(BaseItemPolicy):
    """ The policy for the user request:
        <player> says: <agent>, Is (a) <item> <attribute>?
        For example, Andy says: Is the big person static?
    """
    def __init__(self, player, agent=None, item=None, attribute=None, dialogue=None):
        super().__init__(player, item, agent, dialogue)
        self.attribute = attribute

    def generate_response(self, item, agent_desc_elems, tmp):
        if self.attribute is None:
            return None

        topic = item

        if 'abstract' in item.attributes:
            topic = ['a', item]

        if isinstance(self.attribute, tuple):
            attr = list(self.attribute)
        else:
            attr = self.attribute

        statement = tqueries.be(tmp,
                                (self.agent, self.agent.describe(agent_desc_elems)),
                                topic,
                                "Is",
                                None,
                                attr
                                )
        return statement

    def reset(self):
        super().reset()
        self.attribute = None

    def save_state(self):
        return super().save_state(), self.attribute

    def recover_state(self, state):
        super().recover_state(state[0])
        self.attribute = state[1]

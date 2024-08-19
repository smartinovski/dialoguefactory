#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the policy interface and other base policies that are inherited by the agent/user policies.
"""
from abc import ABC, abstractmethod

from . import policies_helpers as phelpers
from ..language import sentences as tsentences
from . import goals as tgoals
from ..state import kn_checkers


class Policy(ABC):
    """
    This class sets up an interface that every policy should implement.

    Attributes
    ----------
    player : Entity, optional
        The player or agent that acts according to the policy. If None
        it is assumed that the environment responds.
    dialogue : Dialogue, optional
        The current dialogue that the policy is part of.
    """
    def __init__(self, player=None, dialogue=None):
        self.player = player
        self.dialogue = dialogue

    @abstractmethod
    def execute(self, include_goal=False, **params):
        """
        Runs the policy.

        Parameters
        ----------
        include_goal : bool
            If true, returns the goal. Otherwise, return only the steps.
        params : dict
            Additional parameters that might modify the behavior of the policy.

        Returns
        -------
        steps : list
            Since there can be more than one valid response in a specific context,
            the list of valid responses is returned.
        goal : Goal, optional
            The goal of the policy.
        """
        pass

    @abstractmethod
    def get_steps(self, **params):
        """ Returns the list of steps/valid utterances of the policy. This function can be useful if
            the steps are computed separately from the goal. """
        pass

    @abstractmethod
    def get_goal(self, **params):
        """ Returns the goal of the policy. This function can be useful if
            the goal is computed separately from the steps.
        """
        pass

    def replace_dialogue(self, new_dialogue):
        """ The dialogue is replaced when the policy is part of a new dialogue. """
        self.dialogue = new_dialogue

    def save_state(self):
        """ Since the same policy can change dialogues over time, the dialogue is returned. """
        return self.dialogue

    def recover_state(self, state):
        """ Recovers the dialogue in case it was changed over time. """
        self.replace_dialogue(state)


class BasePolicy(Policy, ABC):
    """ The base policy is used in cases where the user issues a request to an agent and
        the agent has to return an appropriate response.
    """

    @abstractmethod
    def parse(self, last_user_command):
        """ Extracts the parameters of the user request necessary to compute the agent's policy logic
            and implements the logic as well.

            Parameters
            ----------
            last_user_command : Sentence
                A user request sentence (queries.<x>) that does not mention the user. For example,
                     "Max, change the toy's color to red."
            Returns
            -------
            steps : list
                The list of valid responses.
            goal : Goal, optional
                The goal of the policy.

        """
        pass

    def execute(self, include_goal=False, say_last_user_command=None, **params):
        """
        Runs the policy.

        Parameters
        ----------
        include_goal : bool, optional
            Whether to include the policy's goal or not. The default is False.
        say_last_user_command : Sentence, optional
            A say sentence in the following format responses.say(queries.<x>). For example,
            "Jim says: Max, change the toy's color to red!"
            If this sentence is not provided, the first dialogue utterance is expected to be the user's request.

        Returns
        -------
        steps : list
            A list of valid responses.
        goal : Goal, optional
            The goal of the policy.
        """
        last_user_command = self.extract_inner_sentence(say_last_user_command)
        if last_user_command is not None:
            steps, goal = self.parse(last_user_command)
        else:
            steps, goal = None, None

        if include_goal:
            return steps, goal

        return steps

    def extract_inner_sentence(self, say_last_user_command=None):
        """
        Extract the inner sentence from the responses.say sentence.

        Parameters
        ----------
        say_last_user_command : Sentence, optional
            A say sentence in the following format responses.say(queries.<x>). For example,
            "Jim says: Max, change the toy's color to red."
            If it's not provided, the first dialogue utterance is expected to be the user's request.

        Returns
        -------
        last_user_command : Sentence
            The extracted inner sentence, if found. Otherwise, None is returned.

        """
        if not say_last_user_command:
            say_last_user_command = self.dialogue.utterances[0] if len(self.dialogue.utterances) > 0 else None

        last_user_command = phelpers.extract_inner_sent(say_last_user_command)
        if last_user_command is None or len(last_user_command.describers) > 1:
            return None
        describer = last_user_command.describers[0]
        player = describer.get_arg('AM-DIS')
        if player != self.player:
            return None
        return last_user_command

    def get_steps(self, **params):
        """ Returns the list of valid responses. """
        steps = self.execute(include_goal=False, **params)
        return steps

    def get_goal(self, **params):
        """ Returns the goal of the policy. """
        _, goal = self.execute(include_goal=True, **params)
        return goal


class ActionPolicy(BasePolicy, ABC):

    def __init__(self, player=None, go_location_policy=None, dialogue=None):
        super().__init__(player, dialogue)
        self.go_location_policy = go_location_policy
        self.item = None
        self.prev_user_command = None

    def one_task(self, item, neg_response, neg_res_func, last_user_command,  **task_params):
        """
        Runs the agent's policy for the following user request:

            <agent> <action> (preposition) a <item> <location>

        For example, "Max, look in a plastic container"

        The agent should accomplish the user request for one item that exists in the world
        and that fits the item's description provided by the user. This function calls self.task
        for each item that fits the description.

        In case the agent issues several steps but during the process
        it discovers that the action can not be done, then it should switch to another
        similar item. If the action is not possible for all the items that fit the description,
        then the neg_response should be outputted.

        Parameters
        ----------
        item : BaseEntity
            The item that describes the kind of object the agent should act upon. It contains
            the properties and attributes that describe the object. Additionally, it contains an 'abstract' attribute
            to indicate that it does not exist in the material world.
        neg_response : Sentence
            In case the action can not be achieved for all items in the world, a negative response (neg_response) is returned.
            An example is, "Hans can not get a big red item."
        neg_res_func : function
            A function that returns a negative response. For example, for the action get, this would be:
            <agent> can not get <object>. The neg_res_func requires only one argument because the <agent> is embedded
            in the sentence using self.player. This function is used to check if self.task returns a negative response.
        last_user_command : Sentence
            The last user request to the agent.
        **task_params : dict
            Additional policy-specific parameters that might be required for execution.

        Returns
        -------
        steps : list
            A list of valid responses.
        goal : Goal
            The goal is to check if the action is successful for at least one of the items in the world.

        """
        if self.prev_user_command is None or id(last_user_command) != id(self.prev_user_command):
            self.reset()
            self.prev_user_command = last_user_command
        similar_items = self.dialogue.dia_generator.world.query_entity_from_db(item)

        counter = 0
        neg_goals_counter = 0
        goals = []
        list_steps = []
        item_list = []
        say_neg_response = tsentences.say(self.player, None, 'says',
                                          neg_response, speaker=self.player)
        know_base = self.dialogue.dia_generator.knowledge_base
        new_similar_items = []
        for sitem in similar_items:
            result = True
            for elem in item.description.elements:
                if elem in sitem.properties and not kn_checkers.property_check_alt(know_base, sitem, elem, sitem.properties[elem], None):
                    result = False
                if elem != 'abstract' and elem in sitem.attributes and not kn_checkers.property_check_alt(know_base, sitem, None, elem, None):
                    result = False
            if result is True:
                new_similar_items.append(sitem)
        similar_items = new_similar_items
        for sitem in similar_items:
            steps, goal = self.task(item=sitem, **task_params)
            if not isinstance(steps, list):
                steps = [steps]
            neg_sent = neg_res_func(sitem)
            found_flag = phelpers.reduce_and_check_say(steps, neg_sent)
            if found_flag:
                counter += 1
                neg_goals_counter += 1
            else:
                if goal.func == tgoals.multiple_correct:
                    if len(goal.args) > 0:
                        goal_steps = goal.args[2]
                    elif "steps" in goal.kwargs:
                        goal_steps = goal.kwargs["steps"]
                    else:
                        goal_steps = []
                    if phelpers.reduce_and_check_say(goal_steps, neg_sent):
                        neg_goals_counter += 1
                goals.append(goal)
                list_steps.append(steps)
                item_list.append(sitem)

        if counter != len(similar_items):
            if neg_goals_counter == len(similar_items):
                goal = tgoals.Goal(tgoals.correct_steps_sublist, self.dialogue, self.player,
                                   [say_neg_response], len(self.dialogue.get_utterances()) - 1)
            else:
                goal = tgoals.Goal(tgoals.goal_or, goals)
            idx = None
            if self.item is not None:
                for item_idx, item_li in enumerate(item_list):
                    if item_li == self.item:
                        idx = item_idx
                        break

            if idx is None or self.item is None:
                idx = self.dialogue.random_gen.choice(range(len(list_steps)))
                self.item = item_list[idx]

            steps = list_steps[idx]
        else:
            steps = [say_neg_response]
            goal = tgoals.Goal(tgoals.correct_steps_sublist, self.dialogue, self.player,
                               steps, len(self.dialogue.get_utterances()) - 1)

        return steps, goal

    def reset(self):
        """ Reset the state that the policy modifies with time """
        if self.go_location_policy is not None:
            self.go_location_policy.reset()

        self.prev_user_command = None
        self.item = None

    def replace_dialogue(self, new_dialogue):
        """ Replace the dialogue with a new one.
            The GoLocation policy's dialogue is replaced as well.
        """
        super().replace_dialogue(new_dialogue)
        if self.go_location_policy is not None:
            self.go_location_policy.replace_dialogue(new_dialogue)

    def save_state(self):
        """ Save the state that the policy modifies with time """
        go_location_state = None
        if self.dialogue is not None:
            kb_state = self.dialogue.dia_generator.knowledge_base.save_state()
        else:
            kb_state = None
        if self.go_location_policy is not None:
            go_location_state = self.go_location_policy.save_state()

        return super().save_state(), go_location_state, self.item, self.prev_user_command, kb_state

    def recover_state(self, state):
        """ Recover the state that the policy modifies with time """
        super().recover_state(state[0])
        if state[1] is not None:
            self.go_location_policy.recover_state(state[1])
        self.item = state[2]
        self.prev_user_command = state[3]
        if self.dialogue is not None:
            self.dialogue.dia_generator.knowledge_base.recover_state(state[4])


class IsItem(ActionPolicy):
    @abstractmethod
    def parse(self, last_user_command):
        pass

    def one_task(self, item, is_not_res, neg_response, neg_res_func, last_user_command,  **task_params):
        """ The difference from the parent function is that here, there are two negative responses.
            One of them is when the agent does not know the answer (neg_response). The second one is when the
            answer is The <item> is not <attribute> or The <item>'s <prop_key> is not <prop_val> (is_not_res).

            Therefore, our algorithm for providing a response is the following:
                1. If the parent function returns "don't know" for all items, then the answer is "don't know".
                2. If it contains at least one positive response for one item, then return it.
                3. If it contains no positive answers but at least one negative response, "don't know",
                   then the answer is "don't know". The reason is that for some items where the information is not
                   available, the answer might be positive.
                4. If for all seen similar items, the answer is "is not", then the correct answer is "is not".
        """
        steps, goal = super().one_task(item, neg_response, neg_res_func, last_user_command,  **task_params)
        pos_steps = []
        if goal.func == tgoals.correct_steps_sublist:
            return steps, goal
        elif goal.func == tgoals.goal_or:
            if len(goal.args) > 0:
                goals = goal.args[0]
            elif "goals" in goal.kwargs:
                goals = goal.kwargs["goals"]
            else:
                goals = []
            count_neg = 0

            for goal in goals:
                if len(goal.args[2]) == 1:
                    inner_sent = goal.args[2][0].describers[0].get_arg('Arg-PPT')
                    if inner_sent.describers[0].get_arg('Rel', _type=0).infinitive == 'be':
                        if inner_sent.describers[0].get_arg('AM-NEG') is None:
                            pos_steps += goal.args[2]
                        else:
                            count_neg += 1
            if count_neg == len(goals) and count_neg > 0:
                steps = [tsentences.say(self.player,  None, "says", is_not_res, speaker=self.player)]
                goal = tgoals.Goal(tgoals.multiple_correct,
                                   self.dialogue,
                                   self.player,
                                   steps,
                                   len(self.dialogue.get_utterances()) - 1)
        if len(pos_steps) > 0:
            steps = pos_steps
            goal = tgoals.Goal(tgoals.multiple_correct,
                               self.dialogue,
                               self.player,
                               steps,
                               len(self.dialogue.get_utterances()) - 1)
        return steps, goal


class AutoPolicy(Policy):
    """
    This class allows the automatic selection of the right policies (in case there are multiple).
    The criterion for selection is if the policies output
    a response or a goal that is not None when executed.

    Attributes
    ----------
    list_policies : list
        A list of instances that inherit the Policy class.
    dialogue : Dialogue
        An instance of the class Dialogue.

    """

    def __init__(self, list_policies, dialogue):
        player = list_policies[0].player if len(list_policies) > 0 else None
        super().__init__(player, dialogue)
        self.list_policies = list_policies
        self.replace_dialogue(self.dialogue)

    def parse(self, **params):
        """ Iterates through all policies in the list_policies and
            returns the ones that outputs a step or a goal.
            If multiple policies output a valid response, then all the responses
            are returned and their goals are merged into one or_goal. """
        valid_res = []
        valid_goals = []
        for pol in self.list_policies:
            if self != pol:
                steps, goal = pol.execute(include_goal=True, **params)
                if steps is not None:
                    if isinstance(steps, list):
                        valid_res += steps
                    else:
                        valid_res.append(steps)
                if goal is not None:
                    valid_goals.append(goal)

        if len(valid_goals) > 1:
            valid_goal = tgoals.goal_or(valid_goals)
        elif len(valid_goals) == 1:
            valid_goal = valid_goals[0]

        if len(valid_res) == 0:
            valid_res = None
        if len(valid_goals) == 0:
            valid_goal = None

        return valid_res, valid_goal

    def execute(self, include_goal=False, **params):
        """
        Runs the policy.

        Parameters
        ----------
        include_goal : bool, optional
            Whether to include the goal of the policy. The default is False.
        **params : dict
            Additional parameters that some policies in self.list_policies
            might require.

        Returns
        -------
        steps : list
            The list of valid utterances.
        goal : Goal, optional
            The goal of the policy.

        """
        steps, goal = self.parse(**params)
        if include_goal:
            return steps, goal
        return steps

    def get_steps(self, **params):
        """ Returns the valid utterances of the policy. """
        steps = self.execute(include_goal=False, **params)
        return steps

    def get_goal(self, **params):
        """ Returns the goal of the policy. """
        _, goal = self.execute(include_goal=True, **params)
        return goal

    def reset(self):
        """ Reset all the policies in list_policies. """
        for pol in self.list_policies:
            if self != pol:
                pol.reset()

    def replace_dialogue(self, new_dialogue):
        """ Replaces the dialogue in the class and also the dialogue in all the policies
            that are part of the AutoPolicy. """
        self.dialogue = new_dialogue
        for pol in self.list_policies:
            if pol != self:
                pol.replace_dialogue(new_dialogue)

    def save_state(self):
        """ Save all the policies states in a list. """
        policies_state = []
        for pol in self.list_policies:
            if self != pol:
                policies_state.append(pol.save_state())
            else:
                policies_state.append(None)

        return policies_state

    def recover_state(self, policies_state):
        """ Recover all the policies' states from a list. """
        for idx, pol_state in enumerate(policies_state):
            pol = self.list_policies[idx]
            if self != pol:
                pol.recover_state(pol_state)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists all the classes that generate the goals of the dialogue.
"""
from ..policies import goals as tgoals


class GoalGenerator:
    """ A simple goal generator that generates the agent's goal (class goals.Goal).
        The agent's goal can change during the dialogue, so the goal generator is required.

        Attributes
        ----------
        policy : Policy
            The rule-based policy that returns the policy's goal.
    """
    def __init__(self, policy):
        self.policy = policy

    def execute(self):
        """ The current rule-based agent policies return the next player's utterance and their goal. We
            use the policy's get_goal function to fetch the goal.
        """
        return self.policy.get_goal()

    def replace_dialogue(self, new_dialogue):
        """ In case the policy is used in a different dialogue, this
            function allows replacing the dialogue.
        """
        self.policy.replace_dialogue(new_dialogue)

    def save_state(self):
        """ Saves the state of the goal generator by saving the policy state. """
        return self.policy.save_state()

    def recover_state(self, state):
        """ Recovers the state of the goal generator by recovering the policy state. """
        self.policy.recover_state(state)


class AndGoalGenerator:
    """ A class for generating the agent's goal for the following user request:

            <user> says: <user_request1> and <user_request2> and ...

         where the user_request is directed to the agent or other agents.
         For example, Andy says: John, go to the kitchen, and Andy, get the blue container from the bedroom.

        Attributes
        ----------
        list_policies : list
            The list of rule-based policies that return their goals.
    """
    def __init__(self, list_policies):
        self.list_policies = list_policies

    def execute(self):
        """ Returns the generated goal (class goals.Goal) by fetching the goals from the policies.
            The generated goal combines all agents' goals for the current user request.
            The goal is achieved if all the individual goals return value 1.
        """
        all_goals = []
        for pol in self.list_policies:
            goal = pol.get_goal()
            all_goals.append(goal)
        return tgoals.Goal(tgoals.goal_and, **{'goals': all_goals})

    def replace_dialogue(self, new_dialogue):
        """ In case the policies are used in another dialogue
            this function is used to update the dialogue in the policies.
        """
        for pol in self.list_policies:
            pol.replace_dialogue(new_dialogue)

    def save_state(self):
        """ Saves the state of all the policies because they are used for generating the goal.
        """
        state_policies = []
        for pol in self.list_policies:
            state_policies.append(pol.save_state())
        return state_policies

    def recover_state(self, state):
        """ Recovers the state of all the policies. """
        for idx, pol in enumerate(self.list_policies):
            self.list_policies[idx].recover_state(state[idx])

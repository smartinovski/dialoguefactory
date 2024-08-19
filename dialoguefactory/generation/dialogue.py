#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the Dialogue class, which controls the dialogue between one or more agents in the world.
"""

import copy
import random
import secrets
import logging

logger = logging.getLogger(__name__)


class Dialogue:
    """
    This class controls the dialogue between one or more participants.

    Attributes
    ----------
    random_seed : int
        The random seed is used to initialize the random generator.
        This seed is randomly selected for each new dialogue.
    random_gen : random.Random
        The random generator is seeded with the same seed before each run.
        It makes sure that the dialogue can be run again and will output the
        same utterances. For example, the environment can provide several responses,
        each of which can change the course of the dialogue.
        The random generator will select the same response each time the dialogue is run.
    dia_generator : DialogueGenerator
        This instance is responsible for generating dialogues and executing the dialogue utterances.
    policies : list
        The participants' policies. The policies should follow the base_policies.Policy interface.
    utterances : list
        The list of dialogue utterances uttered by the policies.
    curr_speaker : Entity
        The player whose policy is executed on the current turn.
    counter : int
        The number of turns taken in the dialogue. One turn is when all participants finish uttering.
    next_policy_id : int
        The id of the next policy to be executed. The id starts from 0 to len(self.policies)-1
    max_episode_length : int
        The maximum number of utterances the agent is allowed to take.
    goal_generator : Generator
        Generates the current dialogue's goal. Since the goal can change over time, there is a goal generator
        that generates a new goal after each utterance. There is a goal generator instead of a single goal
        due to the non-deterministic nature of the participant responses. For example, the user might decide to
        change the request, or the environment might have a list of valid responses
        that reveal different kinds of information, of which one is randomly selected.
    use_generator : bool
        The current rule-based policies return both the utterance and the goal of the agent. So it will be
        useful not to run the goal generator if the policy returns the same goal. If this field is False,
        the goal generator is not run. Otherwise, the goal generator is used.
    goal : Goal
        The goal of the dialogue.
    dialogue_over : bool
        True if the dialogue is finished. False if the dialogue is in progress.
    curr_reward : int
        The agent's reward. 0 means dialogue is still in progress, 1 success, and -1 failure.
    entities_descriptions : dict
        A dictionary with the key being an Entity and the value is the entity's Description.
        The entity's description is used whenever the entity appears in the dialogue.
    max_safety : int
        The max_safety is used to stop the dialogue just in case some rule-based policy goes into an infinite
        recursion. The default is 20 * (1 + 6) * 4 * 2. The calculation is described in the next few sentences.
        The number of items from the easy and hard environment (20)
        times the longest path between two points (including opening doors) plus one for executing the action. (1+6)
        This is considering actions like get <a> <item>.
        The agent might need to visit all items that match the same <a> <item> description. (4)
        So, we multiply the maximum number of similar items by 2 for safety.

    """
    def __init__(self, dia_generator=None, policies=None,
                 goal_generator=None, entities_descriptions=None):

        self.random_seed = secrets.randbelow(1_000_000_000)
        self.random_gen = random.Random(self.random_seed)
        self.dia_generator = dia_generator
        self.policies = policies if policies is not None else list()
        self.utterances = list()
        self.curr_speaker = None
        self.counter = 0
        self.next_policy_id = 0
        self.max_episode_length = None
        self.goal_generator = goal_generator
        self.use_generator = False
        self.goal = None
        self.dialogue_over = False
        self.curr_reward = 0
        self.entities_descriptions = dict() if entities_descriptions is None else entities_descriptions
        self.max_safety = 20 * (1 + 6) * 4 * 2

    def save_state(self):
        """ Saves the state of all class members that change with time """
        return (copy.copy(self.utterances),
                self.dia_generator.save_state(),
                copy.copy(self.policies),
                self.curr_speaker,
                self.counter,
                self.goal_generator.save_state(),
                self.goal,
                self.max_episode_length,
                [p.save_state() for p in self.policies],
                self.dialogue_over,
                self.curr_reward,
                self.next_policy_id,
                self.random_gen.getstate(),
                self.use_generator,
                copy.copy(self.entities_descriptions)
                )

    def recover_state(self, state):
        """ Recovers the state of all class members that change with time """
        del self.utterances[:]
        self.utterances.extend(state[0])
        self.dia_generator.recover_state(state[1])
        del self.policies[:]
        self.policies.extend(state[2])
        self.curr_speaker = state[3]
        self.counter = state[4]
        self.goal_generator.recover_state(state[5])
        self.goal = state[6]
        self.max_episode_length = state[7]
        for idx in range(len(self.policies)):
            pol = self.policies[idx]
            pol.recover_state(state[8][idx])
        self.dialogue_over = state[9]
        self.curr_reward = state[10]
        self.next_policy_id = state[11]
        self.random_gen.setstate(state[12])
        self.use_generator = state[13]
        self.entities_descriptions.clear()
        self.entities_descriptions.update(state[14])

    def reset_descriptions(self):
        """ Resets all the world's entities' descriptions and sets the predefined descriptions (in case they exist).
            It also updates the descriptions' random generator
            to make sure that the dialogue outputs the exact same utterances in case it is run again.
        """

        for obj in list(self.dia_generator.world.obj_list):
            obj.description = None

        for ent, desc in self.entities_descriptions.items():
            ent.description = desc

        for dobj in self.dia_generator.world.all_description_objects:
            dobj.random_gen = self.random_gen

        for obj in self.dia_generator.world.obj_list:
            obj.random_gen = self.random_gen

    def run(self, fake=False):
        """ Runs the dialogue by giving a turn to each of the participant policies
            in the order as they appear in the list self.policies. When all policies are executed,
            one cycle is complete.
        """
        if fake:
            state = self.save_state()
        all_results = []

        for pol in self.policies:
            pol.replace_dialogue(self)

        self.goal_generator.replace_dialogue(self)
        self.reset_descriptions()

        while True:
            result = self.step()
            all_results.append(result)
            if self.is_over():
                break
            if self.counter >= self.max_safety:
                break

        if fake:
            self.recover_state(state)
        return all_results

    def step(self):
        """
        Steps into the current policy and executes it.

        Returns
        -------
        obs : list
            List of observations/sentences that represent the environment response
            to the player's utterance.
        reward : int
            The reward that the player receives after uttering.
        dialogue_over : bool
            Indicates whether the dialogue is finished or still ongoing.
        info : dict
            Other information.

        """
        cycle_id = self.next_policy_id % len(self.policies)

        pol = self.policies[cycle_id]
        self.curr_speaker = pol.player

        try:
            if self.use_generator is False:
                utter, self.goal = pol.execute(include_goal=True)
            else:
                utter = pol.execute()
        except Exception as err:
            logger.error(err, exc_info=True)
            utter = None

        try:
            if self.use_generator is True:
                self.generate_new_goal()
        except Exception as err:
            logger.error(err, exc_info=True)

        if isinstance(utter, list):
            utter = self.random_gen.choice(utter)

        self.next_policy_id += 1

        (obs, reward, dialogue_over, info) = self.player_utters(utter)

        return obs, reward, dialogue_over, info

    def generate_new_goal(self, **params_replace):
        """ Generates new goal by executing the goal generator """
        self.goal = self.goal_generator.execute(**params_replace)
        return self.goal

    def player_utters(self, utter):
        """
        Updates the dialogue generator with the new utterance and returns:
        the utterance together with the environmental response, the reward for uttering,
        whether the dialogue is over, and other information. For more details, please check the step docstring.
        """
        if self.next_policy_id % len(self.policies) == 0:
            self.next_policy_id = 0
            self.counter += 1

        if utter is not None:
            obs = self.dia_generator.execute_utters([utter], self.random_gen)
            self.utterances += obs
        else:
            obs = None

        self.evaluate_goal()
        info = {}
        return obs, self.curr_reward, self.dialogue_over, info

    def is_over(self):
        """ Sets a flag whether the dialogue is over. The dialogue is over when the reward is 1 or -1 or when the
            counter exceeds the maximum episode length. All agents have to finish with their turns before the dialogue
            is over.
        """
        self.dialogue_over = (((self.counter >= self.max_episode_length if self.max_episode_length is not None else False)
                              or self.curr_reward == 1 or self.curr_reward == -1)
                              and self.next_policy_id == 0 and self.counter > 0)

        return self.dialogue_over

    def evaluate_goal(self):
        """
            Executes the current goal and sets the current reward.

            If the goal evaluates to 1, that indicates success, and the reward is set to 1.
            In case the dialogue is over and the goal is not a success,
            then the evaluation is set to -1 (failure).
        """
        if self.goal is None:
            return None
        result = self.goal.execute()
        if self.is_over() and result != 1:
            result = -1
        self.curr_reward = result

        return result

    def replace_player_policies(self, new_policies):
        """ Replaces the player policies with new ones.
            This function is useful when evaluating machine learning
            models because the agent's rule-based policy is replaced with the model-based.
        """
        old_policies = []
        counter = 0
        new_policy_player = new_policies[0].player
        for idx, pol in enumerate(self.policies):
            if pol.player == new_policy_player:
                old_policy = pol
                self.policies[idx] = new_policies[counter]
                self.policies[idx].replace_dialogue(self)
                counter += 1
                old_policies.append(old_policy)

        return old_policies

    def add_policies(self, policies):
        """ Adds agent policies to the dialogue. """
        for pol in policies:
            pol.replace_dialogue(self)
            self.policies.append(pol)

    def get_player_policies(self, player):
        """ Fetches all the policies that belong to a player. """
        policies = []
        for pol in self.policies:
            if pol.player == player:
                policies.append(pol)
        return policies

    def get_players(self):
        """ Fetches all the participants of the dialogue. """
        players = []
        for pol in self.policies:
            players.append(pol.player)
        return players

    def get_player_utters(self, player):
        """ Fetches all the utterances that belong to a player. """
        player_utters = []
        for utter in self.utterances:
            if utter.speaker == player:
                player_utters.append(utter)
        return player_utters

    def get_utterances(self):
        """ Gets the dialogue utterances. """
        return self.utterances

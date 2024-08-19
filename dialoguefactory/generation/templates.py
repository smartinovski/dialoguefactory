#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains functions called templates that generate different dialogue types.
"""
from ..policies import agent_policies
from ..policies import user_policies
from . import helpers

from . import dialogue as dia
from . import goal_generators as gen


def init_dialogue(dia_generator, user_policy, agent_policy, entities_descriptions=None):
    """
    Creates and initializes the dialogue.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The dialogue generator that was used to generate the dialogue.
    user_policy : UserPolicy
        The user policy. The user issues the request to the agent.
    agent_policy : AgentPolicy
        The agent's policy. The agent should satisfy the user's request.
    entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
        A description for each of the entities that are part of the dialogue.
        Each entity can have a different description.
        For example, the toy's container can be described as "the static red container" or "the red openable container".
        If left None, entities' descriptions will be automatically generated as the dialogue runs.

    Returns
    -------
    dialogue : Dialogue
        The initialized dialogue.

    """
    dialogue = dia.Dialogue(dia_generator, entities_descriptions=entities_descriptions)

    env_policy = dia_generator.env_auto_policy
    if env_policy is None:
        return None

    env_policy.replace_dialogue(dialogue)

    if agent_policy is None:
        return None

    dialogue.add_policies([user_policy, agent_policy])

    dialogue.goal_generator = gen.GoalGenerator(agent_policy)
    # To speed up things during execution. Check Dialogue.run for more.
    dialogue.use_generator = False

    return dialogue


def go_direction(dia_generator, user, agent, direction, entities_descriptions=None):
    """ Creates a dialogue between a user, an agent and the environment.
        The user issues a request to the agent in the following manner:

            <user> says: <agent> go <direction>

        The goal of the dialogue is for the agent to fulfill the user's request.

        Parameters
        ----------
        dia_generator : DialogueGenerator
            The class used for generating new dialogues.
        user : Entity
            The user that sends the request.
        agent : Entity
            The agent that needs to fulfill the user's request.
        direction : str
            The direction where the agent should go. For example: north, east, northeast ...
            The list of directions can be found in dia_generator.world.directions.
        entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
            A description for each of the entities that are part of the dialogue.
            Each entity can have a different description.
            For example, the toys container can be described as the static container or the red container.
            If left None, entities' descriptions will be automatically generated as the dialogue runs.

        Returns
        -------
        dialogue : Dialogue
            Returns the dialogue that is ready to be run.

    """
    user_policy = helpers.find_policy(dia_generator.user_policy_database[user],
                                      user_policies.GoDirectionPolicy
                                      )
    user_policy.agent = agent
    user_policy.direction = direction

    agent_policy = helpers.find_policy(dia_generator.agent_policy_database[agent],
                                       agent_policies.GoDirectionPolicy
                                       )

    dialogue = init_dialogue(dia_generator, user_policy, agent_policy,
                             entities_descriptions)

    return dialogue


def action_item(dia_generator, user, agent, user_pol_class, agent_pol_class,
                item, location=None, location_position=None,  entities_descriptions=None):
    """ Creates a dialogue between a user, an agent and the environment.
        The user issues a request using the user's policy to the agent in the following manner:

            <user> says: <agent> <action> (preposition) <item> <preposition> <location>

        For example:

            Jim says: John look in the toys container in the bedroom.

        In this case, the user_pol_class is user_policies.LookItemPolicy
        The goal of the dialogue is for the agent to fulfill the user's request by making several utterances.

        Parameters
        ----------
        dia_generator : DialogueGenerator
            The class used for generating new dialogues.
        user : Entity
            The user that issues the request.
        agent : Entity
            The agent that needs to fulfill the user's request.
        user_pol_class : type
            The class type that is used to create an instance of the user policy.
            The user policies can be found in the user_policies.py file.
        agent_pol_class : type
            The class type that is used to create an instance of the agent policy.
            The agent policies can be found in the agent_policies.py file.
        item : Entity
            The item that the agent acts upon.
        location : Entity, optional
            The supposed location of the item. It does not have to be the correct one.
        location_position : str, optional
            The preposition that refers to the location. For example. in, under or on.
        entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
            A description for each of the entities that are part of the dialogue.
            Each entity can have different description.
            For example, the toys container can be described as the static container or the red container.
            If left None, entities descriptions will be automatically generated as the dialogue runs.

        Returns
        -------
        dialogue : Dialogue
            Returns the dialogue that is ready to be run.
    """

    user_policy = helpers.find_policy(dia_generator.user_policy_database[user],
                                      user_pol_class
                                      )
    user_policy.item = item
    user_policy.agent = agent
    user_policy.location = location
    user_policy.location_position = location_position
    agent_policy = helpers.find_policy(dia_generator.agent_policy_database[agent],
                                       agent_pol_class
                                       )

    dialogue = init_dialogue(dia_generator, user_policy,
                             agent_policy, entities_descriptions)

    return dialogue


def change_prop(dia_generator, user, agent, item,
                property_key, property_val,  entities_descriptions=None):

    """ Creates a dialogue between a user, an agent and the environment.
        The user issues a request using the user's policy to the agent in the following manner:

            <user> says: <agent> change <item> 's <prop_key> to <prop_val>

        For example, "The captain says: fluffy, change the red container's color to green."
        The goal of the dialogue is the agent to fulfill the user's request.

        Parameters
        ----------
        dia_generator : DialogueGenerator
            The class used for generating new dialogues.
        user : Entity
            The user that issues the request.
        agent : Entity
            The agent that needs to fulfill the user's request.
        item : Entity
            The item that the agent wants to change the property.
        property_key : str
            The property of the item to be changed. For example, the item's nickname or color
        property_val : any
            The new property value. For example, honey (for nickname) or red (for color)
        entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
            A description for each of the entities that are part of the dialogue.
            Each entity can have different description.
            For example, the toys container can be described as the static container or the red container.
            If left None, entities descriptions will be automatically generated as the dialogue runs.

        Returns
        -------
        dialogue : Dialogue
            Returns the dialogue that is ready to be run.
    """

    user_policy = helpers.find_policy(dia_generator.user_policy_database[user],
                                      user_policies.ChangePropPolicy
                                      )
    user_policy.item = item
    user_policy.agent = agent
    user_policy.prop_key = property_key
    user_policy.new_val = property_val
    agent_policy = helpers.find_policy(dia_generator.agent_policy_database[agent],
                                       agent_policies.ChangePolicy
                                       )
    dialogue = init_dialogue(dia_generator, user_policy,
                             agent_policy, entities_descriptions)
    return dialogue


def is_item_property(dia_generator,
                     user,
                     agent,
                     item,
                     property_key,
                     property_val,
                     entities_descriptions=None):
    """
    Creates a dialogue between a user, an agent and the environment.
    The user issues a request using the user's policy to the agent in the following manner:

        <user> says: <agent>, Is <item> 's <property_key> <property_val>?

    For example, "the small person says: big person, Is the foods drawer's material wood?"
    The goal of the dialogue is the agent to fulfill the user's request.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The class used for generating new dialogues.
    user : Entity
        The user that issues the request.
    agent : Entity
        The agent that needs to fulfill the user's request.
    item : Entity
        The item that the user inquires about.
    property_key : str
        A item's property. For example: material, size, type
    property_val : any
        The property value that is checked if it's the correct one. For example: metal, small, ball
    entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
        A description for each of the entities that are part of the dialogue.
        Each entity can have different description.
        For example, the toys container can be described as the static container or the red container.
        If left None, entities descriptions will be automatically generated as the dialogue runs.

    Returns
    -------
    dialogue : Dialogue
        Returns the dialogue that is ready to be run.

    """

    user_policy = helpers.find_policy(dia_generator.user_policy_database[user],
                                      user_policies.IsItemPropertyPolicy
                                      )
    user_policy.agent = agent
    user_policy.item = item
    user_policy.property_key = property_key
    user_policy.property_val = property_val

    agent_policy = helpers.find_policy(dia_generator.agent_policy_database[agent],
                                       agent_policies.IsItemPolicy
                                       )

    dialogue = init_dialogue(dia_generator, user_policy,
                             agent_policy, entities_descriptions)

    return dialogue


def is_item_attribute(dia_generator,
                      user,
                      agent,
                      item,
                      attribute,
                      entities_descriptions=None):
    """
    Creates a dialogue between a user, an agent and the environment.
    The user issues a request using the user's policy to the agent in the following manner:

        <user> says: <agent>, Is <item> <attribute>?

    For example, "Hans says: Jim, Is the window static?"
    The goal of the dialogue is the agent to fulfill the user's request.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The class used for generating new dialogues.
    user : Entity
        The user that issues the request.
    agent : Entity
        The agent that needs to fulfill the user's request.
    item : Entity
        The item that the user inquires about.
    attribute : str
        The attribute that is checked.  
    entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
        A description for each of the entities that are part of the dialogue.
        Each entity can have different description.
        For example, the toys container can be described as the static container or the red container.
        If left None, entities descriptions will be automatically generated as the dialogue runs.

    Returns
    -------
    dialogue : Dialogue
        Returns the dialogue that is ready to be run.

    """
    user_policy = helpers.find_policy(dia_generator.user_policy_database[user],
                                      user_policies.IsItemAttributePolicy
                                      )
    user_policy.agent = agent
    user_policy.item = item
    user_policy.attribute = attribute

    agent_policy = helpers.find_policy(dia_generator.agent_policy_database[agent],
                                       agent_policies.IsItemAttributePolicy
                                       )

    dialogue = init_dialogue(dia_generator, user_policy,
                             agent_policy, entities_descriptions)

    return dialogue


def and_(dia_generator, user, any_template1, any_template2, entities_descriptions=None):
    """
    Creates a dialogue between a user (user) and multiple agents in the environment.
    The dialogue consists of the user first issuing a request and the agents fulfilling that request. The environment
    provides feedback after each utterance. Therefore, the environment is also part of the dialogue.
    The user issues the request in the following manner:

        <user> says : first <agent1> <do_task1> and then <agent2> <do_task2> and ...

    For example:

        Hannah says : first Andy open the door and then Jim change the red ball's color and then Andy go north

    The agents should utter in the order provided by the user.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The class used for generating new dialogues.
    user : Entity
        The user that sends the request.
    any_template1 : tuple (function, dict)
        Another template function and the parameters (kwargs) needed for the function.
    any_template2 : tuple (function, dict)
        The same description as any_template1.
    entities_descriptions : dict (:class:`~dialoguefactory.environment.entities.Entity` : :class:`~dialoguefactory.environment.descriptions.BaseDescription`)
        A description for each of the entities that are part of the dialogue.
        Each entity can have different description.
        For example, the toys container can be described as the static container or the red container.
        If left None, entities descriptions will be automatically generated as the dialogue runs.

    Returns
    -------
    dialogue : dialogue.Dialogue
        Returns the dialogue that is ready to be run.
    """
    (func1, params1) = any_template1
    (func2, params2) = any_template2

    dialogue = dia.Dialogue(dia_generator)

    if entities_descriptions is None:
        entities_descriptions = dialogue.entities_descriptions

    params1["entities_descriptions"] = entities_descriptions
    params2["entities_descriptions"] = entities_descriptions

    dialogue1 = func1(**params1)

    user_pol1 = helpers.make_dynamic_copy(dialogue1.policies[0])
    if dialogue1 is None:
        return None

    dialogue2 = func2(**params2)
    user_pol2 = helpers.make_dynamic_copy(dialogue2.policies[0])
    if dialogue2 is None:
        return None

    env_policy = dia_generator.env_auto_policy
    if env_policy is None:
        return None

    dialogue.env_policy = env_policy

    env_policy.replace_dialogue(dialogue)

    participants_policies = []
    for pol in dialogue1.policies[1:]+dialogue2.policies[1:]:
        pol1 = helpers.find_policy(dialogue.dia_generator.agent_policy_database[pol.player],
                                   agent_policies.AndPolicy
                                   )
        if pol1 not in participants_policies:
            participants_policies.append(pol1)

    user_pol = helpers.find_policy(dialogue.dia_generator.user_policy_database[user],
                                          user_policies.AndPolicy
                                          )

    user_pol.user_policies = [user_pol1, user_pol2]
    dialogue.add_policies([user_pol] + participants_policies)
    dialogue.goal_generator = gen.AndGoalGenerator(participants_policies)
    dialogue.use_generator = True

    return dialogue

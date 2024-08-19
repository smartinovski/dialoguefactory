#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists the dialogue goals that the goal generators generate.
"""


import inspect

from ..language import describers as tdescribers
from ..language import helpers as shelpers


class Goal:
    """
    This class represents the dialogue's goal.

    The execute function indicates the progress of the player towards the goal.
    Usually, it is a value ranging from 0 to 1, but it can also vary and can be
    used as a reward function.

    Attributes
    ----------
    func : function
        The goal is a function.
    args : tuple
        The positional arguments of the goal function.
    kwargs : dict
        The keyword arguments of the goal function.
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def execute(self, **params_replace):
        """ Executes the self.func with the stored parameters. If params_replace exists,
            it replaces the parameters just for the execution.
        """
        new_params = find_and_replace_params(self.func,
                                             self.args,
                                             self.kwargs,
                                             **params_replace)

        return self.func(**new_params)


def find_and_replace_params(func, args, kwargs, **params_replace):
    """
    Replaces the parameters found in args and kwargs with other set of params (params_replace).
    """
    new_params = {}
    signature = dict(inspect.signature(func).parameters)
    list_params = list(signature.keys())
    for key, val in signature.items():
        if val.default is not inspect.Parameter.empty:
            new_params[key] = val.default
    for idx, arg in enumerate(args):
        k = list_params[idx]
        new_params[k] = arg

    for key in kwargs.keys():
        new_params[key] = kwargs[key]

    for key, val in params_replace.items():
        if key in list_params:
            new_params[key] = val

    return new_params


def get_player_utters(dialogue, player, start_id):
    """
    Get all the player's utterances from the dialogue starting
    from a specific point in the dialogue.
    """
    dia_utterances = dialogue.get_utterances()[start_id:]
    player_prev_utterances = []
    for utter in dia_utterances:
        if utter.speaker == player:
            player_prev_utterances.append(utter)
    return player_prev_utterances


def correct_steps_sublist(dialogue, player, steps, start_id):
    """ Find if the steps are a sublist of the player utterances
    starting from a specific point in the dialogue. """
    player_utters = get_player_utters(dialogue, player, start_id)
    if is_sublist(player_utters, steps):
        return 1

    return 0


def is_sublist(_list, sub_list, eq_func=None):
    """ Checks whether the elements of the sub_list are part of the _list.
        The order of the elements is considered as well.

        The eq_func is a function with two parameters that defines their equality.
        The first parameter represents an element from the list and the second one an element
        from the sublist.
    """
    if eq_func is None:
        eq_func = lambda el1, el2: el1 == el2
    (i, j) = (0, 0)
    while i < len(_list) and j < len(sub_list):
        if eq_func(_list[i], sub_list[j]):
            j += 1
        i += 1
    return j == len(sub_list)


def multiple_correct(dialogue, player, steps, start_id):
    """ Finds if one of the steps is present in the player's
        utterances starting from a specific point in the dialogue.
    """
    player_utters = get_player_utters(dialogue, player, start_id)
    for step in steps:
        if step in player_utters:
            return 1

    return 0


def go_to_loc_goal(dialogue, player, location, start_id):
    """
    Checks if the player went to the target location starting from
    a specific point of time in the dialogue.
    """
    env_utterances = get_player_utters(dialogue, None, start_id)
    for utter in env_utterances:

        if len(utter.describers) != 0:
            desc = utter.describers[0]
            direction = desc.get_arg("AM-DIR")
            start_loc = desc.get_arg("Arg-DIR")
            desc_goes = tdescribers.go((player, None),
                                       (None, None),
                                       (None, None),
                                       ("goes", None),
                                       (direction, None),
                                       (start_loc, None))

            if desc_goes == desc and isinstance(direction, str) and start_loc[-1].properties[direction] == location:
                return 1

    return 0


def sent_in_reduced(dialogue, sent, player, start_id):
    """ Checks if the sentence is part of the reduced player utterances"""
    player_prev_utterances = get_player_utters(dialogue, player, start_id)
    if sent in shelpers.reduce_sentences(player_prev_utterances):
        return 1

    return 0


def goal_and(goals):
    """
    Checks if all the goals in the list return 1.
    If one of the goals is None or returns 0, then the
    final result is 0. Each of the goal types is
    data.goals.Goal
    """
    goal_res = []
    for goal in goals:
        if goal is not None:
            goal_res.append(goal.execute() == 1)
        else:
            goal_res.append(False)

    result = 0

    if len(goal_res) > 0 and all(goal_res):
        result = 1

    return result


def goal_or(goals):
    """
    Checks whether one of the goals returns 1. Each of the goal types is
    :class:`Goal <dialoguefactory.policies.goals.Goal>`

    """
    for goal in goals:
        if goal is not None:
            if goal.execute() == 1:
                return 1
    return 0

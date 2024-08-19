#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module introduces the functions needed for evaluating an agent's policy.
"""
import random

from ..generation import helpers


def generate_dialogue(dia_generator, agent, users, agent_prob=None, stat_type=None):
    """
    Generates a dialogue where the user issues a request to the agent.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The dialogue generator is used for generating the dialogue.
    agent : Entity
        The agent that receives a command from a user.
    users : list
        A list of users that can issue commands.
    agent_prob : float, optional
        The probability that the agent will participate in the generated dialogue.
        If the agent is not selected, then some random user will get a command from
        another user.
    stat_type : str, optional
        The type of the user utterance ('primitive' or 'complex').
        If None is provided, then the type is randomly taken from dia_generator.stat_types

    Returns
    -------
    Dialogue
        The generated dialogue.

    """
    if agent_prob is None:
        agent_prob = 1/(len(users)+1)

    rand_num = random.choices([0, 1], weights=[1-agent_prob, agent_prob], k=1)[0]
    if rand_num != 1:
        agent = random.choice(users)

    user = random.choice(users)

    if stat_type is None:
        count_prim = len(dia_generator.primitive_templates)
        count_complex = len(dia_generator.complex_templates)
        total_count = count_prim + count_complex
        stat_type = random.choices(['primitive', 'complex'],
                                  weights=[count_prim/total_count,
                                          count_complex/total_count], k=1)[0]
    if stat_type == 'primitive':
        structure_list = helpers.generate_primitive_structure(dia_generator.primitive_templates)
        default_args_list = [{"agent": agent,
                              "user": user}]
    else:
        structure_list = helpers.generate_complex_structure(dia_generator, 0)
        default_args_list = [dict() for _ in range(len(structure_list))]
        structure_primitive_ids = []
        for i in range(len(structure_list)):
            s = structure_list[i]
            if s[0] == 'primitive':
                structure_primitive_ids.append(i)
        random_id = random.choice(structure_primitive_ids)
        default_args_list[0] = {"user": user}
        default_args_list[random_id] = {"agent": agent, "user": user}
    out = dia_generator.generate_dialogue(template_type=stat_type, structure_list=structure_list,
                                          default_args_list=default_args_list)
    return out


def eval_dialogue(agent_policy, dialogue):
    """ Evaluates a dialogue by replacing the default rule-based policy with the agent_policy.
        But first, it checks whether the dialogue goal can be fulfilled with the rule-based policy.
    """

    result = None
    dialogue_players = dialogue.get_players()

    if agent_policy.player in dialogue_players:

        state = dialogue.save_state()

        dialogue.run()
        if dialogue.evaluate_goal() == 1:
            max_episode_len = dialogue.counter
            dialogue.recover_state(state)
            dialogue.max_episode_length = max_episode_len
            old_policies = dialogue.get_player_policies(agent_policy.player)
            dialogue.replace_player_policies([agent_policy]*len(old_policies))
            dialogue.use_generator = True

            dialogue.run()
            result = dialogue.evaluate_goal()
        else:
            dialogue.recover_state(state)

    return result


def eval_dialogues(agent_policy, dialogues, save_state=True):
    """
    Evaluates multiple dialogues using the eval_dialogue function.

    Parameters
    ----------
    agent_policy : Policy
        This policy replaces the rule-based policy in the dialogue.
    dialogues : list
        A list of Dialogue instances to be evaluated.
    save_state : bool, optional
        If True, it saves the dialogues' state and recovers it after the execution of the dialogues.
     
    Returns
    -------
    results : list
        The list of evaluated dialogues.

    """
    dialogues_states = []
    results = []
    for dia in dialogues:
        if not save_state:
            dialogues_states.append(dia.save_state())
        results.append(eval_dialogue(agent_policy, dia))

    if not save_state:
        for idx in range(len(dialogues_states)-1, -1, -1):
            dialogues[idx].recover_state(dialogues_states[idx])

    return results


def generate_and_eval(dia_generator, min_num_dialogues, min_agent_dialogues, agent_policy,
                      flush_after=None, agent_prob=None, forgetful=False, return_dias=False, notebook_run=False):
    """
    Generates a number of dialogues and evaluates
    how many of the generated dialogues are a success when using the agent_policy.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The object used for generating dialogues.
    min_num_dialogues : int
        The minimum number of dialogues to be generated.
    min_agent_dialogues : int
        The minimum number of dialogues to be generated where the agent participates in the dialogue.
    agent_policy : Policy
        The agent policy generates utterances in the dialogues.
    flush_after: int, optional
        It calls the dia_generator.flush() after the context reaches a certain length. It is done because
        the context size might grow large and not fit in RAM.
    agent_prob : float
        The probability that the player will be a participant and an agent in the next generated dialogue.
        The player is the owner of the agent_policy. The probability value ranges from 0 to 1.
    forgetful: bool, optional
        If True, it saves the dialogue state before the dialogue execution and later recovers the state.
        For example, a dialogue changes the context state when a player utters. Later, this change is reverted.
    return_dias: bool, optional
        If False, the generated dialogues are not returned. This might save RAM, otherwise all dialogues
        are appended to a list that may fill the RAM after some time.
    notebook_run : bool
        This parameter indicates whether the function is run from a jupyter notebook (True) or not (False).
        This parameter ensures the progress bars are shown correctly in a jupyter notebook.

    Returns
    -------
    dias : list
        The list of generated dialogues.
        The list contains all dialogues (including the ones where the agent is not a participant).
        If return_dias is False, an empty list is returned.
    individual_accuracies : dict
        The accuracy the agent has achieved per dialogue type.
    total_accuracy : int
        The number of successful dialogues where the agent participates divided by the total number of dialogues
        where the agent participates.
    total_num_dias : int
        The total number of dialogues generated where the agent participates.

    """
    if notebook_run:
        from tqdm.notebook import tqdm
    else:
        from tqdm import tqdm

    agent = agent_policy.player
    world = dia_generator.world
    other_agents = world.players
    other_agents = [p for p in other_agents if p != agent]

    dias = []
    d = 0
    ad = 0
    dialogues_states = []
    dia_type_success = dict()
    dia_type_total = dict()

    if min_num_dialogues is None:
        min_num_dialogues = 0

    if min_agent_dialogues is None:
        min_agent_dialogues = 0

    progress_bar_num = tqdm(total=min_num_dialogues, position=1)
    progress_bar_agent = tqdm(total=min_agent_dialogues, position=0)

    while d < min_num_dialogues or ad < min_agent_dialogues:

        dialogue = generate_dialogue(dia_generator, agent, other_agents, agent_prob)

        if dialogue is None:
            continue
        if forgetful:
            dialogues_states.append(dialogue.save_state())
        eval_result = eval_dialogue(agent_policy, dialogue)

        if eval_result is not None:
            ad += 1
            progress_bar_agent.update(1)
            update_acc_table(dia_type_success, dia_type_total, dialogue, eval_result)
        else:
            dialogue.run()
        if flush_after is not None and len(dia_generator.context) >= flush_after:
            dia_generator.flush()

        progress_bar_num.update(1)

        d += 1
        if return_dias or forgetful:
            dias.append(dialogue)

    progress_bar_agent.close()
    progress_bar_num.close()

    if forgetful:
        for idx in range(len(dialogues_states)-1, -1, -1):
            dias[idx].recover_state(dialogues_states[idx])

    individual_accuracies = {key: 100*val / dia_type_total[key] for key, val in dia_type_success.items()}
    total_num_dias = sum(dia_type_total.values())
    total_accuracy = 100*sum(dia_type_success.values())/total_num_dias
    return dias, individual_accuracies, total_accuracy, total_num_dias


def update_acc_table(dia_type_success, dia_type_total, dia, eval_result):
    """ Updates the number of successful dialogues per dialogue type and the total number of dialogues per type.

    Parameters
    ----------
    dia_type_success : dict
        A mapping from a dialogue type to the number of successful dialogues per dialogue type.
    dia_type_total : dict
        A mapping from a dialogue type to the number of total dialogues per dialogue type.
    dia : Dialogue
        The dialogue is used to fetch the user policy in order to get the dialogue type. The user request
        dictates the dialogue type. For example, the user request can be: Hannah get the apple or
        Hannah, Is the apple red?
    eval_result : int
        It indicates whether the dialogue was successful. A value of 1 indicates success.

    Returns
    -------
    None
    """
    dia_type = dia.policies[0].__class__.__name__.split("Policy")[0]

    if dia_type not in dia_type_total:
        dia_type_total[dia_type] = 0
    if dia_type not in dia_type_success:
        dia_type_success[dia_type] = 0

    dia_type_total[dia_type] += 1
    if eval_result == 1:
        dia_type_success[dia_type] += 1


def accuracy_dia_type(main_player, dias, eval_results):
    """
    Shows the accuracy for each dialogue type.
    The accuracy is computed by dividing the number of successful dialogues by the total number of dialogues.

    Parameters
    ----------
    main_player : Entity
        The agent that is trained.
    dias : list
        The list of dialogues that were evaluated.
    eval_results : list
        The results from the dialogues' evaluation.
        if eval_results[idx] is 1 means that the dialogue dias[idx] was successful.

    Returns
    ----------
    accuracies : list
        A list of tuples in the form: (dia_type, accuracy)
    """
    dia_type_total = dict()
    dia_type_success = dict()
    for idx, dia in enumerate(dias):
        dia_type = dia.policies[0].__class__.__name__.split("Policy")[0]
        if dia_type not in dia_type_total:
            dia_type_total[dia_type] = 0
        if dia_type not in dia_type_success:
            dia_type_success[dia_type] = 0

        dialogue_players = dia.get_players()
        if main_player in dialogue_players:
            dia_type_total[dia_type] += 1
            if eval_results[idx] == 1:
                dia_type_success[dia_type] += 1
    accuracies = [(key, str(val)+"/"+str(dia_type_total[key])+"="+str(val/dia_type_total[key])) for key, val in dia_type_success.items()]

    return accuracies


def pretty_print_eval(sol_name, individual_accuracies, total_accuracy, num_agent_dias, num_train_dias):
    """ Prints the metrics for the leaderboard.

        Parameters
        ----------
        sol_name : str
            The unique solution's name.
        individual_accuracies : dict
            A mapping task_name : task_accuracy.
        total_accuracy : int
            The accuracy across all tasks.
        num_agent_dias : int
            The number of dialogues used for computing the accuracies where the agent participates.
        num_train_dias : int
            The number of dialogues used for training the model where the agent participates.


        Returns
        ----------
        None

    """
    sorted_by_diff = ['IsItemAttribute', 'IsItemProperty', 'GoDirection',
                      'GoLocation', 'OpenItem', 'CloseItem', 'LookItem',
                      'DropItem', 'GetItem', 'ChangeProp', 'And']
    print("Sol. name: "+sol_name)
    string_acc = []
    for acc_name in sorted_by_diff:
        if acc_name in individual_accuracies:
            string_acc.append(acc_name + ": " + str(individual_accuracies[acc_name]))
        else:
            string_acc.append(acc_name + ": " + "NaN")
    print("The individual accuracies %: \n", "\n".join(string_acc))
    print("The total accuracy %", total_accuracy)
    print("The number of testing dialogues where the agent participates", num_agent_dias)
    print("The number of training dialogues where the agent participates", num_train_dias)

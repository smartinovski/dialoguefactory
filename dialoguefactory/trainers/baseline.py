#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module introduces classes and functions needed to implement the baseline model.
"""
import random
import logging
import inspect
import copy
import torch
from torch.nn import functional as F

from . import arch
from . import serializers
from . import evaluation as ev
from ..language import components as lc
from ..language import sentences as tsentences
from ..policies import base_policies as bp

logger = logging.getLogger(__name__)


def compute_voc(data):
    """ Finds the set of unique elements in a list of lists (data). """
    voc = []
    for elem in data:
        voc += elem

    voc = set(voc)
    voc = list(voc)

    return voc


def prepare_datapoint_x(datapoint_x):
    """ Takes all the string sentences from the context (datapoint_x) and extracts
        all the words (including the punctuation marks)
    """
    new_datapoint_x = []
    for sent_str in datapoint_x:
        new_datapoint_x += sent_str.split(' ')
    return new_datapoint_x


def dataset_split(data_x, data_y, train_len):
    """ Splits the data into training and validation data. The test data is not generated because
        the evaluation.generate_and_eval is used for evaluation.
    """
    train_data = data_x[0:train_len], data_y[0:train_len]
    val_data = data_x[train_len:], data_y[train_len:]

    return train_data, val_data


def generate_data(dia_generator, num_points, main_player, other_players, last_context_id=0, flush_after=None, notebook_run=False):
    """
    Generates (x,y) data points. The data points are generated by generating dialogues and running them.

    The data points are immediately serialized using the function
    :func:`serialize() <dialoguefactory.trainers.serializers.serialize>`
    because the entities' descriptions can be different in the dialogues that follow.

    Parameters
    ----------
    dia_generator : DialogueGenerator
        The dialogue generator.
    num_points : int
        The number of data points to be generated.
    main_player : Entity
        The agent to be trained.
    other_players : list
        A list of entities representing the players that are not trained.
    last_context_id : int, optional
        The index of the last sentence that the main agent has observed.
    flush_after : int
        The dialogue generator will be flushed in order not to fill the RAM with sentences.
        When flushing, the context sentences will be saved in a file (if a file is provided in the dia_generator).
    notebook_run : bool
        This parameter indicates whether the function is run from a jupyter notebook (True) or not (False).
        This parameter ensures the progress bars are shown correctly in a jupyter notebook.

    Returns
    -------
    data_x : list of lists
        Each list contains words (strings) from the context that the main_player
        has not observed yet (before providing a response).
    data_y : list of lists
        Each list contains the serialized response that the agent should give
        during a dialogue.
    last_context_id : int
        The updated index of the last sentence that the main agent has observed.
    num_dias : int
        The number of generated dialogues during the process of generating the data points.

    """
    data_x = []
    data_y = []
    num_dias = 0

    if notebook_run:
        from tqdm.notebook import tqdm
    else:
        from tqdm import tqdm

    progress_bar = tqdm(total=num_points)

    while True:
        out = ev.generate_dialogue(dia_generator, main_player, other_players)
        if out is None:
            continue
        dialogue = out
        players = dialogue.get_players()

        if main_player in players:
            num_dias += 1
            for p in dialogue.policies:
                p.replace_dialogue(dialogue)

            dialogue.goal_generator.replace_dialogue(dialogue)
            dialogue.reset_descriptions()
            while True:
                result = dialogue.step()
                (obs, reward, episode_over, info) = result
                if obs is not None:
                    step = obs[0]
                    if step.speaker == main_player:
                        context_window = dia_generator.context_strings[last_context_id:len(dia_generator.context_strings)-len(obs)]
                        data_x.append(prepare_datapoint_x(context_window))
                        data_y.append(serializers.serialize(step, dia_generator.world))
                        last_context_id = len(dia_generator.context_strings)-len(obs)
                        progress_bar.update(1)
                elif dialogue.curr_speaker == main_player:
                    # This branch will be executed in the _and template when the agent is waiting for its turn.
                    context_window = dia_generator.context_strings[last_context_id:]
                    data_x.append(prepare_datapoint_x(context_window))
                    desc = lc.Describer()
                    desc.args['Rel'] = lc.RelArg(None)
                    sent = lc.Sentence()
                    sent.describers = [desc]
                    data_y.append(serializers.serialize(sent, dia_generator.world))
                    progress_bar.update(1)
                if dialogue.is_over():
                    break
        else:
            dialogue.run()
        if flush_after is not None and len(dia_generator.context) >= flush_after:
            dia_generator.flush()
        if len(data_y) >= num_points:
            break

    return data_x, data_y, last_context_id, num_dias


def reconstruct_outputs(output, output_voc, database, speaker, world):
    """ Reconstructs the output from a list of indices to a Sentence """
    new_output = []
    for out in output:
        if out == output_voc.eos_ix:
            break
        new_output.append(out)
    output = new_output
    serialized = output_voc.to_text([output])
    unconverted = serializers.deserialize(serialized[0], world)
    if unconverted is not None:
        db_unconverted = database.query_sentence(unconverted.describers, speaker=speaker)
    else:
        db_unconverted = None
    return db_unconverted


class AgentPolicy(bp.Policy):
    """
    The agent's policy trained using the Seq2Seq continuous model.

    Attributes
    ----------
    player : Entity
        The agent.
    database : MapperDatabase
        The database is used to convert a list of Describer-s into a Sentence.
    model : Seq2SeqContModel
        The model that is used for training the agent.
    last_hid_state : torch.Tensor
        The last hidden state of the encoder. The encoder state is needed because the Seq2Seq model is continuous.
    last_context_id : int
        The index of the last sentence in the context that the model has seen.
    input_voc : Vocabulary
        The input vocabulary is used to convert the context words into indices before inputting
        them in the model
    output_voc : Vocabulary
        The output vocabulary is used to convert the indices back to strings.
    max_len : int
        The maximum number of output tokens.
    dialogue : Dialogue
        The dialogue that the AgentPolicy is part of.
    """

    def __init__(self, player, database, model, last_hid_state, last_context_id,
                 input_voc, output_voc, max_len, dialogue=None):
        super().__init__(player, dialogue)
        self.database = database
        self.model = model
        self.last_hid_state = last_hid_state
        self.last_context_id = last_context_id
        self.input_voc = input_voc
        self.output_voc = output_voc
        self.max_len = max_len

    def execute(self, include_goal=False, **params):
        """ Uses the model to utter a sentence. If there is an error in the policy, an empty sentence is returned. """
        context_window = self.dialogue.dia_generator.context_strings[self.last_context_id:]
        if len(context_window) == 0:
            return None
        state_text = [prepare_datapoint_x(context_window)]
        curr_context_int = self.input_voc.to_indices(state_text)[0]

        (outputs, _, self.last_hid_state) = self.model.translate(torch.LongTensor([curr_context_int]),
                                                                 self.last_hid_state,
                                                                 self.output_voc.bos_ix,
                                                                 self.input_voc.eos_ix,
                                                                 self.max_len, greedy=True)
        self.last_hid_state = self.last_hid_state.detach()
        self.last_context_id = len(self.dialogue.dia_generator.context_strings)
        outputs = [o.detach() for o in outputs]
        outputs = torch.stack(outputs, 0)

        outputs = outputs.detach().tolist()
        try:
            unconverted = reconstruct_outputs(outputs[0], self.output_voc, self.database,
                                              self.player, self.dialogue.dia_generator.world)
        except Exception as err:
            logger.error(err, exc_info=True)
            unconverted = lc.Sentence(speaker=self.player)
        if unconverted is not None:
            unconverted.trusted_source = False

        if include_goal is False:
            return unconverted
        return unconverted, None

    def get_steps(self, **params):
        """ Returns the list of valid responses. """
        steps = self.execute(include_goal=False, **params)
        return steps

    def get_goal(self, **params):
        """ Returns the goal of the policy. """
        return None

    def save_state(self):
        """ Saves the members that change with time when the dialogue is run. """
        return self.last_context_id, copy.deepcopy(self.last_hid_state)

    def recover_state(self, state):
        """ Recovers the members that change with time when the dialogue is run. """
        self.last_context_id = state[0]
        self.last_hid_state = state[1]


class RandomAgentPolicy(bp.Policy):
    """
    A policy that generates random sentences. This policy is used to test the dialogue generator.

    To generate a random sentence, a list of functions is used (self.sent_functions). In order to call the function,
    the function arguments need to be generated first. The arguments can be split into primitive and complex (they
    are explained below).
    A special type of argument is considered the Sentence type because some sentence functions like
    :func:`sentences.say() <dialoguefactory.language.sentences.say>`
    might contain other sentences as an argument.

    Attributes
    ----------
    vocab_words : list
        The list of all words that can possibly appear in the context.
    primitive_arguments : list
        Primitive arguments refer to types that can not contain other types inside them.
    complex_arguments : list
        The complex arguments can contain both primitive and/or complex argument types inside them.
    max_argument_depth : int
        The depth of the complex argument. For example, if the complex argument is a list, a list of lists
        will have depth 1. A shallow list has a depth of zero.
        The depth also refers to how many embedded sentences the type Sentence can have
        since sentences can contain other sentences like (say() or permit()).
    max_argument_len : int
        The maximum length of the elements that the complex argument contains.
    sent_functions : list of functions
        A list of templates that are used for generating the sentences.
    dialogue : Dialogue
        The dialogue that the RandomAgentPolicy is part of.
    player : Entity
        The agent that utters the random sentences.
    """
    def __init__(self, vocab_words, primitive_arguments=None, complex_arguments=None,
                 max_argument_depth=0, max_argument_len=6, sent_functions=None, dialogue=None, player=None):
        super().__init__(player, dialogue)
        self.vocab_words = vocab_words
        self.primitive_arguments = ['string', 'entity'] if primitive_arguments is None else primitive_arguments
        self.complex_arguments = ['list'] if complex_arguments is None else complex_arguments
        self.max_argument_depth = max_argument_depth
        self.max_argument_len = max_argument_len
        self.sent_functions = [tsentences.go,
                               tsentences.say,
                               tsentences.get,
                               tsentences.see,
                               tsentences.look,
                               tsentences.permit,
                               tsentences.have,
                               tsentences.reveal,
                               tsentences.be,
                               tsentences.know,
                               tsentences.opens,
                               tsentences.close,
                               tsentences.tries,
                               ] if sent_functions is None else sent_functions

    def execute(self, include_goal=False, **params):
        """ Returns the randomly generated sentence. """
        if include_goal is False:
            return self.generate_sentence()
        return self.generate_sentence(), None

    def generate_argument(self, arg_type, depth=0):
        """ Generates an argument that will be used to call a function.

            In addition to the primitive and complex arguments generated here, the sentence construct is added since
            there are some sentences like say() that contain other sentences as arguments.
        """
        if arg_type in self.primitive_arguments:
            construct = self.generate_primitive_argument(arg_type)
        else:
            param_len = random.randint(1, self.max_argument_len)
            list_elements = []
            for _ in range(param_len):
                sub_arg_type = random.choice(self.primitive_arguments+self.complex_arguments+['sentence'])
                if sub_arg_type == 'sentence':
                    if depth < self.max_argument_depth:
                        construct = self.generate_sentence(depth+1)
                    else:
                        new_arg_type = random.choice(self.primitive_arguments+self.complex_arguments)
                        construct = self.generate_argument(new_arg_type, depth+1)
                else:
                    construct = self.generate_primitive_argument(sub_arg_type)
                list_elements.append(construct)

            construct = list_elements

        return construct

    def generate_sentence(self, depth=0):
        """ Selects a sentence function randomly from the list of functions (self.sent_functions). It
            generates the arguments for the sentence and calls the function with the generated arguments.
        """
        sent_func = random.choice(self.sent_functions)
        params = dict(inspect.signature(sent_func).parameters)

        new_params = {}
        for key in list(params.keys()):
            if key not in ['speaker', 'rel']:
                arg_type = random.choice(self.primitive_arguments + self.complex_arguments+['sentence'])
                if arg_type == 'sentence':
                    if depth < self.max_argument_depth:
                        construct = self.generate_sentence(depth+1)
                    else:
                        construct = self.generate_argument(random.choice(self.primitive_arguments+self.complex_arguments), depth)
                else:
                    construct = self.generate_argument(arg_type, depth)
                new_params[key] = construct
        new_params['rel'] = sent_func.__name__
        new_params['speaker'] = self.player
        sent = sent_func(**new_params)
        return sent

    def generate_primitive_argument(self, arg_type):
        """ Generates a primitive argument. """
        result = None
        if arg_type == 'string':
            result = random.choice(self.vocab_words)
        elif arg_type == 'entity':
            result = random.choice(self.dialogue.dia_generator.world.obj_list)
        return result

    def get_steps(self, **params):
        """ Returns the list of valid responses. """
        steps = self.execute(include_goal=False, **params)
        return steps

    def get_goal(self, **params):
        """ Returns the goal of the policy. """
        return None

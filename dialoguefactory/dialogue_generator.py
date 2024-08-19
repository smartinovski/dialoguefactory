#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the class for generating dialogues.
"""

import inspect
import copy
import random
from functools import partial
import logging

from dialoguefactory.generation import templates
from dialoguefactory.state import knowledge_base as kb
from dialoguefactory.policies import agent_policies, env_policies
from dialoguefactory.policies import base_policies as bpolicies
from dialoguefactory.policies import user_policies
from dialoguefactory.generation import helpers
from dialoguefactory.generation import file_list_db as fdb
from dialoguefactory.generation import param_generators as pg

logger = logging.getLogger(__name__)


class DialogueGenerator:
    """
    This class contains all the components needed to generate/simulate dialogues.

    Here is an example of how to quickly generate a dialogue:

    ..  code-block:: python

        easy_world = easy_env.build_world()
        generator = DialogueGenerator(easy_world, "error.log", "context_sentences.txt")
        dialogue = generator.generate_dialogue()
        dialogue.run()


    Attributes
    ----------
    world : World
        The world where the simulation occurs.
    context_strings : ContextListDb
        The list where all dialogue utterances, including the environmental feedback, are stored in a string form.
    context : ContextListDb
        The list of instances (type Sentence) where all dialogue utterances, including the environmental feedback,
        are stored.
    meta_context : ContextListDb
        This list is used to save all additional information that is carried
        by the uttered sentences. Please check lc.Phrase for more information about the meta sentences.
    knowledge_base: KnowledgeBase
        The knowledge base stores additional information, and it is used in rule-based policies to quickly
        fetch information. It is updated each time an agent utters.
    primitive_templates : list
        A list of functions that are used to generate the primitive dialogues.
    complex_templates : list
        A list of functions that are used to generate complex dialogues.
        These functions contain both primitive and complex template functions as parameters.
    primitive_template_names : list
        In the case of a complex template, the primitive templates appear as function parameters. This list contains all
        the templates' names that appear as function parameters.
    complex_template_names : list
        In the case of a complex template, other complex templates can appear as function parameters.
        This list contains all the templates' names that appear as function parameters.
    any_template_names : list
        In the case of a complex template, both primitive and complex templates can appear as function parameters.
        This list consists of all parameter names that indicate either a primitive or a complex template.
        For example, such parameter names can be found in the current template templates.AndPolicy
    curr_prim_params : dict
        This field serves as a temporary memory to hold all primitive template parameters while they are generated.
        This field is helpful in case the generation of parameterA depends on the generation of another parameterB.
        The parameterA generator can fetch the value of parameterB using curr_prim_params["parameterB"]
        After the primitive template is generated this dictionary is cleared.
    curr_complex_params : dict
        This field serves as a temporary memory to hold all complex template parameters while they are generated.
        This field is helpful in case the generation of parameterA depends on the generation of another parameterB.
        The parameterA generator can fetch the value of parameterB using curr_complex_params["parameterB"]
        After the complex template is generated this dictionary is cleared.
    prim_param_generators : list
        A list of tuples (param_name, function).
        The function generates a random parameter value for the primitive templates.
    complex_param_generators : list
        A list of tuples (param_name, function).
        The function generates a random parameter value for the complex templates.
    agent_policy_database : dict
        A dictionary that maps each agent (Entity) to all of its policies (list). The agent is the one who fulfills
        the user's requests.
    user_policy_database : dict
        A dictionary that maps each user (Entity) to all of its policies (list). The user issues the requests
        to the agent.
    agent_auto_policy_database : dict
        A dictionary that maps each agent (Entity) to all of its policies.AutoPolicy policies (list).
    user_auto_policy_database : dict
        A dictionary that maps each user (Entity) to all of its policies.AutoPolicy policies (list).
    env_policy_database : list
        A list of all environmental policies.
    env_auto_policy : EnvAutoPolicy
        The environment automatic policy automatically selects the right policy
        from the environment database when an agent utters. Once selected, it provides feedback
        to the agent.

    """
    def __init__(self,
                 world,
                 log_filename,
                 context_strings_filename=None,
                 primitive_templates=None,
                 complex_templates=None,
                 primitive_template_names=None,
                 complex_template_names=None,
                 any_template_names=None
                 ):
        self.world = world
        helpers.configure_logging(log_filename, format_="%(asctime)s:%(name)s:%(funcName)s:%(levelname)s - %(message)s")
        self.context_strings = fdb.StringListDb(file_name=context_strings_filename)
        self.context = fdb.ListDb()
        self.meta_context = fdb.ListDb()
        self.knowledge_base = kb.KnowledgeBase(self.meta_context, self.world)

        if primitive_templates is not None:
            self.primitive_templates = primitive_templates
        else:
            self.primitive_templates = [templates.go_direction,
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.GoLocationPolicy,
                                                agent_pol_class=agent_policies.GoLocationPolicy),
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.GetItemPolicy,
                                                agent_pol_class=agent_policies.GetItemPolicy
                                                ),
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.DropItemPolicy,
                                                agent_pol_class=agent_policies.DropItemPolicy),
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.LookItemPolicy,
                                                agent_pol_class=agent_policies.LookItemPolicy),
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.OpenItemPolicy,
                                                agent_pol_class=agent_policies.OpenCloseItemPolicy
                                                ),
                                        partial(templates.action_item,
                                                user_pol_class=user_policies.CloseItemPolicy,
                                                agent_pol_class=agent_policies.OpenCloseItemPolicy),
                                        templates.change_prop,
                                        templates.is_item_property,
                                        templates.is_item_attribute
                                        ]
        if complex_templates is None:
            self.complex_templates = [templates.and_]
        else:
            self.complex_templates = complex_templates

        self.primitive_template_names = ['primitive_template'] if primitive_template_names is None else primitive_template_names
        self.complex_template_names = ['complex_template'] if complex_template_names is None else complex_template_names
        self.any_template_names = ['any_template'] if any_template_names is None else any_template_names

        self.curr_prim_params = dict()
        self.curr_complex_params = dict()

        self.prim_param_generators = list()
        self.complex_param_generators = list()

        self.init_param_generators()

        self.agent_policy_database = dict()
        self.init_agent_policy_db(self.world.players)

        self.user_policy_database = dict()
        self.init_user_policy_db(self.world.players)

        self.agent_auto_policy_database = dict()
        self.init_agent_auto_policy_db(self.world.players)

        self.user_auto_policy_database = dict()
        self.init_user_auto_policy_db(self.world.players)

        self.env_policy_database = list()
        self.init_env_policy_db()

        self.env_auto_policy = env_policies.EnvAutoPolicy(self.env_policy_database, None)

    def init_param_generators(self):
        """ Initializes the parameter generators for the primitive and complex templates.
        """

        self.prim_param_generators += [("world", partial(getattr, self, "world")),
                                       ("determiner_a", partial(random.choice, [False, True])),
                                       ("item", partial(pg.random_item, self.curr_prim_params)),
                                       ("candidate_property_keys", partial(pg.candidate_prop_keys,
                                                                           self.curr_prim_params)),
                                       ("location", partial(pg.random_location, self.curr_prim_params)),

                                       ("direction", partial(pg.random_world_list, self.curr_prim_params,
                                                             "directions")),
                                       ("property_key", partial(pg.random_param_value, self.curr_prim_params,
                                                                "candidate_property_keys")),
                                       ("property_val",
                                        partial(pg.random_property_val, self, self.curr_prim_params)),
                                       ("attribute", partial(pg.random_attribute, self.curr_prim_params)),
                                       ("user", partial(pg.random_user, self.curr_prim_params)),
                                       ("agent", partial(pg.random_world_list, self.curr_prim_params,
                                                                  "players")),
                                       ("location_position", partial(pg.random_world_list, self.curr_prim_params,
                                                                     "location_positions")),
                                       ("dia_generator", lambda ent=self: ent)
                                       ]
        self.complex_param_generators += [("world", partial(getattr, self, "world")),
                                          ("user", partial(pg.random_user, self.curr_complex_params)),
                                          ("dia_generator", lambda ent=self: ent)
                                          ]

    def init_agent_policy_db(self, players):
        """
        Initializes all individual policies for the specified agents (players) in the world.
        The dialogue at this stage is None.
        """
        for player in players:
            self.agent_policy_database[player] = [
                agent_policies.AndPolicy(player),
                agent_policies.GoDirectionPolicy(player),
                agent_policies.IsItemPolicy(player),
                agent_policies.IsItemAttributePolicy(player),
                ]

            go_dir_policy = helpers.find_policy(self.agent_policy_database[player],
                                                agent_policies.GoDirectionPolicy)

            self.agent_policy_database[player] += [agent_policies.GoLocationPolicy(go_dir_policy, player)]

        for player in players:
            go_loc_policy = helpers.find_policy(self.agent_policy_database[player],
                                                agent_policies.GoLocationPolicy)
            self.agent_policy_database[player] += [
                agent_policies.GetItemPolicy(player, go_loc_policy),
                agent_policies.DropItemPolicy(player, go_loc_policy),
                agent_policies.LookItemPolicy(player, go_loc_policy),
                agent_policies.OpenCloseItemPolicy(player, go_loc_policy)]
            get_policy = helpers.find_policy(self.agent_policy_database[player],
                                             agent_policies.GetItemPolicy
                                             )
            self.agent_policy_database[player] += [agent_policies.ChangePolicy(player, get_policy)]

    def init_user_policy_db(self, players):
        """
        Initializes all individual policies for the specified users (players) in the world.
        The dialogue at this stage is None.
        """
        for player in players:
            self.user_policy_database[player] = [user_policies.GoDirectionPolicy(player),
                                                 user_policies.GoLocationPolicy(player),
                                                 user_policies.GetItemPolicy(player),
                                                 user_policies.DropItemPolicy(player),
                                                 user_policies.LookItemPolicy(player),
                                                 user_policies.OpenItemPolicy(player),
                                                 user_policies.CloseItemPolicy(player),
                                                 user_policies.ChangePropPolicy(player),
                                                 user_policies.AndPolicy(player),
                                                 user_policies.IsItemPropertyPolicy(player),
                                                 user_policies.IsItemAttributePolicy(player)]

    def init_agent_auto_policy_db(self, players):
        """
        Initializes all the auto policies for each agent in the agents (players) list.
        """
        for player in players:
            auto_policy = bpolicies.AutoPolicy(self.agent_policy_database[player], None)
            self.agent_auto_policy_database[player] = auto_policy

    def init_user_auto_policy_db(self, players):
        """
        Initialize all the auto policies for each user in the users (players) list.
        """
        for player in players:
            auto_policy = bpolicies.AutoPolicy(self.user_policy_database[player], None)
            self.user_auto_policy_database[player] = auto_policy

    def init_env_policy_db(self):
        """
        Initializes all environment policies.
        """
        self.env_policy_database = [env_policies.GoPolicy(),
                                    env_policies.GetPolicy(),
                                    env_policies.SayPolicy(),
                                    env_policies.DropPolicy(),
                                    env_policies.LookPolicy(),
                                    env_policies.OpenClosePolicy(),
                                    env_policies.ChangePolicy(),
                                    env_policies.EmptyPolicy()
                                    ]

    def save_state(self):
        """
        Saves the state of all class members that change with time.
        """
        state_context_strings = self.context_strings.save_state()
        state_context = self.context.save_state()
        state_meta_context = self.meta_context.save_state()
        agent_state_policies = dict()
        for player, pol in self.agent_auto_policy_database.items():
            agent_state_policies[player] = pol.save_state()
        env_state = self.env_auto_policy.save_state()

        return state_context_strings, state_context, state_meta_context, agent_state_policies, env_state

    def recover_state(self, state):
        """
        Recovers the state of all class members that change with time.
        """
        (state_context_strings, state_context, state_meta_context, state_policies, env_state) = state
        self.context_strings.recover_state(state_context_strings)
        self.context.recover_state(state_context)
        self.meta_context.recover_state(state_meta_context)

        for player, pol in self.agent_auto_policy_database.items():
            pol.recover_state(state_policies[player])
        self.env_auto_policy.recover_state(env_state)

    def select_complex_template(self, structure_list, structure_id, default_args_list=None):
        """
        Generates a complex template based on the structure list.
        Please read more in the documentation of helpers.generate_complex_structure.

        Parameters
        ----------
        structure_list : list
            A list of tuples in the format ("primitive", template_func) or
            ("complex", template_func, num_templates)
        structure_id : int
            A pointer that indicates which one is the next template inside
            the structure list.
        default_args_list : list, optional
            List of dictionaries. Each dictionary functions as kwargs i.e.
            holds the parameter keys and values for each template in the
            structure list.

        Returns
        -------
        template_rand : function
            A function that creates an instance of Dialogue.
        new_params_list : list
            The list of generated parameters for the template_rand
            function.

        """
        if default_args_list is None:
            default_args_list = list()
            for idx in range(structure_id, len(structure_list), 1):
                default_args_list.append(dict())
        template_rand = structure_list[structure_id][1]
        params = dict(inspect.signature(template_rand).parameters)

        default_args_keys = list(default_args_list[structure_id].keys())
        self.curr_complex_params.clear()
        for gen in self.complex_param_generators:
            if gen[0] not in default_args_keys:
                self.curr_complex_params[gen[0]] = gen[1]()
            else:
                self.curr_complex_params[gen[0]] = default_args_list[structure_id][gen[0]]

        other_params = copy.copy(self.curr_complex_params)
        structure_id += 1
        new_params_list = {}
        for key in list(params.keys()):
            if key in other_params:
                new_params_list[key] = other_params[key]
            elif any(list(map(key.startswith, self.primitive_template_names))):
                template, params = self.select_primitive_template([structure_list[structure_id][1]],
                                                                  default_args_list[structure_id])
                new_params_list[key] = template, params
                structure_id += 1
            elif (any(list(map(key.startswith, self.any_template_names))) or
                  any(list(map(key.startswith, self.complex_template_names)))):
                if structure_list[structure_id][0] == 'primitive':
                    template, params = self.select_primitive_template([structure_list[structure_id][1]],
                                                                      default_args_list[structure_id])
                    new_params_list[key] = template, params
                    structure_id += 1
                else:
                    template, params = self.select_complex_template(structure_list,
                                                                    structure_id,
                                                                    default_args_list)
                    structure_id = structure_id + structure_list[structure_id][2] + 1
                    new_params_list[key] = template, params
        return template_rand, new_params_list

    def select_primitive_template(self, templates_list, default_args=None):
        """
        Selects a primitive template, and it randomly generates its parameters.

        When creating the user request, if the parameter determiner_a is True, this means that
        the item is not concrete, i.e. it does not belong to a specific item in the world.
        For example, a big red ball. Therefore, an abstract item is used (a BaseEntity with an attribute "abstract").
        If the determiner_a is False, a concrete Entity is taken from the world's object list.

        Parameters
        ----------
        templates_list : list
            The list of templates (functions) from which one is randomly selected.

        default_args : dict, optional
            This dictionary is used for overriding the default random
            generation of parameters. The default is None.

        Returns
        -------
        template_rand : function
            The randomly selected template.
        params : dict
            The generated parameters for the template.

        """
        if default_args is None:
            default_args = dict()
        # run the generators here
        default_args_keys = list(default_args.keys())
        self.curr_prim_params.clear()
        for gen in self.prim_param_generators:
            if gen[0] not in default_args_keys:
                self.curr_prim_params[gen[0]] = gen[1]()
            else:
                self.curr_prim_params[gen[0]] = default_args[gen[0]]

        template_rand = random.choice(templates_list)
        params = dict(inspect.signature(template_rand).parameters)
        for key in list(params.keys()):
            if key in self.curr_prim_params:
                params[key] = self.curr_prim_params[key]
            else:
                del params[key]

        return template_rand, params

    def execute_utters(self, utterances, random_gen=None, fake=False, skip_env=False):
        """
        Adds the agent/user utterances to the context, to the meta_context, and
        it updates the knowledge base. Moreover, the env_policy is executed
        so the environment can provide feedback to each of the utterances.

        This function is used by the Dialogue class.


        Parameters
        ----------
        utterances : list
            The list of utterances to be executed.
        random_gen : random.Random
            The random generator used for randomly selecting a valid response from the environmental feedback.
            It makes the Dialogue reproducible.
        fake : bool, optional
            If True the dia_generator state is not updated with the new
            information.
        skip_env : bool, optional
            If True the env_policy is not executed.
        Returns
        -------
        responses : list
            The list of players' utterances, including the environment's responses.

        """
        if fake:
            state = self.save_state()

        responses = []

        for utter in utterances:
            utter_str = utter.to_string()

            if utter is not None and utter_str.strip():
                copied_utter = self.context.add([utter])
                self.context_strings.add([utter_str])
                responses += copied_utter
                self.meta_context.add(helpers.reduce_and_extract(copied_utter, add_original=True), serialize=False)
                self.knowledge_base.context_update()

            if not skip_env:

                res = self.env_auto_policy.execute(last_utter=utter)
                if isinstance(res, list):
                    if random_gen is None:
                        random_gen = random.Random()
                    res = [random_gen.choice(res)]
                else:
                    res = [res]
                new_res = []
                for sent in res:
                    str_sent = sent.to_string()
                    if str_sent.strip():
                        self.context_strings.add([str_sent])
                        new_res.append(sent)

                res_serialized = self.context.add(new_res)
                responses += res_serialized
                self.meta_context.add(helpers.reduce_and_extract(new_res, add_original=True), serialize=False)
                self.knowledge_base.context_update()

        if fake:
            self.recover_state(state)

        return responses

    def generate_dialogue(self,
                          template_type=None,
                          structure_list=None,
                          default_args_list=None,
                          max_depth=5):
        """
        Generates a single dialogue.

        Parameters
        ----------
        template_type: str, optional
            The template type can be either primitive or complex.
        structure_list: list, optional
            If the template type is complex, the structure list contains both primitive and complex templates
            that appear as parameters in another complex template.
            If the template type is primitive, the structure_list consists of a single tuple.
            More information can be found on helpers.generate_complex_structure
            and helpers.generate_primitive_structure
        default_args_list : list, optional
            List of dictionaries that match the length of the structure list.
            The default is None.
        max_depth : int, optional
            The maximum depth for the complex template. The default is 2.

        Returns
        -------
        Dialogue
            The generated dialogue.

        """
        if template_type is None:
            count_prim = len(self.primitive_templates)
            count_complex = len(self.complex_templates)
            total_count = count_prim + count_complex
            template_type = random.choices(['primitive', 'complex'],
                                          weights=[count_prim/total_count, count_complex/total_count], k=1)[0]

        if template_type == 'primitive':
            if default_args_list is None:
                default_args_list = [dict()]
            if structure_list is None:
                structure_list = helpers.generate_primitive_structure(self.primitive_templates)
            structure_list = [structure_list[0][1]]
            template, params = self.select_primitive_template(structure_list, default_args_list[0])
        elif template_type == 'complex':
            if structure_list is None:
                structure_list = helpers.generate_complex_structure(
                    self,
                    max_depth=max_depth)
            if default_args_list is None:
                default_args_list = [dict() for _ in range(len(structure_list))]
            template, params = self.select_complex_template(structure_list, 0, default_args_list)
        return template(**params)

    def run(self, num_dialogues, flush_after=None, save_dialogues=False, notebook_run=False):
        """
        Generates and runs a number of dialogues. The policies used in the dialogue are rule-based, and
        the dialogue should evaluate to 1. In case the
        dialogue does not evaluate to 1, an error is logged together with the dialogue utterances.

        Parameters
        ----------
        num_dialogues : int
            The number of dialogues to be generated
        flush_after : int
            Flushes the dia_generator state after a specific number of generated dialogues is reached.
        save_dialogues : bool
            Whether to keep the dialogues in a list. It's useful sometimes to either not keep the dialogues or remove
            their utterances in order to save RAM.
        notebook_run : bool
            This parameter indicates whether the function is run from a jupyter notebook (True) or not (False).
            This parameter ensures the progress bars are shown correctly in a jupyter notebook.

        Returns
        -------
        dialogues : list
            A list of Dialogue-s or an empty list if the save_dialogues is False.

        """
        if notebook_run:
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm

        count_dialogues = 0
        dialogues = []
        progress_bar = tqdm(total=num_dialogues)
        while True:
            dialogue = self.generate_dialogue()
            if dialogue is not None:
                count_dialogues += 1
                dialogue.run()
                if save_dialogues:
                    dialogues.append(dialogue)

                if dialogue.evaluate_goal() != 1:
                    logger.error("There is some error in the dialogue. The dialogue is the following:")
                    str_dialogue = ""
                    for idx, utter in enumerate(dialogue.utterances):
                        str_dialogue += dialogue.utterances[idx].to_string()
                        if idx != len(dialogue.utterances) - 1:
                            str_dialogue += "\n"
                    logger.error(str_dialogue)
            progress_bar.update(1)
            if count_dialogues >= num_dialogues:
                break
            if flush_after is not None and len(self.context) >= flush_after:
                self.flush()
        progress_bar.close()
        return dialogues

    def flush(self):
        """ Flushes the dialogue generator state in order to save memory."""
        self.context_strings.flush()
        self.context.flush()
        self.meta_context.flush()
        self.world.flush_undo_changes()
        self.knowledge_base.flush_undo_changes()

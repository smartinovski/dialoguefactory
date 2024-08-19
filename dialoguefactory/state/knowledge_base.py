#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the class that stores factual information efficiently.
"""
import logging
from . import kn_updaters, kn_checkers

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    The knowledge base is used to efficiently store information and quickly fetch information that
    is observed by the agent.
    The meta context can have a million sentences (some of them which are repeating as well), so
    querying information from the meta context can be costly.
    For example, if you want to check whether the color of a small toy is blue from the context, you'll have
    to find that information first. Later, you have to check for sentences that do not indicate any change in color.
    On the contrary, the knowledge base only passes the meta context only once and stores the information in
    the sent_db, and the prop_seen, prop_seen_neg, attr_seen, attr_seen_neg fields of the Entity.
    This is done with the help of the updaters. Later, the checkers are used to check whether an agent has observed
    the queried information.

    Write when the world and undo changes are used.

    Attributes
    ----------
    context : ListDb
        The meta-context is used to update the knowledge base.
    world : World
        The world is used in the updaters.
    undo_changes : list
        A list of changes made by the updaters to the sent_db and the fields mentioned above.
    last_context_id : int
        The last point in the meta context is used by the updaters to update the knowledge set.
    sent_db : set
        A list of factual sentences. This field is used by the kn_updaters.basic_updater.
    updaters : list
        A list of functions that update the knowledge base.
    checkers : list
        A list of functions that are used to query the validity of a sentence. A sentence is valid if it's factual and
        if it is observed by the agent.

    """
    def __init__(self, meta_context, world, undo_changes=None,
                 last_context_id=None, sent_db=None,
                 updaters=None, checkers=None):

        self.context = meta_context
        self.world = world
        self.undo_changes = list() if undo_changes is None else undo_changes
        self.last_context_id = 0 if last_context_id is None else last_context_id
        self.sent_db = set() if sent_db is None else sent_db
        self.updaters = [kn_updaters.property_update,
                         kn_updaters.have_update,
                         kn_updaters.look_updater,
                         kn_updaters.see_updater,
                         kn_updaters.go_updater,
                         kn_updaters.get_updater,
                         kn_updaters.drop_updater,
                         kn_updaters.opens_updater,
                         kn_updaters.close_updater,
                         kn_updaters.update_elem_exists,
                         kn_updaters.change_updater,
                         kn_updaters.permit_updater] if updaters is None else updaters

        self.checkers = [kn_checkers.property_check,
                         kn_checkers.have_check,
                         kn_checkers.check_elem_exists,
                         kn_checkers.unique_desc_check,
                         kn_checkers.val_is_key_checker,
                         kn_checkers.basic_check] if checkers is None else checkers

    def context_update(self):
        """ Updates the knowledge base with the unseen context sentences. """
        last_num_elems = len(self.context)-self.last_context_id

        # in case the context was flushed.
        if last_num_elems < 0:
            last_num_elems = len(self.context)

        addition = self.context.get(last_num_elems)
        addition = [sent for sent in addition if len(sent.describers) > 0 and sent.describers[0].get_arg("Rel") is not None]
        self.multi_update(addition)
        self.last_context_id = len(self.context)

    def multi_update(self, sents):
        """ Updates the knowledge base with a list of sentences (each class of components.Sentence) """
        for sent in sents:
            try:
                self.single_update(sent)
            except Exception as err:
                logger.error(err, exc_info=True)

    def single_update(self, sent):
        """ Updates the knowledge base with a single sentence. """
        for updater in self.updaters:
            updater(self, sent)

    def multi_check(self, sents):
        """ Checks the sentences against the knowledge base for their validity.
            A sentence is valid if it's factual, and it is observed by the agent.
            If all of them are valid, return True. If at least one of them is not valid, return False.
            Otherwise, return None (unknown validity)
        """
        self.context_update()
        checks = []
        for sent in sents:
            checks.append(self.check(sent, False))

        is_true = None
        if all(checks):
            is_true = True
        elif False in checks:
            is_true = False

        return is_true

    def check(self, sent, update_context=True):
        """ Checks the validity of a single sentence against the knowledge base.
            A sentence is valid if it's factual, and it is observed by the agent.
            If update_context is true, it will update the knowledge base first
            with the unseen sentences.
        """
        if update_context:
            self.context_update()

        for checker in self.checkers:
            try:
                res = checker(self, sent)
            except Exception as err:
                logger.error(err, exc_info=True)
                res = None
            if res is not None:
                return res
        return None

    def save_state(self):
        """ Save the state that changes with time. """
        return len(self.undo_changes), self.last_context_id

    def recover_state(self, state):
        """ Recover the state that changes with time. """
        prev_undo_counter = state[0]
        for idx in range(len(self.undo_changes) - 1, prev_undo_counter - 1, -1):
            cmd = self.undo_changes[idx]
            cmd()
        del self.undo_changes[prev_undo_counter:]
        self.last_context_id = state[1]

    def flush_undo_changes(self):
        """ Removes the saved changes in order to save memory. """
        del self.undo_changes[:]

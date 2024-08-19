#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module provides the class that represents a database of all describer mappers. It has functions that can
convert an arbitrary describer into a sentence.
"""

import inspect
from ..language import components as lc
from ..language import desc_mappers as dm


class MapperDatabase:
    """
    This class is used for generating a sentence from a list of describers.

    Attributes
    ----------
    slist : list, optional
        The database comprises a list of mappers that map the describers to a sentence.

    """

    def __init__(self, slist=None):
        self.slist = list() if slist is None else slist

    def query_sentence(self, describers, speaker=None, last_match=-1):
        """
        Queries a sentence from the database based on the given describers.
        It queries both primitive and complex sentences.
        The primitive sentences are explained in the query_primitive_sentence function.
        A complex sentence consists of one independent and one or more dependent sentences.

        Parameters
        ----------
        describers : list
            List of instances of the class Describer.
        speaker : Entity, optional
            The person that utters the sentence.
        last_match : int, optional
            The index of the sentence to select
            in case there are multiple matches in the database.

        Returns
        -------
        new_sent : Sentence
            The queried sentence.

        """
        new_sent = lc.Sentence(speaker=speaker)

        for desc in describers:
            new_desc = lc.Describer()
            for arg_key, arg in desc.args.items():
                if isinstance(arg.value, lc.Sentence):
                    new_desc.args[arg_key] = lc.Arg(self.query_sentence(arg.value.describers,
                                                                        speaker,
                                                                        last_match))

                elif isinstance(arg.value, list):
                    new_list = []
                    for elem in arg.value:
                        if isinstance(elem, lc.Sentence):
                            new_list.append(self.query_sentence(elem.describers, speaker, last_match))
                        else:
                            new_list.append(elem)
                    new_desc.args[arg_key] = lc.Arg(new_list)
                else:
                    new_desc.args[arg_key] = arg
            new_sent.describers.append(new_desc)

        matching_sentences = self.query_primitive_sentence(new_sent.describers, speaker)
        if len(matching_sentences) != 0:
            new_sent = matching_sentences[last_match]
        else:
            new_sent = None

        return new_sent

    def query_primitive_sentence(self, describers, speaker=None):
        """
        Queries the database for a primitive sentence from a list of describers.
        A primitive sentence is one that has a single predicate, or if it consists of more than one predicate
        then the constituent sentences are independent.
        The complex sentences are handled in the query_sentence function.

        Parameters
        ----------
        describers : list
            List of describers used for querying the database.
        speaker : Entity, optional
            The agent that the matching sentences belong to.

        Returns
        -------
        matching_sentences : list
            A list of matched sentences.

        """
        matching_sentences = []

        for db_mapper in self.slist:

            additional_params = {'describers': describers}
            customiz_params = list(inspect.signature(db_mapper).parameters)
            if 'database' in customiz_params:
                additional_params['database'] = self
            if 'no_parts' in customiz_params:
                additional_params['no_parts'] = False

            matched_sentence = db_mapper(**additional_params)

            if matched_sentence is not None and matched_sentence.describers == describers:
                matched_sentence.speaker = speaker
                matching_sentences.append(matched_sentence)

        return matching_sentences

    def register(self, desc_mappers):
        """
        Registers the describer mapper in the database.

        Parameters
        ----------
        desc_mappers : list or function
            The describer mapper/s to be added in the database.

        Returns
        -------
        None.

        """
        if not isinstance(desc_mappers, list):
            desc_mappers = [desc_mappers]
        else:
            desc_mappers = desc_mappers
        for dmapper in desc_mappers:
            self.slist.append(dmapper)


def create_database_all_mappers():
    """
    Creates an instance of the Database with all the mappers
    available in the language.desc_mappers file.

    """

    database = MapperDatabase()

    database.register([dm.cont_connector,
                       dm.get, dm.drop, dm.say,
                       dm.see, dm.look, dm.go, dm.be,
                       dm.have, dm.opens, dm.close,
                       dm.change, dm.tries,
                       dm.know, dm.reveal, dm.permit,
                       dm.empty
                       ])
    return database

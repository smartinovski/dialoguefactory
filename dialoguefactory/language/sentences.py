#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions that create a statement.
"""

from . import components as lc

from . import helpers as he
from . import describers as tdescribers
from . import queries as tqueries

from . import desc_mappers as dm


def cont(sentences, speaker=None):
    """
    Concatenates multiple independent sentences (of type Sentence) into a single compound sentence.

    Parameters
    ----------
    sentences : list
        The list of sentences.
    speaker : Entity
        The agent who utters the sentence.

    Returns
    -------
    new_sent : Sentence
        The sentence that contains two or more sentences.

    """
    new_sent = lc.Sentence(sentences, speaker=speaker)

    for sent in sentences:
        new_sent.describers += sent.describers

    new_sent.customizers['desc_mapping'] = lc.Customizer(dm.cont_connector, {})
    new_sent.customizers['reduce'] = lc.Customizer(he.reduce_sentences, {"sentences": sentences})
    new_sent.customizers['request_mapping'] = lc.Customizer(tqueries.cont_connector,
                                                            {'sentences': sentences,
                                                             'speaker': speaker})
    return new_sent


def cont_and(sentences, connector="and", speaker=None):
    """
    Concatenates multiple independent sentences (of type Sentence) with a connector in a single
    compound sentence.

    Parameters
    ----------
    sentences : list
        The list of sentences.
    speaker : Entity, optional
        The agent who utters the sentence.
    connector : str
        The connector that appears between the sentences.

    Returns
    -------
    new_sent : Sentence
        The concatenated sentence.

    """
    new_sent = None
    if len(sentences) > 1:
        break_flag = False
        for sent in sentences:
            if sent is None or not isinstance(sent, lc.Sentence):
                break_flag = True

        if not break_flag:
            reduced_sentences = he.reduce_sentences(sentences)
            for sent in reduced_sentences[:len(reduced_sentences)-1]:
                if sent.parts[-1].to_string() == '.':
                    del sent.parts[-1]

            new_sent_parts = he.join_parts_with_connector(reduced_sentences, connector)
            new_sent = lc.Sentence(new_sent_parts, speaker=speaker)
            for sent in sentences:
                new_sent.describers += sent.describers
            new_sent.customizers['desc_mapping'] = lc.Customizer(dm.cont_connector, {'connector': connector})
            new_sent.customizers['reduce'] = lc.Customizer(he.reduce_sentences, {'sentences': sentences})
            new_sent.customizers['request_mapping'] = lc.Customizer(tqueries.cont_connector,
                                                                    {'sentences': sentences,
                                                                     'speaker': speaker,
                                                                     'connector': connector
                                                                     })

    return new_sent


def reduce_say(say_sent, user, agent, speaker):
    """
    Reduces a complex-compound say(...) sentence into multiple complex sentences.
    For example, the following sentence: "Max says to Andy: go to the kitchen and get the flour bag"
    gets reduced to two sentences: "Max says to Andy: go to the kitchen", "Max says to Andy: get the flour bag."

    Parameters
    ----------
    say_sent : Sentence
        The list of sentences.
    user : Entity
        The player issuing the say sentence. It's Max in the example above.
    agent : list or None
        The player that is addressed. It's ['to', andy] in the example above.
        This parameter is optional.
    speaker : Entity
        The player that utters the sentence.

    Returns
    -------
    new_sent : list
        The list of complex sentences that have type Sentence.
    """
    inner_sent = say_sent.describers[0].get_arg("Arg-PPT")

    reduced_sent = he.reduce_sentences([inner_sent])
    if len(reduced_sent) == 1 and id(reduced_sent[0]) == id(inner_sent):
        return say_sent
    new_sent = []
    for sent in reduced_sent:
        new_sent.append(say(user,  None, 'says', sent, agent, speaker=speaker))
    if None not in new_sent:
        return new_sent
    return None


@he.auto_fill([5], ["speaker"])
def say(user=(None, None), neg=(None, None), rel=(None, None),
        statement=(None, None), agent=(None, None), speaker=None):
    """
    Creates a Sentence for the verb say in the following form:

        <user> (neg) <say> <agent>: <statement>

    An example is "Hans says to Andy: drop the carrot on the table"
    """
    if statement[0] is None or not isinstance(statement[0], lc.Sentence):
        return None

    if lc.verb_inf(rel[0]) != "say":
        return None

    sent = lc.Sentence([user[1],
                       neg[1],
                       rel[1],
                       agent[1],
                       lc.Word(':'),
                       statement[1]], speaker=speaker)
    describer = tdescribers.say(user, neg, rel, statement, agent)
    sent.describers = [describer]

    sent.meta_sent = [statement[0]]
    sent.customizers['desc_mapping'] = lc.Customizer(dm.say, {})

    sent.customizers['reduce'] = lc.Customizer(reduce_say, {"say_sent": sent,
                                                            "user": user,
                                                            "agent": agent,
                                                            "speaker": speaker
                                                            })
    return sent


@he.auto_fill([6], ["speaker"])
def get(player=(None, None), mod=(None, None), neg=(None, None), rel=(None, None),
        entity=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a Sentence for the verb get in the following form:

            <user> <mod> <neg> <rel> <entity> <prepos_location>

        An example is "Hans can not get the small ball in the toy's container."
    """
    if lc.verb_inf(rel[0]) != "get":
        return None

    get_res = lc.Sentence([player[1],
                           (lc.Word('does') if mod[1] is None and neg[1] is not None else None),
                           mod[1],
                           neg[1],
                           rel[1],
                           entity[1],
                           prepos_location[1],
                           lc.Word('.')], speaker=speaker)
    get_desc = tdescribers.get(player, mod, neg, rel, entity, prepos_location)
    get_res.describers = [get_desc]
    get_res.customizers['desc_mapping'] = lc.Customizer(dm.get, {})
    get_res.customizers['request_mapping'] = lc.Customizer(tqueries.get, {'player': player,
                                                                          'neg': neg,
                                                                          'rel': 'get',
                                                                          'entity': entity,
                                                                          'prepos_location': prepos_location,
                                                                          'speaker': speaker,
                                                                          })
    return get_res


@he.auto_fill([6], ["speaker"])
def drop(player=(None, None), mod=(None, None), neg=(None, None), rel=(None, None),
         entity=(None, None), prepos_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb drop in the following form:

        <player> <mod> <neg> <rel> <entity> <prepos_location>

    An example is: The big person should drop the apple on the table.
    """
    if lc.verb_inf(rel[0]) != "drop":
        return None
    res = lc.Sentence([player[1],
                       mod[1],
                       neg[1],
                       rel[1],
                       entity[1],
                       prepos_location[1],
                       lc.Word('.')], speaker=speaker)
    desc = tdescribers.drop(player, mod, neg, rel, entity, prepos_location)
    res.describers = [desc]
    res.customizers['desc_mapping'] = lc.Customizer(dm.drop, {})
    res.customizers['request_mapping'] = lc.Customizer(tqueries.drop, {
        'player': player,
        'neg': neg,
        'rel': 'drop',
        'entity': entity,
        'prepos_location': prepos_location,
        'speaker': speaker,
    })
    return res


@he.auto_fill([5], ["speaker"])
def see(player, neg, rel, item, item_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb see in the following form:

        <player> <neg> <rel> <item> <item_location>

    An example is "Hannah sees Andy in the kitchen."
    """
    if lc.verb_inf(rel[0]) != "see":
        return None

    see_res = lc.Sentence([player[1],
                           (lc.Word('does') if (neg[1] is not None) else None),
                           neg[1],
                           rel[1],
                           item[1],
                           item_location[1],
                           lc.Word('.')], speaker=speaker)
    see_desc = tdescribers.see(player, neg, rel, item, item_location)
    see_res.describers = [see_desc]
    see_res.customizers['desc_mapping'] = lc.Customizer(dm.see, {})

    return see_res


@he.auto_fill([6], ["speaker"])
def look(looker=(None, None), mod=(None, None), neg=(None, None), rel=(None, None),
         thing_looked=(None, None), item_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb look in the following form:

        <looker> <mod> <neg> <rel> <thing_looked> <item_location>

    An example is "Jim looks in the bathroom."
    """
    if lc.verb_inf(rel[0]) != "look":
        return None

    look_response = lc.Sentence([looker[1],
                                 mod[1],
                                 neg[1],
                                 rel[1],
                                 thing_looked[1],
                                 item_location[1],
                                 lc.Word('.')], speaker=speaker)
    describer = tdescribers.look(looker, mod, neg, rel, thing_looked, item_location)
    look_response.describers = [describer]

    look_response.customizers['desc_mapping'] = lc.Customizer(dm.look, {})
    look_response.customizers['request_mapping'] = lc.Customizer(tqueries.look, {
        'player': looker,
        'neg': neg,
        'rel': 'look',
        'thing_looked': thing_looked,
        'item_location': item_location,
        'speaker': speaker
    })

    return look_response


@he.auto_fill([4], ["speaker"])
def permit(action_allowed=(None, None), neg=(None, None), rel=(None, None), allower=(None, None), speaker=None):
    """
    Creates a Sentence for the verb permit in the following form:

        <action_allowed> is <neg> <rel> <allower>

    An example is "Getting players is not permitted."

    """
    if lc.verb_inf(rel[0]) != "permit":
        return None

    permit_response = lc.Sentence([action_allowed[1],
                                   lc.Word('is'),
                                   neg[1],
                                   rel[1],
                                   allower[1],
                                   lc.Word('.')], speaker=speaker)
    describer = tdescribers.permit((None, None), neg, rel, action_allowed, allower)
    permit_response.describers = [describer]
    permit_response.customizers['desc_mapping'] = lc.Customizer(dm.permit, {})

    return permit_response


@he.auto_fill([5], ["speaker"])
def have(entity=(None, None), rel=(None, None), neg=(None, None),
         possession=(None, None), prepos_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb have in the following form:

        <entity> <neg> <rel> <possession> <prepos_location>

    An example is: Hans Mustermann has the rug.
    """
    if lc.verb_inf(rel[0]) != "have":
        return None

    contains_res = lc.Sentence([entity[1],
                                rel[1],
                                neg[1],
                                possession[1],
                                prepos_location[1],
                                lc.Word('.')],
                               speaker=speaker)
    contains_desc = tdescribers.have(entity, rel, neg, possession, prepos_location)
    contains_res.describers = [contains_desc]
    contains_res.customizers['desc_mapping'] = lc.Customizer(dm.have, {})

    return contains_res


def path_reveal(source_location,  target_location, neg, rel, speaker=None):
    """
    Creates a Sentence in the following form:

        Path from <source_location> to <target_location> <is> <neg> <rel>.

    An example is "The path from the barn to the living room is not revealed."
    """
    path_reveal_res = reveal(None,
                             neg,
                             rel,
                             ['The',
                              'path',
                              'from',
                              source_location,
                              'to',
                              target_location],
                             speaker=speaker)
    return path_reveal_res


@he.auto_fill([4], ["speaker"])
def reveal(revealer, neg, rel, truth_cond, speaker=None):
    """
    Creates a Sentence in the following form:

        <truth_cond> is <neg> <rel> <revealer>

    An example is "The living room's location is not revealed."

    """
    if lc.verb_inf(rel[0]) != "reveal":
        return None

    reveal_res = lc.Sentence([truth_cond[1],
                              lc.Word('is'),
                              neg[1],
                              rel[1],
                              revealer[1],
                              lc.Word('.')], speaker=speaker)
    describer = tdescribers.reveal(revealer, truth_cond, neg, rel)
    reveal_res.describers = [describer]
    reveal_res.customizers['desc_mapping'] = lc.Customizer(dm.reveal, {})

    return reveal_res


@he.auto_fill([4], ["speaker"])
def be(topic, rel, neg, comment, speaker=None):
    """
    Create a Sentence for the verb to be in the following form:

       <topic> <rel> <neg> <comment>

    An example is, "The rug's color is blue."
    """
    if lc.verb_inf(rel[0]) != "be":
        return None
    item_is_res = lc.Sentence([topic[1],
                               rel[1],
                               neg[1],
                               comment[1],
                               lc.Word('.')], speaker=speaker)
    describer = tdescribers.be(topic, rel, neg, comment)
    item_is_res.describers = [describer]
    item_is_res.customizers['desc_mapping'] = lc.Customizer(dm.be, {})
    return item_is_res


@he.auto_fill([4], ["speaker"])
def know(knower,  neg, rel, fact_known, speaker=None):
    """
    Creates a Sentence for the verb know in the following form:

        <knower> <rel> <neg> <fact_known>

    An example is, "He knows not whether the toys container is closed."
    """
    if lc.verb_inf(rel[0]) != "know":
        return None
    knower_knows = lc.Sentence([knower[1],
                               rel[1],
                               neg[1],
                               fact_known[1],
                               lc.Word('.')], speaker=speaker)

    describer = tdescribers.know(knower, neg, rel, fact_known)
    knower_knows.describers = [describer]
    knower_knows.customizers["reduce"] = lc.Customizer(lambda sent: sent, {"sent": knower_knows})
    knower_knows.customizers["desc_mapping"] = lc.Customizer(dm.know, {})

    return knower_knows


@he.auto_fill([6], ["speaker"])
def opens(opener=(None, None), mod=(None, None), neg=(None, None),
          rel=(None, None), thing_opened=(None, None),
          prepos_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb open in the following form:

        <opener> <mod> <neg> <rel> <thing_opened> <prepos_location>

    An example is, "Gretel opens the door in the kitchen."
    """

    if lc.verb_inf(rel[0]) != "open":
        return None
    res = lc.Sentence([opener[1],
                       mod[1],
                       neg[1],
                       rel[1],
                       thing_opened[1],
                       prepos_location[1],
                       lc.Word('.')],
                      speaker=speaker)
    describer = tdescribers.opens(opener, mod, neg, rel, thing_opened, prepos_location)
    res.describers = [describer]
    res.customizers["reduce"] = lc.Customizer(lambda sent: sent, {"sent": res})
    res.customizers['request_mapping'] = lc.Customizer(tqueries.opens,
                                                       {'opener': opener,
                                                        'neg': neg,
                                                        'rel': 'open',
                                                        'thing_opened': thing_opened,
                                                        'prepos_location': prepos_location})
    res.customizers['desc_mapping'] = lc.Customizer(dm.opens, {})

    return res


@he.auto_fill([6], ["speaker"])
def close(closer=(None, None), mod=(None, None), neg=(None, None),
          rel=(None, None), thing_closed=(None, None),
          prepos_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb close in the following form:

        <closer> <mod> <neg> <rel> <thing_closed> <prepos_location>

    An example is, "Gretel can not close the door."
    """

    if lc.verb_inf(rel[0]) != "close":
        return None
    res = lc.Sentence([closer[1],
                       mod[1],
                       neg[1],
                       rel[1],
                       thing_closed[1],
                       prepos_location[1],
                       lc.Word('.')],
                      speaker=speaker)
    describer = tdescribers.close(closer, mod, neg, rel, thing_closed, prepos_location)
    res.describers = [describer]
    res.customizers["reduce"] = lc.Customizer(lambda sent: sent, {"sent": res})
    res.customizers['request_mapping'] = lc.Customizer(tqueries.close,
                                                       {'closer': closer,
                                                        'neg': neg,
                                                        'rel': 'close',
                                                        'thing_closed': thing_closed,
                                                        'prepos_location': prepos_location})
    res.customizers['desc_mapping'] = lc.Customizer(dm.close, {})

    return res


@he.auto_fill([5], ["speaker"])
def tries(entity_trying, mod, neg, rel, thing_tried, speaker=None):
    """
    Creates a Sentence for the verb try in the following form:

        <entity_trying> <mod> <neg> <rel> <thing_tried>

    An example is, "Coco tries going north."
    """

    if lc.verb_inf(rel[0]) != "try":
        return None

    sent = lc.Sentence([entity_trying[1],
                        mod[1],
                        neg[1],
                        rel[1],
                        thing_tried[1],
                        ], speaker=speaker)
    describer = tdescribers.tries(entity_trying, mod, neg, rel, thing_tried)

    sent.describers = [describer]
    sent.customizers["reduce"] = lc.Customizer(lambda sentence: sentence, {"sentence": sent})
    sent.customizers['desc_mapping'] = lc.Customizer(dm.tries, {})

    return sent


@he.auto_fill([7], ["speaker"])
def go(player=(None, None), mod=(None, None), neg=(None, None), rel=(None, None),
       direction=(None, None), source_location=(None, None),
       target_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb go in the following form:

        <player> <mod> <neg> <rel> <direction> <source_location> <target_location>

    An example is, "Coco goes north from the porch path to the living room."
    """

    if lc.verb_inf(rel[0]) != "go":
        return None

    player_moved_res = lc.Sentence([player[1],
                                    mod[1],
                                    neg[1],
                                    rel[1],
                                    direction[1],
                                    source_location[1],
                                    target_location[1],
                                    lc.Word('.')],
                                   speaker=speaker)
    player_moved_desc = tdescribers.go(player, mod, neg, rel, direction,
                                       source_location, target_location)
    player_moved_res.describers = [player_moved_desc]
    player_moved_res.customizers['desc_mapping'] = lc.Customizer(dm.go, {})
    player_moved_res.customizers['request_mapping'] = lc.Customizer(tqueries.go, {
        'player': player,
        'neg': neg,
        'rel': 'go',
        'direction': direction,
        'source_location': source_location,
        'target_location': target_location,
        'speaker': speaker,
    })

    return player_moved_res


@he.auto_fill([5], ["speaker"])
def issue(issuer, mod, neg, rel, thing_issued, speaker=None):
    """
    Creates a Sentence for the verb issue in the following form:

        <issuer> <mod> <neg> <rel> <thing_issued>

    An example is, "Gretel issued an unrecognizable command."
    """
    if lc.verb_inf(rel[0]) != "issue":
        return None
    res = lc.Sentence([issuer[1],
                       mod[1],
                       neg[1],
                       rel[1],
                       thing_issued[1],
                       lc.Word('.')
                       ], speaker=speaker)
    desc = tdescribers.issue(issuer, mod, neg, rel, thing_issued)
    res.describers = [desc]

    return res


@he.auto_fill([7], ["speaker"])
def change(causer=(None, None), mod=(None, None), neg=(None, None), rel=(None, None),
           thing_changing=(None, None), end_state=(None, None), prepos_location=(None, None), speaker=None):
    """
    Creates a Sentence for the verb change in the following form:

        <causer> <mod> <neg> <rel> <thing_changing> <end_state> <prepos_location>

    An example is, "Andy can not change the door size to small."
    """

    if lc.verb_inf(rel[0]) != "change":
        return None

    res = lc.Sentence([causer[1],
                       mod[1],
                       neg[1],
                       rel[1],
                       thing_changing[1],
                       end_state[1],
                       prepos_location[1],
                       lc.Word('.')
                       ], speaker=speaker)
    desc = tdescribers.change(causer, mod, neg, rel, thing_changing, end_state, prepos_location)
    res.describers = [desc]
    res.customizers['desc_mapping'] = lc.Customizer(dm.change, {})
    res.customizers['request_mapping'] = lc.Customizer(tqueries.change, {'causer': causer,
                                                                         'neg': neg,
                                                                         'rel': 'change',
                                                                         'thing_changing': thing_changing,
                                                                         'end_state': end_state,
                                                                         'prepos_location': prepos_location,
                                                                         'speaker': speaker})
    return res


def qwant(wanter, neg, rel, thing_wanted, speaker=None):
    """
    Creates a question with the verb want in the following form:

        <wanter> <neg> <rel> <thing_wanted> ?

    For example: Do you want to get a small latte?
    """
    if rel[0].isupper() and lc.verb_inf(rel.lower()) == "want":
        return None

    sent = lc.Sentence([lc.Word("Do"),
                        neg[1],
                        wanter[1],
                        rel[1],
                        thing_wanted[1],
                        lc.Word("?")
                        ], speaker=speaker)

    sent.describers = [tdescribers.want(wanter, neg, rel, thing_wanted)]
    return sent


def want(wanter, neg, rel, thing_wanted, speaker=None):
    """
    Creates a Sentence for the verb want in the following form:

        <wanter> <neg> <rel> <thing_wanted>

    An example is, "Hannah wants the red toy."
    """

    if lc.verb_inf(rel[0]) != "want":
        return None
    sent = lc.Sentence([wanter[1],
                        lc.Word("does") if neg is not None else None,
                        neg[1] if neg[1] is not None else None,
                        rel[1],
                        thing_wanted[1],
                        lc.Word(".")
                        ], speaker=speaker)

    sent.describers = [tdescribers.want(wanter, neg, rel, thing_wanted)]
    return sent


@he.auto_fill([4], ["speaker"])
def Wh_question(comment, rel, neg, topic, speaker=None):
    """
    Creates a Wh-question in the following form:

        <Wh-> <rel> <neg> <topic> ?

    For example, "Where is the closest shop?"
    """
    if lc.verb_inf(rel[0]) != "be":
        return None
    res = lc.Sentence([comment[1],
                       rel[1],
                       neg[1],
                       topic[1],
                       lc.Word('?')], speaker=speaker)
    describer = tdescribers.be(topic, rel, neg, comment)
    res.describers = [describer]

    return res

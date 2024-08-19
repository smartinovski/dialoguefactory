#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions that create request sentences from parameters.
"""

from . import components as lc
from . import describers as tdescribers
from . import helpers as he


@he.auto_fill([6], ["speaker"])
def get(tmp=(None, None), player=(None, None), neg=(None, None), rel=(None, None),
        entity=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a request for the verb get in the following format:

            <tmp> <player> (neg) <get> <entity> <prepos_location>

        For example, "Hannah, get the book on the shelf."
    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "get":
        return None
    get_res = lc.Sentence([tmp[1],
                           player[1],
                           lc.Word(","),
                           neg[1],
                           rel[1],
                           entity[1],
                           prepos_location[1],
                           lc.Word('.')], speaker=speaker)

    get_desc = tdescribers.get((None, None), (None, None), neg, rel,
                               entity, prepos_location)
    get_desc.args["AM-DIS"] = lc.Arg(player[0], player[1])
    if tmp[0] is not None:
        get_desc.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])
    get_res.describers = [get_desc]
    get_res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": get_res})
    get_res.customizers["desc_mapping"] = lc.Customizer(dm.get, {})

    return get_res


@he.auto_fill([6], ["speaker"])
def drop(tmp=(None, None), player=(None, None), neg=(None, None), rel=(None, None),
         entity=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a request for the verb drop in the following format:

            <tmp> <player> (neg) <drop> <entity> <prepos_location>

        where prepos_location refers to the target location.
        For example, "Max, drop the cup on the table."

    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "drop":
        return None

    drop_res = lc.Sentence([tmp[1],
                            player[1],
                            lc.Word(","),
                            neg[1],
                            rel[1],
                            entity[1],
                            prepos_location[1],
                            lc.Word('.')],
                           speaker=speaker)

    drop_res_desc = tdescribers.drop((None, None), (None, None), neg, rel,
                                     entity, prepos_location)
    drop_res_desc.args["AM-DIS"] = lc.Arg(player[0], player[1])
    if tmp[0] is not None:
        drop_res_desc.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    drop_res.describers = [drop_res_desc]
    drop_res.customizers['request_mapping'] = lc.Customizer(he.returns_same, {"sentence": drop_res})
    drop_res.customizers["desc_mapping"] = lc.Customizer(dm.drop, {})

    return drop_res


@he.auto_fill([6], ["speaker"])
def look(tmp=(None, None), player=(None, None), neg=(None, None), rel=(None, None),
         thing_looked=(None, None), item_location=(None, None), speaker=None):
    """ Creates a request for the verb look in the following format:

             <tmp> <player> (neg) <look> <thing_looked> <item_location>

        For example, "Max, look in the clothing drawer in the bedroom."
    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "look":
        return None

    look_response = lc.Sentence([tmp[1],
                                 player[1],
                                 lc.Word(","),
                                 neg[1],
                                 rel[1],
                                 thing_looked[1],
                                 item_location[1],
                                 lc.Word('.')],
                                speaker=speaker)

    describer = tdescribers.look((None, None), (None, None), neg, rel,
                                 thing_looked, item_location, look_response)
    describer.args["AM-DIS"] = lc.Arg(player[0], player[1])
    if tmp[0] is not None:
        describer.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])
    look_response.describers = [describer]
    look_response.customizers["request_mapping"] = lc.Customizer(he.returns_same,
                                                                 {"sentence": look_response})
    look_response.customizers["desc_mapping"] = lc.Customizer(dm.look, {})

    return look_response


@he.auto_fill([7], ["speaker"])
def go(tmp=(None, None), player=(None, None), neg=(None, None), rel=(None, None),
       direction=(None, None), source_location=(None, None), target_location=(None, None), speaker=None):
    """ Creates a request for the verb go in the following format:

             <tmp> <player> (neg) <go> <direction> <source_location> <target_location>

        For example, "Andy, go north from the guest room."
    """

    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "go":
        return None

    go_res = lc.Sentence([tmp[1],
                          player[1],
                          lc.Word(","),
                          neg[1],
                          rel[1],
                          direction[1],
                          source_location[1],
                          target_location[1],
                          lc.Word('.')],
                         speaker=speaker)

    go_desc = tdescribers.go((None, None), (None, None), neg,
                             rel, direction, source_location,
                             target_location, go_res)
    go_desc.args["AM-DIS"] = lc.Arg(player[0], player[1])
    if tmp[0] is not None:
        go_desc.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    go_res.describers = [go_desc]
    go_res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": go_res})
    go_res.customizers["desc_mapping"] = lc.Customizer(dm.go, {})

    return go_res


@he.auto_fill([6], ["speaker"])
def opens(tmp=(None, None), opener=(None, None), neg=(None, None), rel=(None, None),
          thing_opened=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a request for the verb open in the following format:

             <tmp> <opener> <open> (neg) <open> <thing_opened> <prepos_location>

        For example, "John, open the plastic door in the kitchen."
    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "open":
        return None
    res = lc.Sentence([tmp[1],
                       opener[1],
                       lc.Word(","),
                       neg[1],
                       rel[1],
                       thing_opened[1],
                       prepos_location[1],
                       lc.Word('.')],
                      speaker=speaker)
    describer = tdescribers.opens((None, None), (None, None), neg, rel,
                                  thing_opened, prepos_location, res)

    describer.args["AM-DIS"] = lc.Arg(opener[0], opener[1])
    if tmp[0] is not None:
        describer.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    res.describers = [describer]
    res.customizers["desc_mapping"] = lc.Customizer(dm.opens, {})
    res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": res})
    return res


@he.auto_fill([6], ["speaker"])
def close(tmp=(None, None), closer=(None, None), neg=(None, None), rel=(None, None),
          thing_closed=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a request for the verb close in the following format:

             <tmp> <closer> (neg) <close> <thing_closed> <prepos_location>

        For example, "John, close the cardboard container in the barn."
    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "close":
        return None
    res = lc.Sentence([tmp[1],
                       closer[1],
                       lc.Word(","),
                       neg[1],
                       rel[1],
                       thing_closed[1],
                       prepos_location[1],
                       lc.Word('.')],
                      speaker=speaker)
    describer = tdescribers.close((None, None), (None, None), neg, rel,
                                  thing_closed, prepos_location, res)

    describer.args["AM-DIS"] = lc.Arg(closer[0], closer[1])
    if tmp[0] is not None:
        describer.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    res.describers = [describer]
    res.customizers["desc_mapping"] = lc.Customizer(dm.close, {})
    res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": res})
    return res


@he.auto_fill([7], ["speaker"])
def change(tmp=(None, None), causer=(None, None), neg=(None, None), rel=(None, None),
           thing_changing=(None, None), end_state=(None, None), prepos_location=(None, None), speaker=None):
    """ Creates a request for the verb change in the following format:

             <tmp> <causer> (neg) <change> <thing_changing> <end_state> <prepos_location>

        where <prepos_location> refers to the location of the <thing_changing>.
        For example, "Hans, change the cube's color to red."

    """
    from . import desc_mappers as dm

    if lc.verb_inf(rel[0]) != "change":
        return None

    res = lc.Sentence([tmp[1],
                       causer[1],
                       lc.Word(","),
                       neg[1],
                       rel[1],
                       thing_changing[1],
                       end_state[1],
                       prepos_location[1],
                       lc.Word('.')
                       ], speaker=speaker)
    desc = tdescribers.change((None, None), (None, None), neg, rel, thing_changing, end_state, prepos_location, res)
    res.describers = [desc]
    desc.args["AM-DIS"] = lc.Arg(causer[0], causer[1])
    if tmp[0] is not None:
        desc.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    res.customizers["desc_mapping"] = lc.Customizer(dm.change, {})
    res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": res})

    return res


@he.auto_fill([6], ["speaker"])
def be(tmp, agent, topic, rel, neg, comment, speaker=None):
    """ Creates a question in the following form:

            <tmp> <agent>, <Is> (neg) <topic> <comment>

        For example, "Otto, Is the apple red?"
        The tmp can be used if you have want multiple requests to be executed consecutively.
        For example, "Jim, open the wooden container and then Andy, Is the wooden container open?"
    """
    from . import desc_mappers as dm
    if not rel[0][0].isupper() or lc.verb_inf(rel[0].lower()) != "be":
        return None
    is_item_res = lc.Sentence([tmp[1],
                               agent[1],
                               lc.Word(","),
                               rel[1],
                               neg[1],
                               topic[1],
                               comment[1],
                               lc.Word('?')], speaker=speaker)
    describer = tdescribers.be(topic, rel, neg, comment)
    describer.args["AM-DIS"] = lc.Arg(agent[0], agent[1])
    if tmp[0] is not None:
        describer.args["AM-TMP"] = lc.Arg(tmp[0], tmp[1])

    is_item_res.describers = [describer]
    is_item_res.customizers["desc_mapping"] = lc.Customizer(dm.be, {})
    is_item_res.customizers["request_mapping"] = lc.Customizer(he.returns_same, {"sentence": is_item_res})

    return is_item_res


def cont_connector(sentences, speaker=None, connector=None):
    """ Connects multiple requests in a single compound request using a connector. """
    from . import sentences as tsentences

    requests = []
    for sent in sentences:
        req = sent.run_customizer("request_mapping")
        requests.append(req)
    if connector is not None:
        res = tsentences.cont_and(requests, connector, speaker)
    else:
        res = tsentences.cont(requests, speaker)
    return res

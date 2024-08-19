#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains the functions that help implement the functions in the other modules in this folder.
"""
import copy


def create_oppos_sent(sent):
    """
        Creates an opposite sentence by adding an AM-NEG argument with the negation "not."
        in the describer. The "not" element is not added in the sent.parts because
        it might be hard to pinpoint the location where it should be added.

    """
    from ..language import components as lc

    desc = sent.describers[0]
    opposite_sent = lc.Sentence()
    if desc.get_arg("AM-NEG") is None:
        opposite_sent.describers = [lc.Describer(
                                                 args=copy.copy(desc.args))]
        opposite_sent.describers[0].args["AM-NEG"] = lc.Arg("not", lc.Word("not"))
    else:
        opposite_sent.describers = [lc.Describer(
                                                 args=copy.copy(sent.describers[0].args))]
        if "AM-NEG" in opposite_sent.describers[0].args:
            del opposite_sent.describers[0].args["AM-NEG"]
    return opposite_sent


def check_prop(sent):
    """
    Checks whether the sentence is in one of the following formats:

        - <entity> 's <property_key> is (not) <property_val>
        - <entity> is (not) <attribute>

    If it fits the format, it extracts the variables in the brackets.
    Otherwise, None is returned.
    The <entity> has to be an instance of env_main.BaseEntity.
    """
    from ..environment import entities as em

    if len(sent.describers) == 0:
        return None

    desc = sent.describers[0]
    rel = desc.get_arg('Rel', _type=0)
    neg = desc.get_arg('AM-NEG')
    if rel.infinitive == 'be' and rel.value[0].islower():
        topic_arg = desc.get_arg('Arg-PPT', _type=0)
        if topic_arg is not None:
            topic = topic_arg.value
            comment_arg = desc.get_arg('Arg-PRD',  _type=0)
            if comment_arg is not None:
                if isinstance(topic, list) and len(topic) >= 2 and topic[1] == "'s":
                    ent = topic[0]
                    if ent is not None and isinstance(ent, em.BaseEntity):
                        pkey = topic[2:]
                        if len(pkey) == 1:
                            pkey = topic[2]
                        else:
                            pkey = tuple(pkey)
                        pval = comment_arg.value
                        return ent, pkey, pval, neg
                elif isinstance(topic, em.BaseEntity):
                    attr = comment_arg.value
                    ent = topic
                    if ent is not None:
                        return ent, None, attr, neg
    return None


def shared_elements(objects, entity, elements=None, only_seen=False, break_first=False):
    if elements is None:
        elements = []

    if len(elements) == 0:
        return None

    elements = copy.copy(elements)
    if only_seen:
        elements = [elem for elem in elements if elem in entity.prop_seen or elem in entity.attr_seen]
    else:
        elements = [elem for elem in elements if elem in entity.properties or elem in entity.attributes]

    shared_el = []
    for other in objects:
        all_elements = []
        if other != entity:
            for elem in elements:
                if only_seen:
                    if elem in other.prop_seen and entity.prop_seen[elem] == other.prop_seen[elem]:
                        all_elements.append(elem)
                    elif elem in other.attr_seen:
                        all_elements.append(elem)
                else:
                    if elem in other.properties and entity.properties[elem] == other.properties[elem]:
                        all_elements.append(elem)
                    elif elem in other.attributes:
                        all_elements.append(elem)
            if len(elements) > 0 and set(elements).issubset(all_elements):
                shared_el.extend(elements)
                if break_first:
                    break

    return shared_el


def check_unique_entity(objects, entity, elements=None, only_seen=False):
    """ Check whether the <entity> differs from the list of objects based on a list of elements.
        An element can be a property like size or material or an attribute like 'locked' ('west', 'obstacle'), etc.
        only_seen indicates whether to use the element values that are observed by the agent.
    """

    return len(shared_elements(objects, entity, elements, only_seen, True)) == 0


def find_similar_objs(objects, entity, elem, only_seen=False):
    """ Finds objects that are similar to the <entity> based on a single element. An element can be
        a property or an attribute.
        only_seen indicates whether to look for objects whose element values are observed by the agent.
    """
    similar_objs = []
    for other in objects:
        if only_seen:
            if (elem in other.prop_seen and entity.prop_seen[elem] == other.prop_seen[elem]) or elem in other.attr_seen:
                similar_objs.append(other)
        else:
            if (elem in other.properties and entity.properties[elem] == other.properties[elem]) or elem in other.attributes:
                similar_objs.append(other)

    return similar_objs


def add_prop_seen(kb_state, ent, pkey, pval):
    """ If one of the agents observes that the entity's property key equals the property value,
        the (pkey, pval) pair is added to the entity.prop_seen field.
    """
    old_val = ent.prop_seen.get(pkey)

    ent.prop_seen[pkey] = pval

    def undo(old_value=old_val, entity=ent, prop_key=pkey):
        if old_value is None:
            del entity.prop_seen[prop_key]
        else:
            entity.prop_seen[prop_key] = old_value

    kb_state.undo_changes.append(undo)


def remove_prop_seen(kb_state, ent, pkey):
    """ If one of the agents observes that the entity's property key no longer equals its current property value,
        the property key gets removed from the prop_seen field.
        For example, if the color of the chair is no longer white and the agent observes this,
        it gets removed.
    """
    if pkey in ent.prop_seen:
        old_val = ent.prop_seen[pkey]
        del ent.prop_seen[pkey]

        def undo(entity=ent, prop_key=pkey, old_value=old_val):
            entity.prop_seen[prop_key] = old_value
        kb_state.undo_changes.append(undo)


def add_prop_seen_neg(kb_state, ent, pkey, pval):
    """ If one of the agents observes that the entity's property does not equal the property value,
        it gets added to the prop_seen_neg field.
        For example, if Andy's nickname is no longer 'cuddle bunny', it will be written in this field. 
    """
    if pkey not in ent.prop_seen_neg:
        ent.prop_seen_neg[pkey] = list()

        def undo_set(entity=ent, prop_key=pkey):
            del entity.prop_seen_neg[prop_key]

        kb_state.undo_changes.append(undo_set)

    if pval not in ent.prop_seen_neg[pkey]:
        ent.prop_seen_neg[pkey].append(pval)

        def undo_neg_val(entity=ent, prop_key=pkey, prop_val=pval):
            entity.prop_seen_neg[prop_key].remove(prop_val)

        kb_state.undo_changes.append(undo_neg_val)


def remove_prop_seen_neg(kb_state, ent, pkey, pval):
    """ If one of the agents observes that the entity's property key is equal to the property value,
        the value gets removed from the prop_seen_neg field. For example, let's say that the agent observes
        the change of Otto's nickname to 'tuxedo'. If 'tuxedo' exists in the prop_seen_neg['nickname'] field
        from previous observations, it gets removed.
    """

    if pkey in ent.prop_seen_neg:
        if pval in ent.prop_seen_neg[pkey]:
            ent.prop_seen_neg[pkey].remove(pval)

            def undo(prop_val=pval, entity=ent):
                entity.prop_seen_neg[pkey].append(prop_val)

            kb_state.undo_changes.append(undo)


def add_attr_seen(kb_state, ent, attr, neg):
    """ It adds the attr to the :attr:`ent.attr_seen <dialoguefactory.environment.entities.Entity.attr_seen>` or
        :attr:`ent.attr_seen_neg <dialoguefactory.environment.entities.Entity.attr_seen_neg>` depending on
        whether the agent observes one of the following information:

            - The <entity> is <attr>.
            - The <entity> is not <attr>.

    """
    if neg is None:
        attr_seen = ent.attr_seen
    else:
        attr_seen = ent.attr_seen_neg

    if attr not in attr_seen:
        attr_seen[attr] = None

        def undo(attribute=attr, ent_attr_seen=attr_seen):
            del ent_attr_seen[attribute]

        kb_state.undo_changes.append(undo)


def remove_attr_seen(kb_state, ent, attr, neg):
    """ It removes the attr from the :attr:`ent.attr_seen <dialoguefactory.environment.entities.Entity.attr_seen>` or
        :attr:`ent.attr_seen_neg <dialoguefactory.environment.entities.Entity.attr_seen_neg>`.
        This can happen if the agent observes an updated version of the entity's attribute.
        For example, if the door is no longer open and the agent observes this,
        the 'open' attribute is removed from the attr:`ent.attr_seen <dialoguefactory.environment.entities.Entity.attr_seen>`.
    """
    if neg is None:
        attr_seen = ent.attr_seen
    else:
        attr_seen = ent.attr_seen_neg

    if attr in attr_seen:
        del attr_seen[attr]

        def undo(attribute=attr, ent_attr_seen=attr_seen):
            ent_attr_seen[attribute] = None

        kb_state.undo_changes.append(undo)

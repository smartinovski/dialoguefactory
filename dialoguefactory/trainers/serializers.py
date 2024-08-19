#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module offers functions for serializing a Sentence to a list of strings and
deserializing a list of strings to a Sentence.
"""
from ..language import components as lc
from ..environment import entities as emm


def serialize(elem, world):
    """
    Serializes an object into a list of tokens.

    The serialization is done in such a way that only the meaning of the sentence is represented and the
    syntactic structure is ignored.

    For each object type, the serialization is done as follows:

        - Sentence: serializes the describers that represent the semantics.
        - Describer: serializes the arguments in the following manner:

          ..

            b<ArgKey> <serialized argument value> e<ArgKey>

        - set or list: serializes each of the elements recursively and uses bset/eset or blist/elist to indicate
          the beginning or end of the serialization.
        - Entity: serializes the Entity's description.
        - all other: adds the element in the list of serialized objects.

    For the following sentence: "Hans has the red apple and the chicken."
    the sentence object can be created using sentences.have(world.player, "has", None, [world.small_apple, world.chicken])
    The sentence object will be serialized as a list of tokens:

    ..  code-block:: python

        ['bsent',
          'bdesc',
            'bArg-PAG', 'bentity', 'small', 'person', 'eentity', 'eArg-PAG',
            'bRel', 'have', 'eRel',
            'bArg-PPT', 'blist', 'bentity', 'red', 'apple', 'eentity', 'bentity', 'chicken', 'eentity', 'elist', 'eArg-PPT',
          'edesc',
         'esent']

    The indents are there just to better visualize the serialization.

    Parameters
    ----------
    elem : any
        The object to be serialized.
    world : World
        The simulated world.

    Returns
    -------
    cmds : list of strings
        The serialized object.

    """
    cmds = []

    if isinstance(elem, lc.Sentence):
        cmds.append('bsent')
        for desc in elem.describers:
            cmds += serialize(desc, world)
        cmds.append('esent')
    elif isinstance(elem, lc.Describer):
        cmds.append('bdesc')
        for argk, argv in elem.args.items():
            cmds.append('b'+argk)
            if argk == 'Rel':
                val = argv.infinitive
            else:
                val = argv.value
            cmds += serialize(val, world)
            cmds.append('e'+argk)
        cmds.append('edesc')
    elif isinstance(elem, list):
        cmds.append('blist')
        for lelem in elem:
            cmds += serialize(lelem, world)
        cmds.append('elist')
    elif isinstance(elem, set):
        cmds.append('bset')
        for lelem in elem:
            cmds += serialize(lelem, world)
        cmds.append('eset')
    elif isinstance(elem, emm.BaseEntity):
        cmds.append('bentity')
        elem_vals = []
        if elem.description is not None:
            description = elem.description
        else:
            description = elem.generate_description()
        for delem in description.elements:
            if delem in elem.properties:
                if not isinstance(elem.properties[delem], list):
                    elem_vals.append(elem.properties[delem])
                else:
                    elem_vals.extend(serialize(elem.properties[delem], world))
            elif delem in elem.attributes:
                elem_vals.append(delem)
        if 'abstract' in elem.attributes and 'abstract' not in description.elements:
            elem_vals.append('abstract')
        cmds += elem_vals
        cmds.append('eentity')
    else:
        cmds.append(elem)

    return cmds


def deserialize(cmds, world, stack=None):
    """
    Parses a list of tokens (strings) and converts them into an instance of type Sentence.

    The parsing is done in the following manner:
    Each time a beginning token is encountered, the corresponding object instance is created and added to a stack.
    The beginning keyword indicates that the next few tokens belong to the object instance, and those tokens
    are attached to the object instance using the attach_to_element function.
    When the end keyword is encountered, the object instance is attached to a parent object
    if it exists.

    Please check the serialize function for an example of serializing a Sentence object. The deserialization
    just reverses this process; it converts the list into a Sentence object.

    Parameters
    ----------
    cmds : list
        A list of tokens/strings to be deserialized into an object.
    world : World
        The simulated world.
    stack : list, optional
        The stack is used for parsing the tokens.

    Raises
    ------
    Exception
        An exception is raised if there is an error during the parsing.

    Returns
    -------
    last_sent : Sentence
        The parsed sentence.

    """
    if stack is None:
        stack = []
    for cmd in cmds:
        if cmd is None:
            attach_to_element(stack[-1], cmd, world)
        elif cmd == 'bsent':
            stack.append(lc.Sentence())
        elif cmd == 'esent':
            if isinstance(stack[-1], lc.Sentence):
                if len(stack) > 1:
                    attach_to_element(stack[-2], stack[-1], world)
                last_sent = stack[-1]
                del stack[-1]
                if len(stack) == 0:
                    return last_sent
            else:
                raise Exception('The last element in the stack should be a lc.Sentence.\nThe stack is:'.format(stack))
        elif cmd == 'bdesc':
            new_desc = lc.Describer()
            stack.append(new_desc)
        elif cmd == 'edesc':
            if isinstance(stack[-1], lc.Describer):
                attach_to_element(stack[-2], stack[-1], world)
                del stack[-1]
            else:
                raise Exception('The last element in the stack should be a lc.Describer\nThe stack is:'.format(stack))
        elif cmd.startswith('bArg-') or cmd.startswith('bAM-') or cmd == 'bRel':
            if isinstance(stack[-1], lc.Describer):
                if cmd == 'bRel':
                    new_arg = lc.RelArg()
                else:
                    new_arg = lc.Arg()
                stack[-1].args[cmd[1:]] = new_arg
                stack.append(new_arg)
            else:
                raise Exception('The last element in the stack should be a lc.Sentence.\nThe stack is:'.format(stack))
        elif cmd.startswith('eArg-') or cmd.startswith('eAM-') or cmd == 'eRel':
            if isinstance(stack[-1], lc.Arg):
                del stack[-1]
            else:
                raise Exception('The last element in the stack should be a lc.Arg.\nThe stack is:'.format(stack))
        elif cmd.startswith('blist'):
            stack.append(list())
        elif cmd.startswith('elist'):
            if isinstance(stack[-1], list):
                attach_to_element(stack[-2], stack[-1], world)
                del stack[-1]
            else:
                raise Exception('The last element in the stack should be type list.\nThe stack is:'.format(stack))
        elif cmd.startswith('bset'):
            stack.append(set())
        elif cmd.startswith('eset'):
            if isinstance(stack[-1], set):
                attach_to_element(stack[-2], stack[-1], world)
                del stack[-1]
            else:
                raise Exception('The last element in the stack should be type set.\nThe stack is:'.format(stack))
        elif cmd.startswith('bentity'):
            stack.append(emm.BaseEntity())
        elif cmd.startswith('eentity'):
            if isinstance(stack[-1], emm.BaseEntity):
                if 'abstract' not in stack[-1].attributes:
                    entities_found = world.query_entity_from_db(stack[-1])
                else:
                    entities_found = [emm.BaseEntity(properties=stack[-1].properties,
                                                     attributes=stack[-1].attributes)]

                if len(entities_found) == 1:
                    del stack[-1]
                    attach_to_element(stack[-1], entities_found[0], world)
                else:
                    raise Exception("There is no unique entity with the following properties: {0} and the following "
                                    "attributes: {1} found in the world.".format(stack[-1].properties,
                                                                                 stack[-1].attributes))
            else:
                raise Exception(
                    "The last element in the stack should be an instance of BaseEntity.\nThe stack is:".format(stack))

        else:
            attach_to_element(stack[-1], cmd, world)


def attach_to_element(elem, elem_to_attach, world):
    """ Attaches a child element (elem_to_attach) to a parent element (elem).
    """
    if isinstance(elem, list):
        elem.append(elem_to_attach)
    elif isinstance(elem, lc.Arg):
        elem.value = elem_to_attach
        if isinstance(elem, lc.RelArg):
            elem.infinitive = elem.compute_infinitive()
    elif isinstance(elem, emm.BaseEntity):
        elem_attached = False
        for desc in world.all_description_objects:
            for celem in desc.cand_elements:
                if elem_to_attach in world.all_attributes or elem_to_attach == 'abstract':
                    elem.attributes[elem_to_attach] = None
                    elem_attached = True
                elif elem_to_attach in getattr(world, celem+"s"):
                    elem.properties[celem] = elem_to_attach
                    elem_attached = True
        if elem_attached is False:
            raise Exception("{0} is not recognized as a property value nor as an attribute.".format(elem_to_attach))

    elif isinstance(elem, lc.Sentence):
        elem.describers.append(elem_to_attach)

    elif isinstance(elem, set):
        elem.add(elem_to_attach)


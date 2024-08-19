#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides the classes that represent the language elements like word, phrase or sentence. Moreover, it
contains the classes needed for the PropBank arguments.
"""
import logging
import spacy
import pyinflect
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    print('Downloading the language model for SpaCy\n(this will only happen once)')
    spacy.cli.download('en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')

logger = logging.getLogger(__name__)

PRESENT_TENSES = ['VB', 'VBP', 'VBZ']
PAST_TENSES = ['VBD']
PRESENT_PARTICIPLE_TENSES = ['VBG']
PAST_PARTICIPLE_TENSES = ['VBN']
cached_tokens = {}
cached_inflections = {}


def retrieve_token(verb):
    """ Caches the verb (str) as a `spacy.tokens.token.Token <https://spacy.io/api/token#Token>`_.
        Caching saves time computing nlp(verb).

        If the verb is mistakenly tagged as something else, we find the correct tag by
        going through all inflections.
        If the verb is already cached, the token is returned.
    """
    if verb not in cached_tokens:
        tokens = nlp(verb)
        cached_tokens[verb] = tokens[0]
        token = tokens[0]
        if token.pos_ != 'VERB':
            token.pos_ = 'VERB'
            verb_infinitive = token._.inflect('VB')
            # compute the tag
            for key, val in pyinflect.getAllInflections(verb_infinitive).items():
                if key.startswith('V') and verb in val:
                    token.tag_ = key
                    break
    else:
        token = cached_tokens[verb]

    return token


def retrieve_inflection(verb, tag):
    """ Caches the verb's inflection based on the tag. The tag can be VB, VBD, VBG, VBN, VBP, VBZ.
        If the inflection is already cached, the token is returned.
    """
    if (verb, tag) not in cached_inflections:
        cached_inflections[(verb, tag)] = retrieve_token(verb)._.inflect(tag)
    infl = cached_inflections[(verb, tag)]
    return infl


def verb_inf(verb):
    """ Finds the infinite form of the verb. """
    return retrieve_inflection(verb, 'VB')


def verb_tense(verb):
    """ Returns the Part-of-speech (POS) tag of the verb.
        We use the POS tag to determine the tense of the verb. """
    token = retrieve_token(verb)
    return token.tag_


def conjugate_verb(verb):
    """
    Converts the verb first into its base form and later into its tense form.
    For example, for the verb "goes," the result is the verb "go".

    Parameters
    ----------
    verb : str
        The verb to be conjugated.

    Returns
    -------
    conjugated_verb : str
        The conjugated verb.

    """
    upper_flag = False
    if verb[0].isupper():
        upper_flag = True
        verb = verb.lower()

    token = retrieve_token(verb)
    v_tense = token.tag_

    if v_tense in PRESENT_TENSES:
        conjugated_verb = retrieve_inflection(verb, 'VB')
    elif v_tense in PRESENT_PARTICIPLE_TENSES:
        conjugated_verb = retrieve_inflection(verb, 'VBG')
    elif v_tense in PAST_TENSES:
        conjugated_verb = retrieve_inflection(verb, 'VBD')
    elif v_tense in PAST_PARTICIPLE_TENSES:
        conjugated_verb = retrieve_inflection(verb, 'VBN')
    else:
        conjugated_verb = None
    if upper_flag:
        conjugated_verb = conjugated_verb.capitalize()
    return conjugated_verb


def prepare_hash(obj):
    """
    Recursively converts the dictionaries and the sets into frozen sets. The lists are also converted into tuples
    and the tuples are also prepared because some tuples might contain mutable objects like lists.
    """

    if isinstance(obj, dict):
        new_dict = dict()
        for key, val in obj.items():
            new_dict[key] = prepare_hash(val)
        prepared_obj = frozenset(new_dict.items())
    elif isinstance(obj, set):
        new_set = set()
        for elem in obj:
            new_set.add(prepare_hash(elem))
        prepared_obj = frozenset(new_set)
    elif isinstance(obj, (list, tuple)):
        new_list = []
        for elem in obj:
            new_list.append(prepare_hash(elem))
        prepared_obj = tuple(new_list)
    else:
        prepared_obj = obj

    return prepared_obj


class Arg:
    """
    The Arg class stores the `PropBank argument <https://propbank.github.io/>`_.

    Attributes
    ----------
    value : any
        The value of the argument carries the semantics of the PropBank argument.
        For example, in the sentence "Andy sees the small ball,
        the big ball, and the red toy.", the Arg-PPT's value is [small_ball, big_ball, red_toy].
        The connectors between the items are not important for the semantics and are left out in the
        value but included in the part. Please find more information about how the values are computed in our `paper <https://rgdoi.net/10.13140/RG.2.2.17884.19846>`_.
    part : Union[Word, Phrase, Sentence, list, set], optional
       The language part carries the syntax of the PropBank argument. It includes all words and connectors that appear
       in the sentence. For the example above, the language part of Arg-PPT is:

       ..  code-block:: python

           [lc.Phrase([lc.Word('the'), lc.Word('small'), lc.Word('ball')]), lc.Word(",") ... ]

    """
    def __init__(self, value=None, part=None):

        self.value = value
        self.part = part

    def __eq__(self, other):
        """ Checks whether two arguments are equal. Since the values carry the meanings of the arguments,
            they are compared.
        """
        if isinstance(other, Arg):
            if self.value == other.value:
                return True

        return False

    def mycopy(self, memo):
        """ Copies the self.value and the self.part. The memo is used in order to prevent
            copying the same member in case there is a circular relationship between
            two members.
        """
        self_id = id(self)
        result = memo.get(self_id)
        if result is not None:
            return result
        cls = self.__class__
        result = cls.__new__(cls)
        memo[self_id] = result

        result.part = mycopy_el(self.part, memo)
        result.value = mycopy_el(self.value, memo)

        return result

    def __hash__(self):
        """ Computes the hash of the argument. """
        return hash(prepare_hash(self.value))


class RelArg(Arg):
    """
    Argument for the verb in the sentence (PropBank Arg-Rel).
    The addition to the Arg class is the infinitive which is useful
    for comparing two arguments regardless of the conjugated form of the verb.
    The verb tense is still preserved.
    """
    def __init__(self, value=None, part=None):

        super().__init__(value, part)
        self.infinitive = self.compute_infinitive()

    def mycopy(self, memo):
        result = super().mycopy(memo)
        result.infinitive = self.infinitive

        return result

    def compute_infinitive(self):
        """ Computes the infinitive of the verb and conjugates it in its tense form. """
        return conjugate_verb(self.value) if self.value is not None else None

    def __eq__(self, other):
        """ Checks if two verbs are equal. The result is True if
            both of the verb infinitives are equal since the verb form does not contribute to the semantics of the word.
        """
        if isinstance(other, RelArg):
            return self.infinitive == other.infinitive
        return False

    def __hash__(self):
        """ Computes the hash value based on the verb infinitive  """
        return hash(self.infinitive)


class Describer:
    """
    The describer represents the list of PropBank arguments extracted from a
    sentence.

    The dictionary is used to store the args, so they can be quickly fetched by their name.
    An example of annotating the sentence "Hans has the small ball and the red ball" is:

    ..  code-block:: python

        args['Arg-PPT'] = Arg(world.player2)
        args['Rel'] = RelArg('has')
        args['Arg-PRD'] = Arg([world.small_ball, world.red_ball])

    Additionally, the language parts can be added to the arg by calling helpers.convert_obj_to_part.

    To see how to annotate the sentence, please check the
    `PropBank guidelines <https://raw.githubusercontent.com/propbank/propbank-documentation/master/annotation-guidelines/Propbank-Annotation-Guidelines.pdf>`_.

    For automatic semantic labeling, you can check the `Verbnet Parser <https://verbnetparser.com/>`_.
    Additionally, we modified the argument keys such that
    the numbers in the names of PropBank arguments are ignored so that the order of
    the arguments is no longer important. This way, the grammatical structure of the
    sentence is left out, and the focus is strictly on the semantics.
    Please check our `paper <https://rgdoi.net/10.13140/RG.2.2.17884.19846>`_ to see all the modifications that we did.

    Attributes
    ----------
    args : dict
        The dictionary of arguments.
    """
    def __init__(self, args=None, prune=True):

        self.args = args if args is not None else dict()
        if prune:
            self.prune_none_args()

    def __eq__(self, other):
        """ Checks whether two describers are equal by comparing their args """
        if isinstance(other, Describer):
            if self.args == other.args:
                return True
        return False

    def mycopy(self, memo):
        """
        Copies the members of the class Describer. The memo serves to prevent
        copying the same member in case there is a circular relationship between
        two members.
        """
        self_id = id(self)
        result = memo.get(self_id)

        if result is not None:
            return result

        cls = self.__class__
        result = cls.__new__(cls)
        memo[self_id] = result
        result.args = mycopy_el(self.args, memo)

        return result

    def __hash__(self):
        """
        Computes the hash by converting the self.args dictionary into a frozen set.
        """
        return hash(frozenset(self.args.items()))

    def prune_none_args(self):
        """ Removes the args that have value None """
        args = dict()
        for key, arg in self.args.items():
            if arg is not None and arg.value is not None:
                args[key] = arg

        self.args.clear()
        self.args.update(args)

    def get_arg(self, key, _type=1):
        """
        Gets the argument from self.args

        Parameters
        ----------
        key : str
            The key is used to fetch the argument from the dictionary.
            The argument keys either start with Arg- (for the main args)
            or AM- (for the modifier args). The `PropBank <https://propbank.github.io/>`_
            contains the full list of argument types.

        _type : int, optional
            The type indicates whether the whole argument is fetched (type=0),
            the value (type=1) or just the part(type=2)

        Returns
        -------
        res : any
            The desired argument.

        """
        arg = self.args.get(key)
        if arg is None:
            return None
        res = None
        if _type == 0:
            res = arg
        elif _type == 1:
            res = arg.value
        elif _type == 2:
            res = arg.part

        return res


class Word:
    """
    A class that represents a word.

    Attributes
    ----------
    string_value : str
        A single word.
    meta_sent : list, optional
        A list of sentences that describe the word or provide additional information.
        An example can be the word 'red', and the meta sentence can be
        Red is a color.
        It can also be used to clarify the meaning of the word based on the context.
    customizers : dict, optional
        Dictionary with the key being the customizer name and
        the value being an object of type Customizer.
        The customizers can transform the word into a different word or conjugated form of the word.
        An example of a word customizer can be a verb conjugator.
    """
    def __init__(self, string_value, meta_sent=None, customizers=None):
        self.string_value = '' if string_value is None else string_value
        self.meta_sent = list() if meta_sent is None else meta_sent
        self.customizers = dict() if customizers is None else customizers

    def mycopy(self, memo):
        """ Copies the members of the class Word. The memo serves to prevent
            copying the same member in case there is a circular relationship between
            two members.
        """
        self_id = id(self)
        result = memo.get(self_id)
        if result is not None:
            return result
        cls = self.__class__
        result = cls.__new__(cls)
        memo[self_id] = result

        result.string_value = self.string_value
        result.meta_sent = mycopy_el(self.meta_sent, memo)
        result.customizers = mycopy_el(self.customizers, memo)

        return result

    def run_customizer(self, customizer_name, additional_params=None):
        """
        Runs the customizer with parameters (if present) that replace the customizer
        default ones.
        """
        if customizer_name not in self.customizers:
            return None

        return self.customizers[customizer_name].run(additional_params)

    def to_string(self):
        """ Converts the Word object into string """
        return self.string_value


class Phrase:
    """
    A class that represents a phrase. The phrase lacks both a subject and a verb.

    Attributes
    ----------
    parts : list
        A list of instances of type Word and Phrase. An example of a phrase containing another phrase
        is "under the old wooden table," where the "old wooden table" is the embedded phrase.
    meta_sent : list, optional
        The meta-sentences provide additional information that can be inferred from the phrase itself or the context
        where the phrase is used.
        For the example above, the meta-sentence can be "The old wooden table's material is not plastic."
    customizers : dict, optional
        Dictionary with the key being the customizer name and
        the value being an object of type Customizer.
        The customizer transforms the phrase into a different one. An example
        is 'the red door', which can be transformed into 'the wooden door'.

    """
    def __init__(self, parts=None, meta_sent=None, customizers=None):

        self.parts = list() if parts is None else parts
        self.meta_sent = list() if meta_sent is None else meta_sent
        self.customizers = dict() if customizers is None else customizers
        self.remove_nones()

    def mycopy(self, memo):
        """ Copies all the attributes of the class Phrase recursively. """
        self_id = id(self)
        result = memo.get(self_id)
        if result is not None:
            return result

        cls = self.__class__
        result = cls.__new__(cls)
        memo[self_id] = result

        result.parts = mycopy_el(self.parts, memo)
        result.meta_sent = mycopy_el(self.meta_sent, memo)
        result.customizers = mycopy_el(self.customizers, memo)

        return result

    def remove_nones(self):
        """
        Remove the words from the list of parts that are None.
        Moreover, if the parts contain another list, merge it with the original one.
        """
        list_of_words = []
        for word in self.parts:
            if word is not None:
                if not isinstance(word, list):
                    list_of_words.append(word)
                else:
                    for inner_word in word:
                        if inner_word is not None:
                            list_of_words.append(inner_word)

        del self.parts[:]
        self.parts += list_of_words

    def run_customizer(self, customizer_name, replace_params=None):
        """ Run customizer with parameters (if present) that replace the customizer
            default ones.
        """
        if customizer_name not in self.customizers:
            return None

        return self.customizers[customizer_name].run(replace_params)

    def to_string(self):
        """
        Converts the phrase into a string.
        """
        outputs = []

        for part in self.parts:
            try:
                part_str = part.to_string()
            except Exception as err:
                logger.error("The following element: "+str(part)+", can not be converted to string.")
                logger.error(err, exc_info=True)
                part_str = []
            if isinstance(part_str, list):
                outputs.extend(part_str)
            else:
                outputs.append(part_str)

        return ' '.join(outputs)


class Sentence(Phrase):
    """
    A class that represents a phrase. The sentence contains both a subject and a verb.

    Attributes
    ----------
    describers : list, optional
        A list of describers that represent the PropBank annotation of the sentence.
        If the sentence is compound, it has more than one verb and, therefore, more than one describer.
    speaker : Entity, optional
        The person who utters the sentence.
    trusted_source : bool, optional
        The trusted source indicates whether the information the sentence conveys can be trusted.
        For example, if the machine learning model is imperfect, the utterances can not be trusted.
    """

    def __init__(self, parts=None, meta_sent=None, customizers=None,
                 describers=None, speaker=None, trusted_source=None):
        super().__init__(parts, meta_sent, customizers)
        self.describers = list() if describers is None else describers
        self.speaker = speaker
        self.trusted_source = True if trusted_source is None else trusted_source

    def __eq__(self, other):
        """ Checks if two sentences are the same. If the set of describers is the same,
            then the sentences are the same. """
        if isinstance(other, Sentence):
            if self.describers == other.describers:
                return True
        return False

    def mycopy(self, memo):
        """ Copies the speaker and the describers of the Sentence. """
        self_id = id(self)
        result = memo.get(self_id)
        if result is not None:
            return result

        result = super().mycopy(memo)

        result.trusted_source = self.trusted_source
        result.speaker = mycopy_el(self.speaker, memo)
        result.describers = mycopy_el(self.describers, memo)

        return result

    def __hash__(self):
        """ Calculates the hash value of the sentence. """
        return hash(tuple(self.describers))

    def reduce(self):
        """
        Calls the "reduce" customizer if present.
        If not, the same sentence is returned.

        The "reduce" customizer is applied if you want to simplify the sentence so that
        each describer argument has the least amount of elements.

        For example, the sentence "Andy has the red ball and the small ball" can be reduced to
        two sentences: "Andy has the red ball" and "Andy has the small ball".
        The third describer argument Arg-PPT had [red_ball, small_ball] reduced
        to two sentences that have a single value in the Arg-PPT.

        """
        res = self
        if 'reduce' in self.customizers:
            res = self.customizers['reduce'].run()

        return res


class Customizer:
    """
    The customizer uses a function to modify the Word, Phrase, or Sentence.

    Attributes
    ----------
    func : function
        The function used for customizing.
    func_params : dict
        The function parameters needed for the function.

    """

    def __init__(self, func, func_params):
        self.func = func
        self.func_params = func_params

    def run(self, custom_params=None):
        """
        Runs the customizer by invoking self.func with the function parameters. (self.func_params)
        The custom_params can temporarily replace some func_params.
        """
        final_params = dict()
        final_params.update(self.func_params)
        if custom_params is not None:
            final_params.update(custom_params)
        return self.func(**final_params)

    def mycopy(self, memo):
        """ Copies the func_params dictionary recursively. """
        self_id = id(self)
        result = memo.get(self_id)
        if result is not None:
            return result

        cls = self.__class__
        result = cls.__new__(cls)
        memo[self_id] = result
        result.func = self.func
        result.func_params = mycopy_el(self.func_params, memo)

        return result


def mycopy_el(elem, memo):
    """
    Copy the elements that contain the mycopy function.
    If the element is a list, set, dict then the copying is done recursively.

    Parameters
    ----------
    elem : Union[set, dict, list, objects containing mycopy]
        The element to be copied.
    memo : dict
        The dictionary memorizes whether an element has been copied already.
        This is done in case there are cyclic relations between two objects.

    Returns
    -------
    copied_el : Union[set, dict, list, objects containing mycopy]
        The copied element.

    """
    el_id = id(elem)

    copied_el = memo.get(el_id)
    if copied_el is None:

        if callable(getattr(elem, "mycopy", None)):
            copied_el = elem.mycopy(memo)

        elif isinstance(elem, set):
            copied_el = set()
            memo[el_id] = copied_el

            for ell in elem:
                copied_ell = mycopy_el(ell, memo)
                copied_el.add(copied_ell)
        elif isinstance(elem, dict):
            copied_el = dict()

            memo[el_id] = copied_el
            for key, val in elem.items():
                copied_val = mycopy_el(val, memo)
                copied_el[key] = copied_val
        elif isinstance(elem, list):
            copied_el = []
            memo[el_id] = copied_el

            for ell in elem:
                copied_ell = mycopy_el(ell, memo)
                copied_el.append(copied_ell)
        else:
            memo[el_id] = elem
            copied_el = elem

    return copied_el

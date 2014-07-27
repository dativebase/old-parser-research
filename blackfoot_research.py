#!/home/joel/env/bin/python
# coding=utf8

# Copyright 2013 Joel Dunham
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Blackfoot Research --- a script that tries to create effective morphological
parsers for the Blackfoot language.

WARNING: THERE IS A LOT OF JUNKY ONCE-OFF CODE IN HERE. PERHAPS USEFUL FOR SOME
IDEAS, BUT DEFINITELY NOT QUALITY STUFF!

The point of this script, beyond any empirical/theoretical linguistic findings
that it might facilitate, is to demonstrate practical and theory-relevant
interaction with a live OLD language-documenting OLD web service using only the
interface that it exposes and a means of local storage, both of which are
available in a client-side JavaScript program. The reliance here on local
``foma`` and ``evaluate-lm`` (i.e., MITLM) executables is motivated by
performance and is incidental to the feat itself. Of course, anybody with foma
and MITLM installed and contributor-level access to a live OLD application
could also make minor language/system-specific alterations to this script and
develop their parsers in that way.

.. note::

    This script assumes a database of Blackfoot and several blackfoot-specific
    foma phonology scripts. Without these, it will not work. However, these
    contain data that cannot be made publicly available and are not included
    in this library.

"""

import codecs
import cPickle
import os
import re
import time
import locale
import sys
import optparse
from researcher import ParserResearcher, Keeper, Log
import pprint
from pprint import PrettyPrinter
import random

pp = PrettyPrinter(indent=4)

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
# This allows piping of unicode output.
# See http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file
#sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

# The global ``log`` instance can be used instead of ``print`` and output can be
# silenced by setting ``log.silent`` to ``True``.
log = Log()

class BlackfootParserResearcher(ParserResearcher):
    """Researches the creation of effective morphological parsers for Blackfoot.

    Warning, there are a lot of Blackfoot-specific assumptions and values in 
    this script. It may be useful as an example.

    This class has several Blackfoot OLD-specific methods for doing parser-
    related research. In general, it creates OLD objects on the OLD web service
    to which it connects (form searches, corpora, phonologies, morphologies, LMs,
    parsers) and it saves large datasets to pickle objects in localstore/ and 
    smaller data structures to record.pickle.

    """

    # Blackfoot OLD syntactic category name values that correspond to lexical items.
    lexical_category_names = ['nan', 'nin', 'nar', 'nir', 'vai', 'vii', 'vta',
            'vti', 'vrt', 'adt', 'drt', 'prev', 'med', 'fin', 'oth', 'o',
            'und', 'pro', 'asp', 'ten', 'mod', 'agra', 'agrb', 'thm', 'whq',
            'num', 'stp', 'PN']

    def create_lexicon_search(self, force_recreate=False):
        """Create a form search that returns Blackfoot lexical items.

        The code below constructs a query that finds a (large) subset of the
        Blackfoot morphemes.

        Notes for future morphology creators:
        1. the "oth" category is a mess: detangle the nominalizer, inchoative,
           transitive suffixes, etc. from one another and from the numerals and
           temporal modifiers -- ugh!

        2. the "pro" category" is also a mess: clearly pronoun-forming iisto
           does not have the same distribution as the verbal suffixes aiksi and
           aistsi!  And oht, the LING/means thing, is different again...

        3. hkayi, that thing at the end of demonstratives, is not agra, what is
           it? ...

        4. the dim category contains only 'sst' 'DIM' and is not used in any
           forms ...

        """

        name = u'Blackfoot morphemes'
        key = 'searches'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Form search "%s" has already been created.' % name)
            return record
        not_complex_conjunct = ['not', ['Form', 'morpheme_break', 'regex', '[ -]']]
        durative_morpheme = 15717
        hkayi_morpheme = 23429
        exclusions = ['not', ['Form', 'id', 'in', [durative_morpheme,
            hkayi_morpheme]]]
        query = {'filter': ['and', [
            ['Form', 'syntactic_category', 'name', 'in', self.lexical_category_names],
            not_complex_conjunct, exclusions]]}
        search = self.create_search(name, query)
        log.info(u'Form search "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record.update(search)
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return search

    def create_sentence_search(self, force_recreate=False):
        """Create a form search that returns grammatical forms representing Blackfoot sentences.

        """

        name = u'Blackfoot sentences'
        key = 'searches'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Form search "%s" has already been created.' % name)
            return record
        query = {'filter': ['and', [
            ['Form', 'syntactic_category', 'name', '=', u'sent'],
            ['Form', 'grammaticality', '=', u'']]]}
        description = u'Returns all sentential Blackfoot forms.'
        search = self.create_search(name, query, description=description)
        log.info(u'Form search "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record.update(search)
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return search

    def create_analyzed_words_search(self, force_recreate=False, **kwargs):
        """Create a form search that returns forms containing *morphologically analyzed* words.

        The goal here is to exclude things that look like words but are not
        really words, i.e., morphemes; as a heuristic we search for grammatical
        forms categorized as 'sent' or whose transcription value contains a
        space or a hyphen-minus.

        The condition that the ``syntactic_category_string`` value is not NULL
        is what ensures that the words are analyzed: the OLD sets this value to
        None/NULL when there is no acceptable morphological analysis implicit
        in the form.

        """

        relation = kwargs.get('relation')
        attribute = kwargs.get('attribute')
        value = kwargs.get('value')
        relative_clause = u''
        if relation:
            relative_clause = u', with %s %s as %s,' % (
                relation, attribute, value)
        name = u'Forms%s containing analyzed words of Blackfoot' % relative_clause
        key = 'searches'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Form search "%s" has already been created.' % name)
            return record
        print '\n\n\nIN create_analyzed_words_search\n\n\n'
        conjuncts = [['or', [['Form', 'syntactic_category', 'name', '=', u'sent'],
                             ['Form', 'morpheme_break', 'like', '% %'],
                             ['Form', 'morpheme_break', 'like', '%-%']]],
                     ['Form', 'syntactic_category_string', '!=', None],
                     ['not', ['Form', 'syntactic_category_string', 'regex', '( |^|-)sent( |$|-)']],
                     ['Form', 'grammaticality', '=', '']]
        if relation:
            conjuncts.append(['Form', relation, attribute, '=', value])
        query = {'filter': ['and', conjuncts]}
        search = self.create_search(name, query)
        log.info(u'Form search "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record.update(search)
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return search

    def create_words_search(self, force_recreate=False, **kwargs):
        """Create a form search that returns forms containing words.

        The goal here is to exclude things that look like words but are not
        really words, i.e., morphemes; as a heuristic we search for grammatical
        forms categorized as 'sent' or whose transcription value contains a
        space or a hyphen-minus.

        Note that this search, in contrast to that returned by
        ``create_analyzed_words_search``, returns words both with and without
        morphological analyses.

        """

        relation = kwargs.get('relation')
        attribute = kwargs.get('attribute')
        value = kwargs.get('value')
        relative_clause = u''
        if relation:
            relative_clause = u', with %s %s as %s,' % (relation, attribute, value)
        name = u'Forms%s containing words of Blackfoot' % relative_clause
        key = 'searches'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Form search "%s" has already been created.' % name)
            return record
        conjuncts = [['Form', 'grammaticality', '=', ''],
                     ['not', ['Form', 'syntactic_category', 'name', 'in', self.lexical_category_names]],
                     ['or', [['Form', 'syntactic_category', 'name', '=', u'sent'],
                             ['Form', 'morpheme_break', 'like', '% %'],
                             ['Form', 'morpheme_break', 'like', '%-%']]]]
        if relation:
            conjuncts.append(['Form', relation, attribute, '=', value])
        query = {'filter': ['and', conjuncts]}
        search = self.create_search(name, query)
        log.info(u'Form search "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return search

    # Corpus creation methods
    ################################################################################

    def create_lexicon_corpus(self, force_recreate=False):
        """Create a corpus of Blackfoot morphemes.

        """

        name = u'Corpus of Blackfoot morphemes'
        key = 'corpora'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Corpus "%s" has already been created.' % name)
            return record
        lexicon_search = self.create_lexicon_search(force_recreate)
        corpus = self.create_corpus(name, search_id=lexicon_search['id'])
        log.info(u'Corpus "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        record.update(corpus)
        self.record[key][name] = record
        self.dump_record()
        return record

    def create_sentence_corpus(self, force_recreate=False):
        """Create a corpus of Blackfoot sentences.

        """

        name = u'Corpus of Blackfoot sentences'
        key = 'corpora'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Corpus "%s" has already been created.' % name)
            return record
        sentence_search = self.create_sentence_search(force_recreate)
        corpus = self.create_corpus(name, search_id=sentence_search['id'])
        log.info(u'Corpus "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return corpus

    def create_analyzed_words_corpus(self, force_recreate=False, **kwargs):
        """Create a corpus of forms containing *morphologically analyzed* words.

        """

        return self._create_analyzed_words_corpus(force_recreate, **kwargs)

    def create_well_analyzed_words_corpus(self, force_recreate=False, **kwargs):
        """Create a corpus of forms containing morphologically *well* analyzed words.

        """

        kwargs['adverb'] = u' well'
        return self._create_analyzed_words_corpus(force_recreate, **kwargs)

    def _create_analyzed_words_corpus(self, force_recreate=False, **kwargs):
        """Create a corpus of forms containing *morphologically analyzed* words.

        Note: this method is used to create multiple functionally identical
        corpora under different names.

        """

        relation = kwargs.get('relation')
        relative_clause = u''
        if relation:
            relative_clause = u', with %s %s as %s,' % (
                relation, kwargs['attribute'], kwargs['value'])
        adverb = kwargs.get('adverb', u'')
        name = u'Corpus of forms%s that contain%s analyzed Blackfoot words' % (
            relative_clause, adverb)
        key = 'corpora'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Corpus "%s" has already been created.' % name)
            return record
        words_search = self.create_analyzed_words_search(force_recreate, **kwargs)
        search_id = words_search['id']
        corpus = self.create_corpus(name, search_id=search_id)
        log.info(u'Corpus "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return corpus

    def create_words_corpus(self, force_recreate=False, **kwargs):
        """Create a corpus of forms containing words.

        """

        relation = kwargs.get('relation')
        relative_clause = u''
        if relation:
            relative_clause = u', with %s %s as %s,' % (
                relation, kwargs['attribute'], kwargs['value'])
        name = u'Corpus of forms%s that contain Blackfoot words' % relative_clause
        key = 'corpora'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Corpus "%s" has already been created.' % name)
            return record
        words_search = self.create_words_search(force_recreate, **kwargs)
        search_id = words_search['id']
        corpus = self.create_corpus(name, search_id=search_id)
        log.info(u'Corpus "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return corpus

    # Corpus saving methods
    ################################################################################

    def save_words_corpus(self, force_recreate=False, **kwargs):
        """Create the corpus of words and pickle it locally.

        """

        corpus = self.create_words_corpus(force_recreate=force_recreate, **kwargs)
        name = corpus['name']
        key = 'corpora'
        relation = kwargs.get('relation')
        suffix = u''
        if relation:
            suffix = u'_%s_%s' % (kwargs['value'].replace(' ', '')[:10].lower(), relation)
        filename = u'words%s.pickle' % suffix

        record = self.record.get(key, {}).get(name, {})
        if record.get('saved_locally') and not force_recreate:
            log.info(u'Corpus "%s" has already been saved locally.' % name)
            return record
        else:
            forms = self.get_corpus_forms(corpus)
            form_quads = self.get_form_words(forms)
            file_path = os.path.join(self.localstore, key, filename)
            cPickle.dump(form_quads, open(file_path, 'wb'))
            assert os.path.isfile(file_path)
            corpus.update({
                'saved_locally': True,
                'local_copy_path': file_path
            })
            record.update(corpus)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Corpus "%s" has been saved locally.' % name)
            return record

    def save_analyzed_words_corpus(self, force_recreate=False, **kwargs):
        """Create the analyzed words corpus and pickle it locally.

        """

        corpus = self.create_analyzed_words_corpus(
            force_recreate=force_recreate, **kwargs)
        name = corpus['name']
        key = 'corpora'
        relation = kwargs.get('relation')
        suffix = u''
        if relation:
            suffix = u'_%s_%s' % (kwargs['value'].replace(' ', '')[:10].lower(), relation)
        filename = u'analyzed_words%s.pickle' % suffix

        record = self.record.get(key, {}).get(name, {})
        if record.get('saved_locally') and not force_recreate:
            log.info(u'Corpus "%s" has already been saved locally.' % name)
            return record
        else:
            forms = self.get_corpus_forms(corpus)
            form_words = self.get_form_words(forms)
            file_path = os.path.join(self.localstore, key, filename)
            cPickle.dump(form_words, open(file_path, 'wb'))
            assert os.path.isfile(file_path)
            corpus.update({
                'saved_locally': True,
                'local_copy_path': file_path
            })
            record.update(corpus)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Corpus "%s" has been saved locally.' % name)
            return record

    def save_well_analyzed_words_corpus(self, force_recreate=False, **kwargs):
        """Create the well analyzed words corpus and pickle it locally.

        """

        corpus = self.create_well_analyzed_words_corpus(force_recreate=force_recreate, **kwargs)
        name = corpus['name']
        key = 'corpora'
        relation = kwargs.get('relation')
        suffix = u''
        if relation:
            suffix = u'_%s_%s' % (kwargs['value'].replace(' ', '')[:10].lower(), relation)
        filename = u'well_analyzed_words%s.pickle' % suffix

        record = self.record.get(key, {}).get(name, {})
        if record.get('saved_locally') and not force_recreate:
            log.info(u'Corpus "%s" has already been saved locally.' % name)
            return record
        else:
            forms = self.get_corpus_forms(corpus)
            form_words = self.get_form_words(forms, filter_=True)
            file_path = os.path.join(self.localstore, key, filename)
            cPickle.dump(form_words, open(file_path, 'wb'))
            assert os.path.isfile(file_path)
            corpus.update({
                'saved_locally': True,
                'local_copy_path': file_path
            })
            record.update(corpus)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Corpus "%s" has been saved locally.' % name)
            return record



    # Morphology creation methods
    ################################################################################

    def create_morphology_1(self, force_recreate=False):
        """All words in all sentential forms, no rich morpheme representations."""
        return self.create_morphology_by_rich_upper(force_recreate, rich_upper=False)

    def create_morphology_2(self, force_recreate=False):
        """All words in all sentential forms, rich morpheme representations."""
        return self.create_morphology_by_rich_upper(force_recreate, rich_upper=True)

    def create_morphology_dunham_enterer(self, force_recreate=False):
        """All well analyzed words entered by Dunham."""
        return self.create_morphology_x(force_recreate,
            name = 'Morphology based on well analyzed words entered by Joel Dunham',
            rc_func = 'create_dunham_enterer_well_analyzed_words_corpus',
            rich_upper = True)

    def create_morphology_frantz95_waw(self, force_recreate=False):
        """Create a morphology with Frantz & Russell (1995) as lexicon and morphotactic
        rules drawn from the well analyzed words in the data set.
        """
        print 'In create_morphology_frantz95_waw'
        name = 'Morphology with morphotactics drawn from well analyzed words in the data set.'
        lexicon_corpus = self.create_lexicon_corpus(force_recreate)
        rules_corpus_id = 369 # The "Corpus where each form is a representation of a unique well-analyzed word" as already been created; it's id is 369.
        #script_type = 'lexc'
        script_type = 'lexc'
        rich_upper = False
        rich_lower = False
        include_unknowns = False
        extract_morphemes_from_rules_corpus = False
        key = 'morphologies'

        morphology = self.create_morphology(
            name,
            lexicon_corpus_id=lexicon_corpus['id'],
            rules_corpus_id=rules_corpus_id,
            script_type=script_type,
            rich_upper=rich_upper,
            rich_lower=rich_lower,
            include_unknowns=include_unknowns,
            extract_morphemes_from_rules_corpus=extract_morphemes_from_rules_corpus
        )
        assert 'id' in morphology
        log.info(u'Morphology "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        if record.get('generate_succeeded') and not force_recreate:
            log.warn(u'Morphology "%s" already generated.' % name)
        else:
            old_generate_attempt = record.get('generate_attempt')
            morphology = self.generate_morphology(morphology['id'])
            assert old_generate_attempt != morphology['generate_attempt']
            morphology['generate_succeeded'] = True
            self.record[name] = morphology
            self.dump_record()
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        record.update(morphology)
        self.record[key][name] = record
        self.dump_record()
        return record

    def create_morphology_louie_elicitor(self, force_recreate=False):
        """All analyzed words elicited by Louie."""
        return self.create_morphology_x(force_recreate,
            name = 'Morphology based on words entered by Meagan Louie',
            rc_func = 'create_louie_elicitor_analyzed_words_corpus',
            lc_func = 'create_louie_elicitor_analyzed_words_corpus',
            extract_morphemes_from_rules_corpus = True,
            rich_upper = False,
            script_type = 'lexc')

    def create_morphology_weber(self, force_recreate=False):
        """All well analyzed words with rich upper and lower."""
        return self.create_morphology_x(force_recreate,
            name = 'Morphology with rich morpheme representations on both sides of the tape.',
            rc_func = 'create_weber_2013_well_analyzed_words_corpus',
            lc_func = 'create_weber_2013_well_analyzed_words_corpus',
            extract_morphemes_from_rules_corpus = True,
            rich_upper = True,
            rich_lower = True,
            script_type = 'lexc')

    def create_morphology_by_rich_upper(self, force_recreate=False, rich_upper=False):
        """Create a Blackfoot morphology using all of the words in all of the
        sentential forms in the database, defined by whether it employs rich
        morpheme representations.

        """

        name = u'Blackfoot morphology%s' % {False: u'',
            True: u', rich morpheme representations'}[rich_upper]
        return self.create_morphology_x(
            force_recreate,
            name=name,
            rich_upper=rich_upper
        )

    def create_morphology_x(self, force_recreate=False, **kwargs):
        """Create a Blackfoot morphology based on the parameters in kwargs.  The
        morphology's foma script is generated and the entire process is cached.

        kwargs must have a 'name' key; optional keys with defaults are 'lc_func',
        'rc_func', 'script_type' and 'rich_upper'.

        HERE!!!

        """

        name = kwargs['name']
        key = 'morphologies'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Morphology "%s" has already been created and generated.' % name)
            return record
        lexicon_corpus = getattr(self, kwargs.get('lc_func', 'create_lexicon_corpus'))(force_recreate)
        rules_corpus = getattr(self, kwargs.get('rc_func', 'create_sentence_corpus'))(force_recreate)
        script_type = kwargs.get('script_type', 'lexc')
        rich_upper = kwargs.get('rich_upper', False)
        rich_lower = kwargs.get('rich_lower', False)
        include_unknowns = kwargs.get('include_unknowns', False)
        extract_morphemes_from_rules_corpus = kwargs.get('extract_morphemes_from_rules_corpus', True)
        morphology = self.create_morphology(
            name,
            lexicon_corpus_id=lexicon_corpus['id'],
            rules_corpus_id=rules_corpus['id'],
            script_type=script_type,
            rich_upper=rich_upper,
            rich_lower=rich_lower,
            include_unknowns=include_unknowns,
            extract_morphemes_from_rules_corpus=extract_morphemes_from_rules_corpus
        )
        assert 'id' in morphology
        log.info(u'Morphology "%s" created.' % name)
        record = self.record.get(key, {}).get(name, {})
        if record.get('generate_succeeded') and not force_recreate:
            log.warn(u'Morphology "%s" already generated.' % name)
        else:
            old_generate_attempt = record.get('generate_attempt')
            morphology = self.generate_morphology(morphology['id'])
            assert old_generate_attempt != morphology['generate_attempt']
            morphology['generate_succeeded'] = True
            self.record[name] = morphology
            self.dump_record()
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        record.update(morphology)
        self.record[key][name] = record
        self.dump_record()
        return record

    def create_toy_morphology(self, force_recreate=False):
        """Create a toy Blackfoot morphology with a single rule: nan.

        """

        name = u'Blackfoot toy morphology'
        key = 'morphologies'
        rules = u'nan'
        script_type = 'regex'
        rich_upper = False

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Morphology "%s" has already been created and generated.' % name)
            return record

        lexicon_corpus = self.create_lexicon_corpus(force_recreate)
        morphology = self.create_morphology(name, lexicon_corpus_id=lexicon_corpus['id'],
            rules=rules, script_type=script_type, rich_upper=rich_upper)
        log.info(u'Morphology "%s" created.' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('generate_succeeded') and not force_recreate:
            log.warn(u'Morphology "%s" already generated.' % name)
        else:
            old_generate_attempt = record.get('generate_attempt')
            morphology = self.generate_morphology(morphology['id'], compile_=True)
            assert old_generate_attempt != morphology['generate_attempt']
            morphology['generate_succeeded'] = True
            self.record[name] = morphology
            self.dump_record()

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return morphology

    # Phonology creation methods
    ################################################################################

    def create_phonology_x(self, force_recreate=False, **kwargs):
        """Create a Blackfoot foma phonology.

        """

        name = kwargs['name']
        description = kwargs.get('description', u'')
        script_path = kwargs['script_path']
        compile_ = kwargs.get('compile_', True)
        script = codecs.open(script_path, mode='r', encoding='utf8').read()
        key = 'phonologies'

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Phonology "%s" has already been created.' % name)
            return record

        phonology = self.create_phonology(name, script, description=description)
        log.info(u'Phonology "%s" created.' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('compile_succeeded') and not force_recreate:
            log.warn(u'Phonology "%s" already generated.' % name)
        elif compile_:
            old_compile_attempt = record.get('compile_attempt')
            phonology = self.compile_phonology(phonology['id'])
            assert old_compile_attempt != phonology['compile_attempt']
            log.warn(phonology['compile_message'])
            log.warn(phonology['compile_succeeded'])
            assert phonology['compile_succeeded'] == True
            self.record[key][name] = phonology
            self.dump_record()

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return phonology

    def create_phonology_1(self, force_recreate=False):
        """Create a Blackfoot foma phonology based on Frantz's (1997) phonology.

        """

        name = u'Blackfoot phonology'
        description = u'A foma phonology script for Blackfoot adapted from Frantz (1997).'
        #script_path = 'resources/blackfoot_phonology.script'
        script_path = 'resources/blackfoot_phonology_frantz91.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def create_phonology_frantz91(self, force_recreate=False):
        """Create a Blackfoot foma phonology based on Frantz's (1991) phonology.

        """

        name = u'Blackfoot phonology from Frantz (1991)'
        description = u'A foma phonology script for Blackfoot adapted from Frantz (1991) with phonological and lexico-phonological rules.'
        script_path = 'resources/blackfoot_phonology_frantz91.script'
        #script_path = 'resources/blackfoot_phonology_frantz91_gold_tests.script' # This one is used to hackily try all of the gold standard forms as tests ...
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def create_phonology_frantz91_flattener(self, force_recreate=False):
        """Create a Blackfoot foma phonology based on Frantz's (1991) phonology 
        but which flattens prominence and length distinctions.

        """

        name = u'Blackfoot phonology from Frantz (1991) with prominence and length distinctions flattened'
        description = u'A foma phonology script for Blackfoot adapted from Frantz (1991) with phonological and lexico-phonological rules and with prominence and length distinctions flattened.'
        script_path = 'resources/blackfoot_phonology_frantz91_flattener.script'
        #script_path = 'resources/blackfoot_phonology_frantz91_flattener_gold_tests.script' # This one is used to hackily try all of the gold standard forms as tests ...
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def get_stems_by_initial_segment(self):
        """Throw-away function used to query all verb and noun stems and pickle them
        as a dict that can later be used in the REPL to count them according to their
        initial segment. Used in the dissertation to show that the vast majority of
        verb stems begin with a vowel, a semivowel or s.

        """

        stems = ['nan', 'nin', 'nar', 'nir', 'vta', 'vai', 'vti', 'vii']
        forms = self.old.search('forms',
            {'query': {'filter': ['Form', 'syntactic_category', 'name', 'in', stems]}})
        stems = {}
        for form in forms:
            stems.setdefault(form['syntactic_category']['name'], []).append(form['morpheme_break'])
        print len(stems)
        cPickle.dump(stems, open('stems.pickle', 'wb'))

    def create_phonology_2(self, force_recreate=False):
        """Create a Blackfoot foma phonology based on Frantz's (1997) phonology but
        with additional rules that attempt to capture the surface transcriptions of the
        "well analyzed words, with Dunham as enterer" corpus.

        """

        name = u'Phonology for the corpus of well analyzed words entered by Joel Dunham'
        description = (u'A foma phonology script for Blackfoot adapted from Frantz (1997) '
            u' with additional rules that attempt to generate the surface transcriptions '
            u' found in the words of the corpus of well analyzed words entered by Joel Dunham.')
        script_path = 'resources/blackfoot_phonology_dunham_enterer.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def create_phonology_3(self, force_recreate=False):
        """Create a Blackfoot foma phonology based on Frantz's (1997) phonology but
        with additional rules that attempt to encode the syllabification principles of
        Denzer-King (2009) / Weber (2013) as well as the accent placement principles of
        Weber (2013).

        """

        name = (u'Phonology attempting to predict accent placement in orthographically '
                u'transcribed Blackfoot words.')
        description = name
        script_path = 'resources/blackfoot_phonology_syllabification_accent.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def create_phonology_4(self, force_recreate=False):
        """Create a Blackfoot foma phonology built upon the dunham-enterer-tailored one 
        but which includes the massively over-generating `misspell` transducer.

        """

        name = u'Over-generating phonology with `misspell` transducer.'
        description = name
        script_path = 'resources/blackfoot_phonology_overgenerator.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

    def create_phonology_5(self, force_recreate=False):
        """Create a Blackfoot foma phonology that works with rich morpheme representations
        and uses the available categorial information to inform the transformations.

        """

        name = u'Phonology that works with rich morpheme representations.'
        description = name
        script_path = 'resources/blackfoot_phonology_weber_orthographic.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description, compile_=False)

    def create_syllabification_phonology(self, force_recreate=False):
        """Create a foma phonology that syllabifies Blackfoot words a la Denzer-King 2009.

        """

        name = u'Phonology for syllabifying Blackfoot words.'
        description = u'A foma phonology script for syllabifying Blackfoot words.'
        script_path = 'resources/syllabify.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)


    # Language model creation methods
    ################################################################################

    def create_language_model_x(self, name, force_recreate=False, **kwargs):
        """Create a morpheme language model with ``name`` and using the params in **kwargs.

        """

        key = 'language models'
        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'LM "%s" has already been created and generated.' % name)
            return record
        record = self.record.get(key, {}).get(name, {})
        categorial = kwargs.get('categorial', False)
        corpus = getattr(self, kwargs.get('corpus_func', 'create_analyzed_words_corpus'))(force_recreate)
        language_model = self.create_language_model(name, corpus['id'], toolkit='mitlm', categorial=categorial)
        log.info(u'%s created.' % name)
        if (language_model['generate_attempt'] == record.get('generate_attempt') and
            language_model['generate_succeeded'] == True and not force_recreate):
            log.info(u'Language model "%s" has already been generated.' % name)
        else:
            language_model = self.generate_language_model(language_model['id'])
            try:
                assert language_model['generate_succeeded'] == True
            except AssertionError:
                log.info(language_model['generate_message'])
            record.update(language_model)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'%s generated.' % name)
        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return language_model


    def create_gold_language_model(self):
        """Create five morpheme language models based on the five randomly shuffled 90%ers
        of the Gold Standard corpus:

        corpus #371 'Gold 1 training'.
        corpus #373 'Gold 2 training'.
        corpus #375 'Gold 3 training'.
        corpus #377 'Gold 4 training'.
        corpus #379 'Gold 5 training'.

        After this ran, I had:

        | 40 | Language model based on corpus "Gold 1 training". |
        | 41 | Language model based on corpus "Gold 2 training". |
        | 42 | Language model based on corpus "Gold 3 training". |
        | 43 | Language model based on corpus "Gold 4 training". |
        | 44 | Language model based on corpus "Gold 5 training".

        """

        for corpus_id, corpus_name in (
            (371, 'Gold 1 training'),
            (373, 'Gold 2 training'),
            (375, 'Gold 3 training'),
            (377, 'Gold 4 training'),
            (379, 'Gold 5 training')):
            categorial = False
            name = u'Language model based on corpus #371 "%s".' % corpus_name
            language_model = self.create_language_model(name, corpus_id, toolkit='mitlm', categorial=categorial)
            log.info(u'%s created.' % name)
            language_model = self.generate_language_model(language_model['id'])
            try:
                assert language_model['generate_succeeded'] == True
            except AssertionError:
                log.info(language_model['generate_message'])
            log.info(u'%s generated.' % name)



    def create_gold_language_model_categorial(self):
        """Create five morpheme language models based on the five randomly shuffled 90%ers
        of the Gold Standard corpus which are categorial:

        corpus #371 'Gold 1 training'.
        corpus #373 'Gold 2 training'.
        corpus #375 'Gold 3 training'.
        corpus #377 'Gold 4 training'.
        corpus #379 'Gold 5 training'.

        After this ran, I had:

        | 54 | Categorial Language model based on corpus #371 "Gold 1 training". |
        | 55 | Categorial Language model based on corpus #373 "Gold 2 training". |
        | 56 | Categorial Language model based on corpus #375 "Gold 3 training". |
        | 57 | Categorial Language model based on corpus #377 "Gold 4 training". |
        | 58 | Categorial Language model based on corpus #379 "Gold 5 training".

        """

        for corpus_id, corpus_name in (
            (371, 'Gold 1 training'),
            (373, 'Gold 2 training'),
            (375, 'Gold 3 training'),
            (377, 'Gold 4 training'),
            (379, 'Gold 5 training')):
            categorial = True
            name = u'Categorial Language model based on corpus #%s "%s".' % (corpus_id, corpus_name)
            language_model = self.create_language_model(name, corpus_id, toolkit='mitlm', categorial=categorial)
            log.info(u'%s created.' % name)
            language_model = self.generate_language_model(language_model['id'])
            try:
                assert language_model['generate_succeeded'] == True
            except AssertionError:
                log.info(language_model['generate_message'])
            log.info(u'%s generated.' % name)



    def create_language_model_1(self, force_recreate=False):
        """Create a morpheme language model based on a corpus of forms containing analyzed words.

        """

        name = u'Morpheme language model for Blackfoot'
        return self.create_language_model_x(name, force_recreate)

    def create_language_model_dunham_enterer(self, force_recreate=False):
        """Create a morpheme language model based on a corpus of forms containing well
        analyzed words entered by Dunham.

        """

        name = (u'Morpheme language model for Blackfoot based on a corpus of well analyzed '
            u'forms entered by Joel Dunham.')
        corpus_func = 'create_dunham_enterer_well_analyzed_words_corpus'
        return self.create_language_model_x(name, force_recreate, corpus_func=corpus_func)

    def create_language_model_dunham_enterer_categorial(self, force_recreate=False):
        """Create a *categorial* morpheme language model based on a corpus of forms containing well
        analyzed words entered by Dunham.

        """

        name = (u'Categorial morpheme language model for Blackfoot based on a corpus of well analyzed '
            u'forms entered by Joel Dunham.')
        corpus_func = 'create_dunham_enterer_well_analyzed_words_corpus_weighted'
        return self.create_language_model_x(name, force_recreate, corpus_func=corpus_func, categorial=True)

    def create_language_model_louie_elicitor(self, force_recreate=False):
        """Create a morpheme language model based on a corpus of forms containing well
        analyzed words entered by Dunham.

        """

        name = (u'Morpheme language model for Blackfoot based on a corpus of analyzed '
            u'forms elicited by Meagan Louie.')
        corpus_func = 'create_louie_elicitor_analyzed_words_corpus'
        return self.create_language_model_x(name, force_recreate, corpus_func=corpus_func)



    # Parser creation methods
    ################################################################################

    def create_parser_x(self, name, morph_func, phon_func, lm_func, force_recreate=False):
        """Create a parser given a name and the names of three methods used to create the
        phonology, morphology and language model.  The parser is created, compiled and saved
        locally, with all steps cached.

        """

        key = 'parsers'
        log.info(u'Creating a parser named "%s".' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Parser "%s" has already been created, compiled and saved locally.' % name)
            return record

        # Create and generate the parser's dependencies
        morphology = getattr(self, morph_func)(force_recreate)
        phonology = getattr(self, phon_func)(force_recreate)
        language_model = getattr(self, lm_func)(False)

        # Create the parser
        parser = self.create_parser(name, phonology['id'], morphology['id'], language_model['id'])
        assert 'id' in parser
        log.info(u'%s created.' % name)
        local_copy_path = os.path.join(self.localstore, key, 'parser_%s' % parser['id'])
        self.record[key][name] = parser
        self.dump_record()

        # Compile the parser, if not already compiled.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            parser['compile_succeeded'] == True and not force_recreate):
            log.info(u'Parser "%s" has already been compiled.' % name)
        else:
            parser = self.compile_parser(parser['id'])
            assert parser['compile_succeeded'] == True
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'%s compiled.' % name)

        # Save a local copy of the parser.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            record.get('saved_locally') and not force_recreate):
            log.info(u'Parser "%s" has already been saved locally.' % name)
        else:
            local_copy_path = researcher.save_parser_locally(parser['id'], local_copy_path)
            assert os.path.exists(local_copy_path)
            assert os.path.isfile(os.path.join(local_copy_path, 'parse.py'))
            parser.update({
                'saved_locally': True,
                'local_copy_path': local_copy_path
            })
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Parser "%s" has been saved locally.' % name)

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return parser

    def create_thesis_parser_1(self, lm_id, force_recreate=False):
        """Create Parser 1 as discussed in my dissertation with LM 40.
        morphological parser for Blackfoot, compile it and save it locally.

        # Phonology: #50 "Blackfoot phonology from Frantz (1991)"
        # Morphology: #61 "Morphology with morphotactics drawn from well analyzed words in the data set"
        # Language Models: 
        #     #40 "Language model based on corpus 'Gold 1 training'."
        #     #41 "Language model based on corpus 'Gold 2 training'."
        #     #42 "Language model based on corpus 'Gold 3 training'."
        #     #43 "Language model based on corpus 'Gold 4 training'."
        #     #44 "Language model based on corpus 'Gold 5 training'."

        """

        phonology_id = 50
        morphology_id = 61
        name = u'Morphological parser for Blackfoot as described in Dunham (2014) with LM #%d' % lm_id

        #BOSCO
        # Here begins the code of create_parser_x

        key = 'parsers'
        log.info(u'Creating a parser named "%s".' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Parser "%s" has already been created, compiled and saved locally.' % name)
            return record

        # Create the parser
        parser = self.create_parser(name, phonology_id, morphology_id, lm_id)
        assert 'id' in parser
        log.info(u'%s created.' % name)
        local_copy_path = os.path.join(self.localstore, key, 'parser_%s' % parser['id'])
        self.record[key][name] = parser
        self.dump_record()

        # Compile the parser, if not already compiled.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            parser['compile_succeeded'] == True and not force_recreate):
            log.info(u'Parser "%s" has already been compiled.' % name)
        else:
            parser = self.compile_parser(parser['id'])
            pprint.pprint(parser)
            assert parser['compile_succeeded'] == True
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'%s compiled.' % name)

        # Save a local copy of the parser.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            record.get('saved_locally') and not force_recreate):
            log.info(u'Parser "%s" has already been saved locally.' % name)
        else:
            local_copy_path = researcher.save_parser_locally(parser['id'], local_copy_path)
            assert os.path.exists(local_copy_path)
            assert os.path.isfile(os.path.join(local_copy_path, 'parse.py'))
            parser.update({
                'saved_locally': True,
                'local_copy_path': local_copy_path
            })
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Parser "%s" has been saved locally.' % name)

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return parser


    def create_thesis_parser_2(self, lm_id, force_recreate=False):
        """Create Parser 1 as discussed in my dissertation with LM 40.
        morphological parser for Blackfoot, compile it and save it locally.

        # Phonology: #51 "Blackfoot phonology from Frantz (1991) with prominence and length distinctions flattened"
        # Morphology: #61 "Morphology with morphotactics drawn from well analyzed words in the data set"
        # Language Models: 
        #     #40 "Language model based on corpus 'Gold 1 training'."
        #     #41 "Language model based on corpus 'Gold 2 training'."
        #     #42 "Language model based on corpus 'Gold 3 training'."
        #     #43 "Language model based on corpus 'Gold 4 training'."
        #     #44 "Language model based on corpus 'Gold 5 training'."

        """

        phonology_id = 51
        morphology_id = 61
        name = u'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #%d' % lm_id

        key = 'parsers'
        log.info(u'Creating a parser named "%s".' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Parser "%s" has already been created, compiled and saved locally.' % name)
            return record

        # Create the parser
        parser = self.create_parser(name, phonology_id, morphology_id, lm_id)
        assert 'id' in parser
        log.info(u'%s created.' % name)
        local_copy_path = os.path.join(self.localstore, key, 'parser_%s' % parser['id'])
        self.record[key][name] = parser
        self.dump_record()

        # Compile the parser, if not already compiled.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            parser['compile_succeeded'] == True and not force_recreate):
            log.info(u'Parser "%s" has already been compiled.' % name)
        else:
            parser = self.compile_parser(parser['id'])
            pprint.pprint(parser)
            assert parser['compile_succeeded'] == True
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'%s compiled.' % name)

        # Save a local copy of the parser.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            record.get('saved_locally') and not force_recreate):
            log.info(u'Parser "%s" has already been saved locally.' % name)
        else:
            local_copy_path = researcher.save_parser_locally(parser['id'], local_copy_path)
            assert os.path.exists(local_copy_path)
            assert os.path.isfile(os.path.join(local_copy_path, 'parse.py'))
            parser.update({
                'saved_locally': True,
                'local_copy_path': local_copy_path
            })
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Parser "%s" has been saved locally.' % name)

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return parser



    def create_parser_1(self, force_recreate=False):
        """Create a morphological parser for Blackfoot, compile it and save it locally.

        """

        name = u'A morphological parser for Blackfoot'
        morph_func = 'create_morphology_1'
        phon_func = 'create_phonology_1'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_2(self, force_recreate=False):
        """Create a morphological parser for Blackfoot that differs from parser
        1 in that its phonology generates more surface transcriptions.  I.e., 
        attempt to generate more parses.

        """

        name = u'The overgenerator parser'
        morph_func = 'create_morphology_1'
        phon_func = 'create_phonology_2'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_3(self, force_recreate=False):
        """Create a morphological parser for Blackfoot that differs from parser
        2 in that its phonology syllabifies and tries to model default accent placement.

        """

        name = u'Parser with a syllabifying, default accent-guessing phonology'
        morph_func = 'create_morphology_1'
        phon_func = 'create_phonology_3'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_4(self, force_recreate=False):
        """Create a morphological parser for Blackfoot that differs from parser
        2 in that its phonology includes the `misspell` transducer.

        """

        name = u'Parser with a phonology that wildly accepts spelling errors.'
        morph_func = 'create_morphology_1'
        phon_func = 'create_phonology_4'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_5(self, force_recreate=False):
        """A duplicate of parser 5 (misspell transducer) but with a rich representations
        morphology.

        """

        name = (u'Parser with a phonology that wildly accepts spelling errors and a rich '
                u'representations morphology.')
        morph_func = 'create_morphology_2'
        phon_func = 'create_phonology_4'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_dunham_enterer(self, force_recreate=False):
        """A parser that tries to maximize the parse accuracy against the corpus of well
        analyzed words entered by Dunham.

        morphology: based on corpus of well analyzed forms entered by Dunham
        phonology: misspell overgenerator phonology
        language model: based on corpus of well analyzed forms entered by Dunham

        """

        name = u'Parser attuned to the corpus of well analyzed words entered by Dunham.'
        morph_func = 'create_morphology_dunham_enterer'
        phon_func = 'create_phonology_4'
        lm_func = 'create_language_model_dunham_enterer'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_louie_elicitor(self, force_recreate=False):
        """A parser that tries to maximize the parse accuracy against the corpus of forms
        elicited by Meagan Louie.

        morphology: based on corpus of forms containing analyzed words elicited by Meagan Louie,
        crucially with *her* lexical items in the morphological specification.
        phonology: #2, the one tuned towards my corpus (try #1 or #3 too ...?)
        language model: based on corpus of analyzed words elicited by Louie

        """

        name = u'Parser attuned to the corpus of analyzed words elicited by Louie.'
        morph_func = 'create_morphology_louie_elicitor'
        phon_func = 'create_phonology_2'
        lm_func = 'create_language_model_louie_elicitor'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_dunham_enterer_categorial(self, force_recreate=False):
        """A second parser that tries to maximize the parse accuracy against the corpus of well
        analyzed words entered by Dunham.  The change from `_dunham_enterer` is that this
        one has a categorial LM.

        morphology: based on corpus of well analyzed forms entered by Dunham
        phonology: misspell overgenerator phonology
        language model: based on corpus of well analyzed forms entered by Dunham, categorial

        """

        name = u'Parser attuned to the corpus of well analyzed words entered by Dunham.'
        morph_func = 'create_morphology_dunham_enterer'
        phon_func = 'create_phonology_4'
        lm_func = 'create_language_model_dunham_enterer_categorial'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_parser_weber_2013(self, force_recreate=False):
        """A parser that tries to maximize the parse accuracy against the corpus of well
        analyzed words from Weber (2013).

        morphology: based on corpus of well analyzed word-containing forms; rich upper and
            rich lower.
        phonology: a category/morpheme-aware phonology ...
        language model: based on corpus of well analyzed forms entered by Dunham, categorial

        """

        name = u'Parser attuned to the corpus of well analyzed words from Weber (2013).'
        morph_func = 'create_morphology_weber'
        phon_func = 'create_phonology_5'
        lm_func = 'create_language_model_1'
        return self.create_parser_x(name, morph_func, phon_func, lm_func, force_recreate)

    def create_toy_parser(self, force_recreate=False):
        """Create a toy morphological parser for Blackfoot, compile it and save it locally.

        """

        name = u'A toy morphological parser for Blackfoot'
        key = 'parsers'
        local_copy_path = os.path.join(self.localstore, key, 'parser_toy')
        log.info(u'Creating a parser named "%s".' % name)

        record = self.record.get(key, {}).get(name, {})
        if record.get('created') and not force_recreate:
            log.info(u'Parser "%s" has already been created, compiled and saved locally.' % name)
            return record

        # Create and generate the parser's dependencies
        morphology = self.create_toy_morphology(force_recreate)
        phonology = self.create_phonology_1(force_recreate)
        language_model = self.create_language_model_1(force_recreate)

        # Create the parser
        parser = self.create_parser(name, phonology['id'], morphology['id'],
                                    language_model['id'])
        assert 'id' in parser
        log.info(u'%s created.' % name)
        self.record[key][name] = parser
        self.dump_record()

        # Compile the parser, if not already compiled.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            parser['compile_succeeded'] == True and not force_recreate):
            log.info(u'Parser "%s" has already been compiled.' % name)
        else:
            parser = self.compile_parser(parser['id'])
            assert parser['compile_succeeded'] == True
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'%s compiled.' % name)

        # Save a local copy of the parser.
        record = self.record.get(key, {}).get(name, {})
        if (parser['compile_attempt'] == record.get('compile_attempt', 'None') and
            record.get('saved_locally') and not force_recreate):
            log.info(u'Parser "%s" has already been saved locally.' % name)
        else:
            local_copy_path = researcher.save_parser_locally(parser['id'], local_copy_path)
            assert os.path.exists(local_copy_path)
            assert os.path.isfile(os.path.join(local_copy_path, 'parse.py'))
            parser.update({
                'saved_locally': True,
                'local_copy_path': local_copy_path
            })
            record.update(parser)
            self.record[key][name] = record
            self.dump_record()
            log.info(u'Parser "%s" has been saved locally.' % name)

        record = self.record.get(key, {}).get(name, {})
        record['created'] = True
        self.record[key][name] = record
        self.dump_record()
        return parser

    def test_parser(self, parser):
        """Do some basic tests on the parser to ensure that it is behaving as expected.

        """

        rare_delimiter = parser['morphology_rare_delimiter']
        transcriptions = {
            u'nitsspiyi': u'%s-%s' % (
                rare_delimiter.join([u'nit', u'1', u'agra']),
                rare_delimiter.join([u'ihpiyi', u'dance', u'vai'])),
            u'nitsinoaawa': u'%s-%s-%s-%s' % (
                rare_delimiter.join([u'nit', u'1', u'agra']),
                rare_delimiter.join([u'ino', u'see', u'vta']),
                rare_delimiter.join([u'aa', u'DIR', u'thm']),
                rare_delimiter.join([u'wa', u'3SG', u'agrb'])),
            u'nonsense': None
        }

        # Test the parser via request
        parses = self.parse(parser, transcriptions.keys())
        print 'Parser produces:'
        pprint.pprint(parses)
        print 'Parser should produce:'
        pprint.pprint(transcriptions)
        try:
            assert parses == transcriptions
            log.info('Parser "%s" parses correctly via request.' % parser['name'])
        except AssertionError:
            print 'Parser parsers, but not as expected.'
            log.info('Parser "%s" parses, but not as expected.' % parser['name'])

        # Test the locally saved parser
        # Note that ``parse_locally`` returns ``Parse`` instances, not strings.
        parses = self.parse_locally(parser, transcriptions.keys())
        try:
            assert (dict((transcription, parse.parse) for transcription, (parse, candidates) in parses.iteritems())
                    == transcriptions)
            log.info('Parser "%s" parses correctly locally.' % parser['name'])
        except AssertionError:
            log.info('Parser "%s" parses locally, not correctly.' % parser['name'])

    def create_dunham_enterer_well_analyzed_words_corpus(self, force_recreate=False):
        """Create a corpus of forms containing well analyzed words entered by Dunham.

        """

        return self.save_well_analyzed_words_corpus(
            force_recreate=force_recreate,
            relation='enterer',
            attribute='last_name',
            value='Dunham'
        )

    def create_weber_2013_well_analyzed_words_corpus(self, force_recreate=False):
        """Create a corpus of forms containing well analyzed words from Weber
        (2013) `Accent and prosody in Blackfoot verbs.'

        Note: the forms from Weber 2013 must exist in the database. If necessary,
        call self.add_weber().

        """

        return self.save_well_analyzed_words_corpus(
            force_recreate=force_recreate,
            relation='source',
            attribute='author',
            value='Natalie Weber'
        )

    def create_louie_elicitor_analyzed_words_corpus(self, force_recreate=False):
        """Create a corpus of forms containing analyzed words entered by Louie.

        """
        return self.save_analyzed_words_corpus(
            force_recreate=force_recreate,
            relation='elicitor',
            attribute='last_name',
            value='Louie'
        )

    def create_dunham_enterer_well_analyzed_words_corpus_weighted(self, force_recreate=False):
        """Create a corpus of forms containing well analyzed words entered by Dunham.
        The corpus will contain many repetitions of the same forms so as to create a
        better LM.

        """

        interim_corpus = self.create_dunham_enterer_well_analyzed_words_corpus(force_recreate)
        interim_corpus_forms = self.get_corpus_forms(interim_corpus)
        # content attribute value should be:
        name = u'Corpus of forms entered by Dunham, containing well analyzed words, 100x each token.'
        content = u','.join([str(f['id']) for f in interim_corpus_forms] * 100)
        return self.create_corpus(name, content=content)


    def get_well_analyzed_words(self, force_recreate=False, **kwargs):
        """Find all of the well analyzed words in the database and do stuff with them ...

        1. Count them - CHECK

        2. Get and count the unique well analyzed word types - CHECK

        3. Get a list of well analyzed word types with a unique most common
           analysis; this is the "gold standard" that the ideal parser will encode. - CHECK

        4. Create a pickle file containing the gold standard

        5. Create a new form object in the database for each well analyzed word
           type and tag each of these form objects as a "well analyzed word". - CHECK

        6. Create a corpus that contains all of these well analyzed word types.
           This should be used as the rules corpus for the morphologies of parsers. - CHECK

        7. Create a corpus that contains all of the gold standard well analyzed
           word types.  This should be used to create the training/test set
           corpora for training LMs and testing parsers. - CHECK

        8. Create 5 training/test set (90%/10%) corpus pairs built from the
           elements in the gold standard corpus; each parser should have 5
           different versions, each with a LM built from a given training set and
           each tested against the corresponding training set.

        9. Print the gold standard to a file that is a bunch of test declarations and
           see how many of them the phonology passes!

        """


        gold_corpus = self.old.get('corpora/370')
        gold_forms = self.get_corpus_forms(gold_corpus)
        with codecs.open('gold_tests_no_accents.txt', 'w', 'utf8') as f:
            for gold_form in gold_forms:
                line = (u'#test %s -> %s\n' % (gold_form['morpheme_break'], gold_form['transcription'])).replace(
                        u'a\u0301', u'a').replace(u'i\u0301', u'i').replace(u'o\u0301', u'o')
                f.write(line)





        """
        corpora = {}

        log.info(u'Creating and pickling locally a corpus of forms that contain well analyzed words.')
        corpus = self.create_well_analyzed_words_corpus(force_recreate=force_recreate, **kwargs)
        name = corpus['name']
        key = 'corpora'

        tokens_filename = u'well_analyzed_word_tokens.pickle'
        tokens_file_path = os.path.join(self.localstore, key, tokens_filename)

        filename = u'well_analyzed_words.pickle' 
        file_path = os.path.join(self.localstore, key, filename)

        record = self.record.get(key, {}).get(name, {})
        if record.get('saved_locally') and not force_recreate:
            word_tokens = cPickle.load(open(tokens_file_path, 'rb'))
        else:
            log.info('requesting forms of corpus')
            forms = self.get_corpus_forms(corpus)
            log.info('got forms of corpus')
            log.info('extracting word tokens from forms of corpus')
            word_tokens = self.get_word_tokens(forms, filter_=True) # This is a list of (tr, mb, mg, scs) 4-tuples
            log.info('done extracting word tokens from forms of corpus')
            cPickle.dump(word_tokens, open(tokens_file_path, 'wb'))
            assert os.path.isfile(tokens_file_path)

        def latex_accents(input_):
            return input_.replace(u'a\u0301', u"\\'a")\
                .replace(u'i\u0301', u"\\'i")\
                .replace(u'o\u0301', u"\\'o")

        # Print to stdout how many waw tokens and types there are
        word_types = list(set(word_tokens))
        print '\nSummary'
        print '-' * 80
        print '\nThere are %d well analyzed word tokens' % len(word_tokens)
        print 'There are %d well analyzed word types' % len(word_types)
        print

        # Create a form object for each of the 3,414 well analyzed word types
        self.create_form_for_each_well_analyzed_word(word_types)


        # Create a form search that returns these well analyzed word types.
        waw_search_name = u'Search that returns a set of forms where each represents a unique well-analyzed word'
        query = {'filter': ['Tag', 'name', '=', u'well analyzed word']}
        params = self.old.form_search_create_params.copy()
        params.update({'name': waw_search_name, 'search': query, 'description': u''})
        create_response = self.old.post('formsearches', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            waw_search = self.old.search('formsearches',
                {'query': {'filter': ['FormSearch', 'name', '=', waw_search_name]}})[0]
            if waw_search['search'] != query:
                waw_search = self.old.put('formsearches/%s' % waw_search['id'], params)
        elif create_response.get('id'):
            waw_search = create_response
        else:
            log.info(create_response)
            raise Exception('Unable to create search named "%s".' % waw_search_name)

        # Create a corpus in the OLD database containing these well analyzed word types.
        corpus_name = u'Corpus where each form is a representation of a unique well-analyzed word'
        corpus = self.create_corpus(corpus_name, search_id=waw_search['id'])
        log.info(u'Corpus "%s" created.' % corpus_name)
        log.info(u'Getting all forms in this corpus: %s' % corpus_name)
        #waw_type_forms = self.get_corpus_forms(corpus) # This is a list of 3,414 dict representations of forms.
        log.info(u'All forms in the well analyzed word types corpus retrieved')


        # Get the Gold IDs and create a gold corpus with them
        gold_ids = cPickle.load(open('gold_ids.pickle', 'rb'))

        log.info('Create Gold corpus')
        params = self.old.corpus_create_params.copy()
        gold_id_str = u','.join(map(unicode, gold_ids))
        params.update({'name': u'Gold', 'content': gold_id_str})
        gold_corpus = self.old.post('corpora', params)

        gold_len = len(gold_ids)
        print gold_len
        print gold_len * 6
        ninety_mark = int(0.9 * gold_len)

        # Create 5 training/test set corpus pairs from the gold data, via request
        for i in range(1, 6):
            log.info('Create Gold corpus training/test pair %d' %i)
            random.shuffle(gold_ids)

            train_corpus_name = u'Gold %d training' % i
            train_set = gold_ids[:ninety_mark]
            train_content = u','.join(map(unicode, train_set))
            params = self.old.corpus_create_params.copy()
            params.update({'name': train_corpus_name, 'content': train_content})
            train_corpus = self.old.post('corpora', params)

            test_corpus_name = u'Gold %d test' % i
            test_set = gold_ids[ninety_mark:]
            test_content = u','.join(map(unicode, test_set))
            params = self.old.corpus_create_params.copy()
            params.update({'name': test_corpus_name, 'content': test_content})
            test_corpus = self.old.post('corpora', params)

        #+-----+-----------------+
        #| id  | name            |
        #+-----+-----------------+
        #| 358 | Gold            |
        #| 359 | Gold 1 training |
        #| 360 | Gold 1 test     |
        #| 361 | Gold 2 training |
        #| 362 | Gold 2 test     |
        #| 363 | Gold 3 training |
        #| 364 | Gold 3 test     |
        #| 365 | Gold 4 training |
        #| 366 | Gold 4 test     |
        #| 367 | Gold 5 training |
        #| 368 | Gold 5 test     |
        #+-----+-----------------+




        types = {} # dict from (tr, mb, mg, sc) tuples to counts
        sc_types = {} # dict from sc values to counts
        tr_types = {} # dict from tr values to analyses, i.e., (mb, mg, sc) triples
        for tr, mb, mg, sc in word_tokens:
            #word_token = (tr, mb, mg.lower(), sc) # Here is where I lowercase the morpheme gloss information
            word_token = (tr, mb, mg, sc)
            types.setdefault(word_token, 0)
            types[word_token] += 1
            sc_types.setdefault(sc, 0)
            sc_types[sc] += 1
            tr_types.setdefault(tr, []).append((mb, mg, sc))
        types_list = sorted([(v, k) for k, v in types.iteritems()], reverse=True)

        # Get the Gold Standard
        # This is a list of all well analyzed word types with a single best analysis.
        # If a transcription has only one good analysis, that is the gold parse.
        # If a transcription has many good analyses, choose the one that is used most often.
        # If there is no most often chosen good analysis, don't include this word.
        gold = []
        for tr, analyses in tr_types.iteritems():
            if len(analyses) == 1:
                gold.append((tr, analyses[0][0], analyses[0][1], analyses[0][2]))
            else:
                #print
                #print 'Many good analyses for %s' % tr
                tmp = {}
                for analysis in analyses:
                    tmp.setdefault(analysis, 0)
                    tmp[analysis] += 1
                tmp2 = sorted([(v, k) for k, v in tmp.items()], reverse=True)
                #print 'Here they are'
                #pprint.pprint(tmp2)
                pg_count, possible_gold = tmp2[0]
                if len([x for x in tmp.values() if x == pg_count]) == 1:
                    #print 'Gold is %s %s %s' % possible_gold
                    gold.append((tr, possible_gold[0], possible_gold[1], possible_gold[2]))
                else:
                    print 'No gold parse for %s :(' % tr
                    pprint.pprint(tmp2)
                    print

        print '\n\n'
        print 'There are %d Gold Parses' % len(gold)

        # This is a really hacky way of tagging all of the gold waw forms as 'gold':
        # The 'gold' tag has ID=15;
        # So, just create 3,245 SQL statements to update the formtag table so that all 3,245 gold
        # forms have the 'gold' tag. Then run mysql blaold_research < gold_tagger.sql
        # Also, just pickle the IDs of all of the gold forms for later creation of training/test set pairs
        gold_form_ids = []
        for form_dict in waw_type_forms:
            id_ = form_dict['id']
            tr = form_dict['transcription']
            mb = form_dict['morpheme_break']
            mg = form_dict['morpheme_gloss']
            scs = form_dict['syntactic_category_string']
            if (tr, mb, mg, scs) in gold:
                gold_form_ids.append(id_)
        print 'Found the id values of %d gold forms' % len(gold_form_ids)
        with open('gold_tagger.sql', 'w') as f:
            for gold_id in gold_form_ids:
                f.write('INSERT INTO formtag (form_id, tag_id) VALUES (%d, 15);\n' % gold_id)
        cPickle.dump(gold_form_ids, open('gold_ids.pickle', 'wb'))




        # Create a corpus that contains all of the gold standard well analyzed
        # word types.  This should be used to create the training/test set
        # corpora for training LMs and testing parsers.


        # PLACE THE TRIPLE QUOTES HERE!!!


        print '\n\n'
        print 'Most common well analyzed words'
        print '-' * 80
        for count, (tr, mb, mg, sc) in types_list[:20]:
            print latex_accents(u'%s & %s & %s & %s & %d \\\\' % (tr, mb, mg, sc, count))

        verbals = []
        nominals = []
        for count, (tr, mb, mg, sc) in types_list:
            if len(verbals) < 20 or len(nominals) < 20:
                if set(['vti', 'vta', 'vrt', 'vai', 'vii']) & set(sc.split('-')):
                    verbals.append((count, tr, mb, mg, sc))
                if set(['nan', 'nin', 'nar', 'nir']) & set(sc.split('-')):
                    nominals.append((count, tr, mb, mg, sc))
            else:
                break
        verbals = sorted(verbals[:20], reverse=True)
        nominals = sorted(nominals[:20], reverse=True)

        print '\n\n'
        print 'Most common well analyzed verbal forms'
        print '-' * 80
        for count, tr, mb, mg, sc in verbals:
            print latex_accents(u'%s & %s & %s & %s & %d \\\\' % (tr, mb, mg, sc, count))

        print '\n\n'
        print 'Most common well analyzed verbal forms'
        print '-' * 80
        for count, tr, mb, mg, sc in nominals:
            print latex_accents(u'%s & %s & %s & %s & %d \\\\' % (tr, mb, mg, sc, count))

        sc_types = sorted([(v, k) for k, v in sc_types.iteritems()], reverse=True)
        print '\n\n'
        print 'Most common category strings'
        print '-' * 80
        for count, sc in sc_types[:20]:
            print latex_accents(u'%s & %d \\\\' % (sc, count))

        corpus.update({
            'saved_locally': True,
            'local_copy_path': file_path
        })

        record.update(corpus)
        self.record[key][name] = record
        self.dump_record()
        log.info(u'Corpus "%s" has been saved locally.' % name)
        return record





        corpora[well_analyzed_words_corpus['name']] = well_analyzed_words_corpus
        return corpora
        """



        """


        waw_meta = corpora[u'Corpus of forms that contain well analyzed Blackfoot words']
        waw = cPickle.load(open(waw_meta['local_copy_path'], 'rb'))
        waw_dict = {}
        for tr, mb, mg, sc in waw:
            waw_dict.setdefault(tr, []).append((mb, mg, sc))
        multiples = {}
        uniques = {}
        for tr, ana in waw_dict.iteritems():
            if len(ana) > 1:
                multiples[tr] = ana
            else:
                uniques[tr] = ana[0]
        print len(waw)
        print len(uniques)
        k = multiples.keys()[1]
        v = multiples[k]
        print k
        print
        for br, gl, sc in v:
            print br
            print gl
            print sc
            print
        """

    def create_form_for_each_well_analyzed_word(self, waw_types):
        """Create a form object for each of the well analyzed words provided in ``waw_types``.

        Warning: this creates some 3,400 form objects by request, one at a
        time; so it can take a while. The second time it is run, it won't
        recreate them and it'll be faster.
        Warning 2: it's really weird that I made 'well analyzed word' the
        category!  I meant to create a 'well analyzed word' tag and use that...
        So I just did it manually via MySQL (35 is the id of the waw category
        and 14 is the id of the waw tag): mysql> insert into formtag (form_id,
        tag_id) select id, 14 from form where syntacticcategory_id=35; print
        waw_types is a list of (tr, mb, mg, scs) 4-tuples.

        """

        waw_name = u'well analyzed word'
        waw_cat = self.old.create('syntacticcategories', {
            'name': waw_name,
            'type': u'',
            'description': u'Specialized category for the 3414 well analyzed word types discovered in the database.'})
        if 'errors' in waw_cat: # This will happen if we've created this category already ...
            waw_cat = [sc for sc in self.old.get('syntacticcategories') if sc['name'] == waw_name][0]

        waws = self.old.search('forms',
            {'query': {'filter': ['Form', 'syntactic_category', 'name', '=', waw_name]}})
        if len(waws) == 0:
            for tr, mb, mg, scs in waw_types:
                params = self.old.form_create_params.copy()
                params.update({
                    'grammaticality': u'',
                    'transcription': tr,
                    'morpheme_break': mb,
                    'morpheme_gloss': mg,
                    'translations': [{'transcription': mg, 'grammaticality': u''}],
                    'syntactic_category': waw_cat['id'],
                    'comments': u"Created programmatically; identified as a well analyzed word in the data set."
                })
                form = self.old.post('forms', params)

            waws = self.old.search('forms',
                {'query': {'filter': ['Form', 'syntactic_category', 'name', '=', waw_name]}})
        print 'There are %d well analyzed word forms are now in the database' % len(waws)


    def create_corpora(self, force_recreate=False, **kwargs):
        """Create a bunch of corpora and pickle them locally.

        .. note::

            I have commented out the commands to create the "words" and "analyzed words" copora,
            focusing instead on just creating the "well analyzed words" ones.

        """

        log.info(u'Creating corpora.')
        corpora = {}

        # Create the three main corpora.
        #words_corpus = self.save_words_corpus(force_recreate=force_recreate)
        #analyzed_words_corpus = self.save_analyzed_words_corpus(
        #    force_recreate=force_recreate)
        well_analyzed_words_corpus = self.save_well_analyzed_words_corpus(
            force_recreate=force_recreate)

        #corpora[words_corpus['name']] = words_corpus
        #corpora[analyzed_words_corpus['name']] = analyzed_words_corpus
        corpora[well_analyzed_words_corpus['name']] = well_analyzed_words_corpus
        
        """

        # Create a corpus of well-analyzed words from Weber 2013.
        researcher.create_weber_2013_well_analyzed_words_corpus(force_recreate=True)

        # Create 17 additional corpora. The 5 largest enterer-defined corpora, the 5 largest
        # elicitor-defined, 3 speaker-defined, 2 dialect-defined, 2 source-defined.
        relations = {
            'enterer': (
                ('last_name', 'Dunham'),
                ('last_name', 'Hanson'),
                ('last_name', 'Johansson'),
                ('last_name', 'Marshall'),
                ('last_name', 'Meadows')),
            'elicitor': (
                ('last_name', 'Bliss'),
                ('last_name', 'Dunham'),
                ('last_name', 'Johansson'),
                ('last_name', 'Louie'),
                ('last_name', 'Wiltschko')),
            'speaker': (
                ('last_name', 'Bullshields'),
                ('last_name', 'Ermineskin'),
                ('last_name', 'Breaker'),
                ('dialect', u'Siksika\u0301'),
                ('dialect', 'Kainai')),
            'source': (
                ('author', 'Donald Frantz'),
                ('id', '3'), # Frantz & Russell (1995)
                ('id', '14')) # Frantz (2009)
        }
        for relation, attribute_values in relations.items():
            for attribute, value in attribute_values:
                #corpus = self.save_words_corpus(
                #    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                #corpora[corpus['name']] = corpus

                #corpus = self.save_analyzed_words_corpus(
                #    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                #corpora[corpus['name']] = corpus

                corpus = self.save_well_analyzed_words_corpus(
                    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                corpora[corpus['name']] = corpus
        """
        return corpora

    def get_corpora_locally(self, force_recreate=False, **kwargs):
        """Get the following corpora and save them locally.
        372, "Gold 1 test"
        374, "Gold 2 test"
        376, "Gold 3 test"
        378, "Gold 4 test"
        380, "Gold 5 test"

        """

        log.info(u'Getting gold test set corpora locally.')
        corpora = {}
        key = 'corpora'
        for index, corpus_id in ((1, 372), (2, 374), (3, 376), (4, 378), (5, 380)):
            corpus = self.old.get('corpora/%d' % corpus_id)
            filename = u'gold_%d_corpus.pickle' % index
            name = corpus['name']
            record = self.record.get(key, {}).get(name, {})
            if record.get('saved_locally') and not force_recreate:
                log.info(u'Corpus "%s" has already been saved locally.' % name)
                corpora[name] = record
            else:
                forms = self.get_corpus_forms(corpus)
                form_words = self.get_form_words(forms, filter_=True)
                file_path = os.path.join(self.localstore, key, filename)
                cPickle.dump(form_words, open(file_path, 'wb'))
                assert os.path.isfile(file_path)
                corpus.update({
                    'saved_locally': True,
                    'local_copy_path': file_path
                })
                record.update(corpus)
                self.record[key][name] = record
                self.dump_record()
                log.info(u'Corpus "%s" has been saved locally.' % name)
                corpora[name] = record
        log.info(u'Done getting gold test set corpora locally.')
        return corpora

    def remove_unwanted_characters(self, unistr):
        """Unwanted characters (mainly punctuation) can be removed and the resulting
        transcription should still be parseable.

        .. note::

            I remove the lowline character even though it is used to indicate
            word-final devoicing by some researchers. This should probably be
            incorporated into a phonology.

        """

        unwanted_unichrs = u'_"?(),#;:!.^&@$/*\u2018\u201C\u201D\u2026'
        translate_table = dict((ord(unichr), u'') for unichr in unwanted_unichrs)
        return unistr.translate(translate_table)

    def remove_deal_breakers_deprecated(self, unistr):
        """The presence of these characters in a transcription signifies that it is unparseable.

        .. note::

            I am including characters that are not standard in the Frantz-ian Bf
            inventory in the set of deal breakers. This is potentially
            problematic for two reasons:

            1. It will cause the exclusion of foreign word proper nouns, which
               should be parseable.

            2. It will cause the exclusion of transcriptions that contain
               characters which are quasi-standard in the Bf orthography, i.e.,
               "e" and "u" and chai for the palatal/velar fricative...

        """

        deal_breakers = u'1234567890-'
        translate_table = dict((ord(unichr), u'') for unichr in deal_breakers)
        return unistr.translate(translate_table)

    orthography = u"ptkmnsywhaio\u0301'"
    remove_deal_breakers = Keeper(orthography)

    def clean_transcription(self, transcription):

        return self.remove_unwanted_characters(transcription.lower()).\
            replace(u'\u2019', u"'").replace(u"''", u'')

    def clean_corpus(self, corpus):
        """Clean up the word transcriptions in the corpus and return a list of all unique.

        :param list corpus: a list of quadruples: <tr, mb, mg, sc>.
        :returns: a list of unique transcriptions that have been "cleaned".

        .. note::

            The ``lower()`` call will make matching names (e.g., "Abigail") impossible...

        """

        transcriptions = set()
        for transcription, m, g, c in corpus:
            cleaned_transcription = self.clean_transcription(transcription)
            if self.remove_deal_breakers(cleaned_transcription) == cleaned_transcription:
                transcriptions.add(cleaned_transcription)
        return list(transcriptions)


    def parse_corpus(self, parser, corpus, batch_size=0, preflight=lambda x: x):
        """Parse all of the transcriptions in the locally saved corpus using the
        locally saved parser.

        Ideas for improving performance:

        1. allow parser to attempt a parse on ``transcription.lower()`` if
           parse on ``transcription`` returns ``None``. Make this toggleable at
           the parse interface level.  This could also be implemented in the
           phonology for cases where the orthography makes segmental use of
           uppercase characters.

        2. make sure that unicode normalization is not fucking up local
           parsing! A possibility is that unicode->JSON->unicode conversion is
           resulting in non-NFD normalization.

        3.

        """
        #batch_size = 1 # DELETE ME, I AM FOR TESTING !!!
        batch_size = 20 # DELETE ME, I AM FOR TESTING !!!


        print 'in parse_corpus in blackfoot_research.py'
        corpus_list = cPickle.load(open(corpus['local_copy_path'], 'rb'))
        #corpus_list = [(preflight(t), m, g, c) for t, m, g, c in corpus_list[:100]] # WARNING: remove the 100 cap!
        corpus_list = [(preflight(t), m, g, c) for t, m, g, c in corpus_list] # WARNING: remove the 100 cap!
        transcriptions = self.clean_corpus(corpus_list)
        log.info('About to parse all %s unique transcriptions in corpus "%s".' % (
            len(transcriptions), corpus['name']))
        start_time = time.time()
        transcriptions = transcriptions
        parses = self.parse_locally(parser, transcriptions, batch_size)

        """
        # Attempt conversion to lowercase to get more parses
        unparsed_lc = list(set([t.lower() for t, p in parses.iteritems() if not p.parse]))
        if unparsed_lc:
            parses_lc = self.parse_locally(parser, unparsed_lc)
            for transcription, parse in parses.iteritems():
                if not parse.parse:
                    parses[transcription] = parses_lc.get(transcription.lower(), parse)
        """

        end_time = time.time()
        log.info('Time elapsed: %s' % self.old.human_readable_seconds(end_time - start_time))
        return parses, corpus_list

    def create_weber_2013(self):
        """Create a Weber (2013) source or return it if it already exists.

        """

        key = u'weber2013'
        params = self.old.source_create_params.copy()
        params.update({
            'type': u'unpublished',
            'key': key,
            'title': u'Accent and prosody in Blackfoot verbs',
            'author': u'Natalie Weber',
            'note': u'To be published in a proceedings of the Algonquian conference.',
            'year': 2013
        })
        create_response = self.old.post('sources', params)
        if 'id' in create_response:
            return create_response
        else:
            return self.old.search('sources',
                {'query': {'filter': ['Source', 'key', '=', key]}})[0]

    def add_weber_lexical_items(self, categories, weber_id):
        """ipowaa arise (in F&R as ipowa\u0301o\u0301o).
        simimmohki gossip (F&R only has simimm gossip.about vta).
        """

        params = self.old.form_create_params.copy()
        params.update({
            'grammaticality': u'',
            'transcription': u'ipowaa',
            'morpheme_break': u'ipowaa',
            'morpheme_gloss': u'arise',
            'translations': [{'transcription': u'arise', 'grammaticality': u''}],
            'syntactic_category': categories['vai']['id'],
            'comments': u"Compare to F&R's ipowa\u0301o\u0301o",
            'source': weber_id
        })
        self.old.post('forms', params)

        params = self.old.form_create_params.copy()
        params.update({
            'grammaticality': u'',
            'transcription': u'simimmohki',
            'morpheme_break': u'simimmohki',
            'morpheme_gloss': u'gossip',
            'translations': [{'transcription': u'gossip', 'grammaticality': u''}],
            'syntactic_category': categories['vai']['id'],
            'comments': u"Compare to F&R's simimm 'gossip.about' (vta).",
            'source': weber_id
        })
        self.old.post('forms', params)

    def add_weber(self):
        """A one-off method to add the data from Weber (2013).

        """

        import resources.weber as weber
        forms = weber.forms
        weber_2013 = self.create_weber_2013() # weber source object
        weber_id = weber_2013['id']
        categories = self.get_categories()
        self.add_weber_lexical_items(categories, weber_id)
        for npt, ot, ms, mg, tr, cat in forms:
            params = self.old.form_create_params.copy()
            params.update({
                'grammaticality': u'',
                'narrow_phonetic_transcription': npt,
                'phonetic_transcription': npt.replace(u'.', u''),
                'transcription': ot,
                'morpheme_break': ms,
                'morpheme_gloss': mg,
                'translations': [{'transcription': tr, 'grammaticality': u''}],
                'syntactic_category': categories[cat]['id'],
                'source': weber_id
            })
            self.old.post('forms', params)


    def pretty_print_parse_summaries(self, parse_summaries):
        summaries = {}
        for summary in parse_summaries:
            key = u'%-9s %-30s %-7s' % (
                    summary['type'],
                    u'%s %s (#%s)' % (summary['relation'], summary['entity'], summary['id']),
                    u'%s' % summary['attempted_count'])
            summaries.setdefault(key, {})
            summaries[key].setdefault('correctly_parsed_percent', []).\
                                append(summary['correctly_parsed_percent'])
            summaries[key].setdefault('morphophonology_success_percent', []).\
                                append(summary['morphophonology_success_percent'])
            summaries[key].setdefault('phonology_success_percent', []).\
                                append(summary.get('phonology_success_percent', 0.0))
            summaries[key].setdefault('lm_success_percent', []).\
                                append(summary['lm_success_percent'])
        for summary in sorted(summaries.keys()):
            correctly_parsed_percent = u'    '.join(
                [u'%0.3f' % (p,) for p in summaries[summary]['correctly_parsed_percent']])
            morphophonology_success_percent = u'    '.join(
                [u'%0.3f' % (p,) for p in summaries[summary]['morphophonology_success_percent']])
            phonology_success_percent = u'    '.join(
                [u'%0.3f' % (p,) for p in summaries[summary]['phonology_success_percent']])
            lm_success_percent = u'    '.join(
                [u'%0.3f' % (p,) for p in summaries[summary]['lm_success_percent']])

            print u'%s    %s    %s    %s    %s' % (
                summary, correctly_parsed_percent, morphophonology_success_percent,
                lm_success_percent, phonology_success_percent)



if __name__ == '__main__':

    # Get the command-line arguments
    ################################################################################

    # Basic usage: ./blackfoot_research.py -u USERNAME -p PASSWORD -H HOST -P PORT

    parser = optparse.OptionParser()
    parser.add_option("-u", "--username", default="old",
        help="username of the OLD researcher (on the OLD application) [default: %default]")
    parser.add_option("-p", "--password", default="old",
        help="password of the OLD researcher (on the OLD application) [default: %default]")
    parser.add_option("-H", "--host", default="127.0.0.1",
        help="hostname where the OLD application can be accessed [default: %default]")
    parser.add_option("-P", "--port", default="5000",
        help="port of the OLD application being used for the research [default: %default]")

    (options, args) = parser.parse_args()


    # Researcher initialization & configuration.
    ################################################################################

    record_file = 'record.pickle' # A cache of our research results

    # The researcher is an object designed to interact with a live OLD
    # application and issue requests involving the creation and testing of
    # morphological parsers and their subcomponents.
    researcher = BlackfootParserResearcher(options.username,
                                  options.password,
                                  options.host,
                                  record_file=record_file,
                                  port=options.port)

    # Silence the log! (or not)
    log.silent = False

    # GLOBAL: Determines whether resources are regenerated/recreated/recompiled even
    # when said resources have been persisted.
    force_recreate = True

    # This will reset the pickled record of the researcher to an empty dict.
    # Calling ``clear_record()`` is necessary for forcing the researcher to
    # repeat his research.
    #researcher.clear_record(clear_corpora=False)


    ################################################################################
    # Research!
    ################################################################################

    #sam_phonology = researcher.create_phonology(u'sam1', u'define phonology a;')
    #researcher.old.delete('phonologies/46')
    #researcher.old.delete('morphologies/57')
    #researcher.old.delete('morphemelanguagemodels/37')
    #researcher.old.delete('morphologicalparsers/47')
    #researcher.old.delete('corpora/333')


    # Phonologies
    ################################################################################
    # The run_phonology_tests method runs the tests in a defined phonology. Very
    # useful for test-driven phonology composition!
    # This creates phonology #50 "Blackfoot phonology from Frantz (1991)"

    #phonology = researcher.create_phonology_frantz91(force_recreate=True)
    #unsuccessful, test_count = researcher.run_phonology_tests(phonology)


    # This creates phonology #51 "Blackfoot phonology from Frantz (1991) with prominence and length distinctions flattened"
    #flattener_phonology = researcher.create_phonology_frantz91_flattener(force_recreate=True)
    #unsuccessful, test_count = researcher.run_phonology_tests(phonology)


    # Morphologies
    ################################################################################
    # The create_morphology_frantz95_waw method creates a morphology with the standard
    # lexicon corpus (basically the lexicon of the dictionary) and with a rules corpus
    # that is the corpus of 3,414 well analyzed word types present in the database.

    #morphology = researcher.create_morphology_frantz95_waw(force_recreate=True)


    # LMs
    ################################################################################
    # Create language models for each of the training set corpora drawn from the
    # gold standard corpus, i.e.,
    # 371 Gold 1 training, 373 Gold 2 training, 375 Gold 3 training, 377 Gold 4 training, 379 Gold 5 training
    # This gives me:
    # 40 Language model based on corpus #371 "Gold 1 training".
    # 41 Language model based on corpus #371 "Gold 2 training".
    # 42 Language model based on corpus #371 "Gold 3 training".
    # 43 Language model based on corpus #371 "Gold 4 training".
    # 44 Language model based on corpus #371 "Gold 5 training
    # NOTE: add 5 to all of the LM ids listed above (changes made!)

    #researcher.create_gold_language_model()
    #researcher.create_gold_language_model_categorial()


    # Well Analyzed Words
    ################################################################################

    # Gather up all of the well analyzed words from the non-mono-morphemic
    # forms in the database. Then print how many there are, how many unique
    # well analyzed word types there are, save a pickled dict of the gold 
    # standard (i.e., the well analyzed words with a single most common analysis)
    # (for later testing), and enter all of the well analyzed word types into
    # the database for later use in the creation of morphologies and language
    # models.
    #force_recreate = False
    #researcher.get_well_analyzed_words(force_recreate=force_recreate)


    # Corpora
    ################################################################################

    # Create a bunch of corpora that will be useful later on. This can take a while,
    # but the corpora are persisted as pickles, so it should only need to be done once.
    # I.e., researcher.record['corpora'] will contain the corpus metadata and
    # localstore/corpora/ will contain the corpus pickle files.
    #corpora = researcher.create_corpora(force_recreate=force_recreate)

    # Get the corpora already created by the create_corpora method of the researcher.
    #corpora = researcher.record['corpora']

    # Save the test set gold standard corpora locally
    #corpora = researcher.get_corpora_locally(force_recreate=force_recreate)


    """
    # Thesis Parser 1
    ################################################################################
    # This is one parser that is recreated five times with the five gold standard
    # training set-derived LMs (see above) and then tested with the relevant test set.

    # Phonology: #50 "Blackfoot phonology from Frantz (1991)"
    # Morphology: #61 "Morphology with morphotactics drawn from well analyzed words in the data set"
    # Language Models: 
    #     #40 "Language model based on corpus 'Gold 1 training'."
    #     #41 "Language model based on corpus 'Gold 2 training'."
    #     #42 "Language model based on corpus 'Gold 3 training'."
    #     #43 "Language model based on corpus 'Gold 4 training'."
    #     #44 "Language model based on corpus 'Gold 5 training'."

    #for lm_id in (45, 46, 47, 48, 49):
    #    researcher.create_thesis_parser_1(lm_id, force_recreate=True)
    #    print '\n\n\n'

    # The result of the above is that I have the following parsers (saved locally too):
    #     #55 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #40"
    #     #51 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #41"
    #     #52 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #42"
    #     #53 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #43"
    #     #54 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #44"

    # Run the basic tests on one of the parsers:
    # Note that parser 54 incorrectly parses nitsspiyi as nit|1|agra-sspi|among|adt-yi|0|agrb,
    # probably because of the LM ...
    # record = cPickle.load(open('record.pickle', 'rb'))
    # parsers = record['parsers']
    # parser_54 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #44']
    # researcher.test_parser(parser_54)

    # Test the parser on its test sets ...
    # Test the parser against all corpora and generate a list of success/failure summaries
    # for each parser-corpus pair. WARNING: takes about 2-3 mins. However, the summaries are
    # cached and the cached data can be retrieved by setting ``force_recreate`` to False.

    record = cPickle.load(open('record.pickle', 'rb'))
    parsers = record['parsers']
    parser_55 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #45']
    parser_51 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #46']
    parser_52 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #47']
    parser_53 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #48']
    parser_54 = parsers['Morphological parser for Blackfoot as described in Dunham (2014) with LM #49']


    corpora = researcher.get_corpora_locally(force_recreate=force_recreate)
    parser_55_test_set_corpus = {u'Gold_1_test': corpora[u'Gold 1 test']}
    parser_51_test_set_corpus = {u'Gold_2_test': corpora[u'Gold 2 test']}
    parser_52_test_set_corpus = {u'Gold_3_test': corpora[u'Gold 3 test']}
    parser_53_test_set_corpus = {u'Gold_4_test': corpora[u'Gold 4 test']}
    parser_54_test_set_corpus = {u'Gold_5_test': corpora[u'Gold 5 test']}

    parser_55_summaries = researcher.evaluate_parser_against_corpora(parser_55,
        parser_55_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True)[0]
    parser_51_summaries = researcher.evaluate_parser_against_corpora(parser_51,
        parser_51_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True)[0]
    parser_52_summaries = researcher.evaluate_parser_against_corpora(parser_52,
        parser_52_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True)[0]
    parser_53_summaries = researcher.evaluate_parser_against_corpora(parser_53,
        parser_53_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True)[0]
    parser_54_summaries = researcher.evaluate_parser_against_corpora(parser_54,
        parser_54_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True)[0]

    summaries = (parser_55_summaries, parser_51_summaries, parser_52_summaries,
            parser_53_summaries, parser_54_summaries)

    #pp.pprint(parser_55_summaries)
    #print
    #pp.pprint(parser_51_summaries)
    #print
    #pp.pprint(parser_52_summaries)
    #print
    #pp.pprint(parser_53_summaries)
    #print
    #pp.pprint(parser_54_summaries)

    evaluation = {}
    for key in summaries[0].keys():
        try:
            value = sum(s[key] for s in summaries) / float(len(summaries))
            evaluation[key] = value
        except:
            pass
    pprint.pprint(evaluation)
    """



    """
    # Thesis Parser 2 -- Frantz (1991) phon *FLATTENED*, F&R (1995) lexicon
    ################################################################################
    # This is one parser that is recreated five times with the five gold standard
    # training set-derived LMs (see above) and then tested with the relevant test set.

    # Phonology: #51 "Blackfoot phonology from Frantz (1991) with prominence and length distinctions flattened"
    # Morphology: #61 "Morphology with morphotactics drawn from well analyzed words in the data set"
    # Language Models: 
    #     #40 "Language model based on corpus 'Gold 1 training'."
    #     #41 "Language model based on corpus 'Gold 2 training'."
    #     #42 "Language model based on corpus 'Gold 3 training'."
    #     #43 "Language model based on corpus 'Gold 4 training'."
    #     #44 "Language model based on corpus 'Gold 5 training'."

    #for lm_id in (45, 46, 47, 48, 49):
        #researcher.create_thesis_parser_2(lm_id, force_recreate=True)
        #print '\n\n\n'

    # The result of the above is that I have the following parsers (saved locally too):
    #     #55 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #40"
    #     #51 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #41"
    #     #52 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #42"
    #     #53 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #43"
    #     #54 "Morphological parser for Blackfoot as described in Dunham (2014) with LM #44"

    # Test the parser on its test sets ...
    # Test the parser against all corpora and generate a list of success/failure summaries

    # This flattener function removes accent marking on vowels and shortens all long
    # segments. It should do exactly what the shorten and noAccentedVowels FSTs do
    # in the phonology of this parser.
    def flattener(input_):
        p = re.compile(u'([ptkmnsaio])(\\1)*')
        return p.sub('\\1', input_.replace(u'a\u0301', u'a').replace(
            u'i\u0301', u'i').replace(u'o\u0301', u'o'))

    record = cPickle.load(open('record.pickle', 'rb'))
    parsers = record['parsers']
    parser_61 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #45']
    #parser_62 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #46']
    #parser_63 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #47']
    #parser_64 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #48']
    #parser_65 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #49']

    #corpora = researcher.get_corpora_locally(force_recreate=force_recreate)
    corpora = record['corpora']
    parser_61_test_set_corpus = {u'Gold_1_test': corpora[u'Gold 1 test']}
    #parser_62_test_set_corpus = {u'Gold_2_test': corpora[u'Gold 2 test']}
    #parser_63_test_set_corpus = {u'Gold_3_test': corpora[u'Gold 3 test']}
    #parser_64_test_set_corpus = {u'Gold_4_test': corpora[u'Gold 4 test']}
    #parser_65_test_set_corpus = {u'Gold_5_test': corpora[u'Gold 5 test']}
    pprint.pprint(parser_61_test_set_corpus)

    # Note how the flattener function is passed as the preflight kw argument in the following ...
    parser_61_summaries = researcher.evaluate_parser_against_corpora(parser_61,
        parser_61_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_62_summaries = researcher.evaluate_parser_against_corpora(parser_62,
        parser_62_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_63_summaries = researcher.evaluate_parser_against_corpora(parser_63,
        parser_63_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_64_summaries = researcher.evaluate_parser_against_corpora(parser_64,
        parser_64_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_65_summaries = researcher.evaluate_parser_against_corpora(parser_65,
        parser_65_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]

    summaries = (parser_61_summaries, parser_62_summaries, parser_63_summaries,
            parser_64_summaries, parser_65_summaries)

    evaluation = {}
    for key in summaries[0].keys():
        try:
            value = sum(s[key] for s in summaries) / float(len(summaries))
            evaluation[key] = value
        except:
            pass
    pprint.pprint(evaluation)
    """
    

    # Thesis Parser 2b -- Frantz (1991) phon *FLATTENED*, F&R (1995) lexicon, CATEGORIAL!!!
    ################################################################################
    # This is one parser that is recreated five times with the five gold standard
    # training set-derived CATEGORIAL LMs (see above) and then tested with the relevant test set.

    # Phonology: #51 "Blackfoot phonology from Frantz (1991) with prominence and length distinctions flattened"
    # Morphology: #61 "Morphology with morphotactics drawn from well analyzed words in the data set"
    # Language Models: 
    #     #54 'Categorial Language model based on corpus #371 "Gold 1 training".'
    #     #55 'Categorial Language model based on corpus #373 "Gold 2 training".'
    #     #56 'Categorial Language model based on corpus #375 "Gold 3 training".'
    #     #57 'Categorial Language model based on corpus #377 "Gold 4 training".'
    #     #58 'Categorial Language model based on corpus #379 "Gold 5 training".'

    #for lm_id in (54, 55, 56, 57, 58):
        #researcher.create_thesis_parser_2(lm_id, force_recreate=True)
        #print '\n\n\n'

    # The result of the above is that I have the following parsers (saved locally too):
    #     #66 'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #54'
    #     #67 'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #55'
    #     #68 'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #56'
    #     #69 'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #57'
    #     #70 'Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #58'

    # Test the parser on its test sets ...
    # Test the parser against all corpora and generate a list of success/failure summaries

    def flattener(input_):
        p = re.compile(u'([ptkmnsaio])(\\1)*')
        return p.sub('\\1', input_.replace(u'a\u0301', u'a').replace(
            u'i\u0301', u'i').replace(u'o\u0301', u'o'))

    record = cPickle.load(open('record.pickle', 'rb'))
    parsers = record['parsers']
    parser_66 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #54']
    parser_67 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #55']
    parser_68 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #56']
    parser_69 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #57']
    parser_70 = parsers['Morphological parser #2 ("Flattener") for Blackfoot as described in Dunham (2014) with LM #58']

    #corpora = researcher.get_corpora_locally(force_recreate=force_recreate)
    corpora = record['corpora']
    parser_66_test_set_corpus = {u'Gold_1_test': corpora[u'Gold 1 test']}
    parser_67_test_set_corpus = {u'Gold_2_test': corpora[u'Gold 2 test']}
    parser_68_test_set_corpus = {u'Gold_3_test': corpora[u'Gold 3 test']}
    parser_69_test_set_corpus = {u'Gold_4_test': corpora[u'Gold 4 test']}
    parser_70_test_set_corpus = {u'Gold_5_test': corpora[u'Gold 5 test']}

    # Note how the flattener function is passed as the preflight kw argument in the following ...
    parser_66_summaries = researcher.evaluate_parser_against_corpora(parser_66,
        parser_66_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_67_summaries = researcher.evaluate_parser_against_corpora(parser_67,
        parser_67_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_68_summaries = researcher.evaluate_parser_against_corpora(parser_68,
        parser_68_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_69_summaries = researcher.evaluate_parser_against_corpora(parser_69,
        parser_69_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]
    parser_70_summaries = researcher.evaluate_parser_against_corpora(parser_70,
        parser_70_test_set_corpus, force_recreate=True, get_phonology_success=True,
        test_phonology=True, preflight=flattener)[0]

    summaries = (parser_66_summaries, parser_67_summaries, parser_68_summaries,
            parser_69_summaries, parser_70_summaries)

    evaluation = {}
    for key in summaries[0].keys():
        try:
            value = sum(s[key] for s in summaries) / float(len(summaries))
            evaluation[key] = value
        except:
            pass
    pprint.pprint(evaluation)




    """
    # All this stuff is about trying to see why the parser is not handling
    # unicode characters correctly. The phonology does just fine and so does the morphology;
    # The problem seems to be the morphophonology...
    # Proposed solution: change the morphology to regex, not lexc, and see what happens ...
    transcriptions = [u'nitsspiyi', u'nita\u0301i\u0301hpiyi']
    morpheme_sequences = [u'nit-ihpiyi', u'nit-a\u0301-ihpiyi']
    parses = researcher.parse(parser_54, transcriptions)
    pprint.pprint(parses) # the one with the accents will have no parses ...
    srs = researcher.get_parse_module(parser_54).phonology.applydown(morpheme_sequences)
    pprint.pprint(srs) # the phonology can applydown the accent-containing morpheme sequence, no problem
    morphology = researcher.get_parse_module(parser_54).morphology
    morph_down = researcher.get_parse_module(parser_54).morphology.applydown(morpheme_sequences)
    pprint.pprint(morph_down) # the morphology recognizes the accent-containing morpheme sequence, no problem
    morph_up = researcher.get_parse_module(parser_54).morphology.applyup(morpheme_sequences)
    pprint.pprint(morph_up)
    parser_54_obj = researcher.get_parse_module(parser_54).parser
    morphophon_up = parser_54_obj.applyup(transcriptions)
    pprint.pprint(morphophon_up)
    """









    """

    # Restrict what we're working with to a subset of the corpora just created, if desired.
    #corpora = dict((key, value) for key, value in researcher.record['corpora'].iteritems()
    #               if 'local_copy_path' in value and value['id'] == 273)
    #corpus_name = u'Corpus of forms, with elicitor last_name as Dunham, that contain well analyzed Blackfoot words'
    corpus_name = u'Corpus of forms that contain well analyzed Blackfoot words'
    corpora_subset = dict((key, value) for key, value in corpora.iteritems()
            if 'local_copy_path' in value and value['name'] == corpus_name)


    # Toy Parser
    ################################################################################

    # Create a toy parser for debugging!
    #toy_parser = researcher.create_toy_parser(force_recreate=force_recreate)


    # Parser 1 
    ################################################################################

    # * phonology: Frantz (1997)
    # * morphology: sentential forms corpus
    # * LM: sentential forms corpus
    # * takes up to 5 minutes to create, generate, and compile

    # Create a morphological parser for Blackfoot
    parser_1 = researcher.create_parser_1(force_recreate=force_recreate)

    # Run a test to ensure that the parser functions at a minimal level.
    #researcher.test_parser(parser_1)

    # Test the parser against all corpora and generate a list of success/failure summaries
    # for each parser-corpus pair. WARNING: takes about 2-3 mins. However, the summaries are
    # cached and the cached data can be retrieved by setting ``force_recreate`` to False.
    parser_summaries = researcher.evaluate_parser_against_corpora(parser_1,
        corpora_subset, force_recreate=True, get_phonology_success=True,
        test_phonology=True)
    pp.pprint(parser_summaries)
    #parser_summaries = [ps for ps in parser_summaries
    #    if ps['relation'] == 'all' and ps['type'] == 'well']

    # Notes:
    # It took 14m18s (i.e., 858s) to parse the 1,357 unique words in the corpus of
    # forms, with elicitor last_name as Dunham, that contain well analyzed Blackfoot
    # words. That's 1.58 words per second.
    # It took 53m22s (i.e., 3,202s) to parse all 6,577 unique transcriptions in
    # the corpus of forms that contain well analyzed Blackfoot words. That's 2.02 words per second.
    # It took 61m45s (i.e., 3,705s) to parse all 8,431 unique transcriptions in
    # the corpus of forms that contain Blackfoot words. That's 2.28 words per second.
    # well      elicitor Dunham, (#298)        1357       8.47%    9.87%    85.82%    10.92%
    # well      all  (#277)                    6577       8.27%    9.59%    86.21%    16.80%
    # well      all  (#277)                    6577       1.64%    9.59%    17.12%    16.80%
    #researcher.pretty_print_parse_summaries(parser_summaries)




    # Parser 2  "The Overgenerator"
    ################################################################################

    # * phonology: Frantz (1997) extended, i.e., made to overgenerate
    # * morphology: sentential forms corpus
    # * LM: sentential forms corpus

    #parser_2 = researcher.create_parser_2(force_recreate=force_recreate)
    #parser_2_summaries = researcher.evaluate_parser_against_corpora(parser_2, corpora)


    # Parser 3
    ################################################################################

    # * phonology: Frantz (1997) extended with syllabification and default accent
    # * morphology: sentential forms corpus
    # * LM: sentential forms corpus

    #parser_3 = researcher.create_parser_3(force_recreate=force_recreate)
    #parser_3_summaries = researcher.evaluate_parser_against_corpora(parser_3, corpora)


    # Parser 4
    ###############################################################################

    # * phonology: misspell
    # * morphology: sentential forms corpus, impoverished morphemes
    # * LM: sentential forms corpus

    #parser_4 = researcher.create_parser_4(force_recreate=force_recreate)
    #parser_4_summaries = researcher.evaluate_parser_against_corpora(parser_4, corpora, test_phonology=False)


    # Parser 5
    ###############################################################################

    # * phonology: misspell
    # * morphology: sentential forms corpus, *rich* morphemes
    # * LM: sentential forms corpus

    #parser_5 = researcher.create_parser_5(force_recreate=force_recreate)
    #parser_5_summaries = researcher.evaluate_parser_against_corpora(parser_5, corpora, test_phonology=False, batch_size=100, force_recreate=True)


    # Parser 6 -- the "Dunham enterer" parser
    ###############################################################################

    # * phonology: misspell
    # * morphology: dunham entered, well analyzed words, *rich* morphemes.
    # * LM: dunham entered, well analyzed words.

    #parser_6 = researcher.create_parser_dunham_enterer(force_recreate=force_recreate)
    #parser_6_summaries = researcher.evaluate_parser_against_corpora(parser_6,
    #        corpora, test_phonology=False, batch_size=100)


    # Parser 7 -- the "Dunham enterer, categorial LM" parser
    ###############################################################################

    # * phonology: misspell
    # * morphology: dunham entered, well analyzed words.
    # * LM: dunham entered, well analyzed words, *categorial*.

    #parser_7 = researcher.create_parser_dunham_enterer_categorial(force_recreate=False)
    #parser_7_summaries = researcher.evaluate_parser_against_corpora(parser_7,
            #corpora, test_phonology=False)


    # Parser 8 -- the "Louie elicited" parser
    ###############################################################################

    # NOTE: THIS PARSER FAILED.  It attempted to use the ``include_unknowns``
    # attribute of morphologies in order to create a useful morphology from
    # Louie's data.  It failed because it resulted in a massively over-generative
    # morphophonology that crashed the system.  This is because the default
    # implementation of the ``include_unknowns`` option resulted in the creation
    # of an ``unkwnownCat`` foma regex that allowed any uncategorized morpheme to
    # occur in any position that any other uncategorized morpheme was found to
    # occur in.  This, combined with the fact that Louie uses "M" and "S", etc. 
    # as abbreviations for proper nouns in her analyses and because these
    # particular consonants are deleted by Frantz's phonology, resulted in a
    # massively over-generative morphophonology.  I attempted, in response, to
    # create a more intelligent algorithm for assigning extant categories to
    # uncategorized morphemes.  This turned out to be more difficult than
    # anticipated and though it is well within the realm of possibility, it is
    # not something I have the time to pursue right now.  This is a good lesson
    # about why tests should remain restricted to *well* analyzed words.

    # * phonology: phonology 2 (Frantz + modifications for dunham enterer corpus)
    # * morphology: based on analyzed Louie-elicited words (create_morphology_louie_elicitor)
    # * LM: based on analyzed Louie-elicited words (create_language_model_louie_elicitor)

    #parser_8 = researcher.create_parser_louie_elicitor(force_recreate=True)
    #parser_8_summaries = researcher.evaluate_parser_against_corpora(parser_8, corpora)


    # Parser 9 -- the Weber (2013) parser
    ###############################################################################

    # * phonology: phonology 3 (Frantz + modifications that implement morphologically
            # conditioned phonological alternations a la Weber (2013).
    # * morphology: based on well analyzed words
    # * LM: based on well analyzed words

#    well      source Weber, (#269)           67         31.34%    31.34%    100.00%    0.00%
#    well      source Weber, (#269)           67         14.93%    14.93%    100.00%    0.00%
#    well      source Weber, (#269)           67         26.87%    26.87%    100.00%    0.00%

    parser_9 = researcher.create_parser_weber_2013(force_recreate=True)
    parser_9_summaries = researcher.evaluate_parser_against_corpora(parser_9, corpora,
        test_phonology=False, get_phonology_success=False, vocal=True, force_recreate=True)


    """


    # TODO: create a Louie parser that crucially contains a lexicon that contains all of the 
    #       lexical items that *she* uses.  This is probably why her parse accuracy rates are
    #       so low.
    # TODO: write function to evaluate the phonology against a corpus!


    """

    researcher.record['phonologies'] = {}
    researcher.dump_record()
    log.silent=True
    phonology_2 = researcher.create_phonology_2(True)
    log.silent=False
    unsuccessful, test_count = researcher.run_phonology_tests(phonology_2)
    successful_count = test_count - len(unsuccessful)
    log.silent=False
    log.info('%s / %s' % (successful_count, test_count))
    #log.info(unsuccessful)
    """


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
import time
import locale
import sys
import optparse
from researcher import ParserResearcher, Keeper, Log

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
        conjuncts = [['or', [['Form', 'syntactic_category', 'name', '=', u'sent'],
                             ['Form', 'morpheme_break', 'like', '% %'],
                             ['Form', 'morpheme_break', 'like', '%-%']]],
                     ['Form', 'syntactic_category_string', '!=', None],
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
        script_path = 'resources/blackfoot_phonology.script'
        return self.create_phonology_x(force_recreate=force_recreate, name=name,
            script_path=script_path, description=description)

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
        assert parses == transcriptions
        log.info('Parser "%s" parses correctly via request.' % parser['name'])

        # Test the locally saved parser
        # Note that ``parse_locally`` returns ``Parse`` instances, not strings.
        parses = self.parse_locally(parser, transcriptions.keys())
        assert (dict((transcription, parse.parse) for transcription, (parse, candidates) in parses.iteritems())
                == transcriptions)
        log.info('Parser "%s" parses correctly locally.' % parser['name'])

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


    def create_corpora(self, force_recreate=False, **kwargs):
        """Create a bunch of corpora and pickle them locally.

        """

        log.info(u'Creating corpora.')
        corpora = {}

        # Create the three main corpora.
        words_corpus = self.save_words_corpus(force_recreate=force_recreate)
        analyzed_words_corpus = self.save_analyzed_words_corpus(
            force_recreate=force_recreate)
        well_analyzed_words_corpus = self.save_well_analyzed_words_corpus(
            force_recreate=force_recreate)

        corpora[words_corpus['name']] = words_corpus
        corpora[analyzed_words_corpus['name']] = analyzed_words_corpus
        corpora[well_analyzed_words_corpus['name']] = well_analyzed_words_corpus

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
                corpus = self.save_words_corpus(
                    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                corpora[corpus['name']] = corpus

                corpus = self.save_analyzed_words_corpus(
                    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                corpora[corpus['name']] = corpus

                corpus = self.save_well_analyzed_words_corpus(
                    force_recreate=force_recreate, relation=relation, attribute=attribute, value=value)
                corpora[corpus['name']] = corpus
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


    def parse_corpus(self, parser, corpus, batch_size=0):
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

        corpus_list = cPickle.load(open(corpus['local_copy_path'], 'rb'))
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

    # Determines whether resources are regenerated/recreated/recompiled even
    # when said resources have been persisted.
    force_recreate = False

    # This will reset the pickled record of the researcher to an empty dict.
    # Calling ``clear_record()`` is necessary for forcing the researcher to
    # repeat his research.
    #researcher.clear_record(clear_corpora=False)


    ################################################################################
    # Research!
    ################################################################################


    # Corpora
    ################################################################################

    # Create a bunch of corpora that will be useful later on. This can take a while,
    # but the corpora are persisted as pickles, so it should only need to be done once.
    # I.e., researcher.record['corpora'] wil contain the corpus metadata and
    # localstore/corpora will contain the corpus pickles.
    #corpora = researcher.create_corpora(force_recreate=force_recreate)

    # Restrict what we're working with to a subset of the corpora just created, if desired.
    corpora = dict((key, value) for key, value in researcher.record['corpora'].iteritems()
                   if 'local_copy_path' in value and value['id'] == 273)
    # 218 is Bliss 96-word corpus
    # 233 is Dunham entered well analyzed corpus
    # 221 is Dunham elicited well analyzed corpus
    # 226 is Louie elicited analyzed corpus (1,198 words)
    # 273 is Weber 2013 forms (79 forms)


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

    # Create a morphological parser for Blackfoot and make sure it works.
    parser_1 = researcher.create_parser_1(force_recreate=force_recreate)
    researcher.test_parser(parser_1)

    # Test the parser against all corpora and print a summary.
    # WARNING: no caching here, takes about 2-3 mins ...
    parser_1_summaries = researcher.evaluate_parser_against_corpora(parser_1,
        corpora, force_recreate=True, get_phonology_success=True,
        test_phonology=True)

    """

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

    all_parse_summaries = parser_1_summaries
    summaries = {}
    for summary in all_parse_summaries:
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
            [u'%0.2f%s' % (p, chr(37)) for p in summaries[summary]['correctly_parsed_percent']])
        morphophonology_success_percent = u'    '.join(
            [u'%0.2f%s' % (p, chr(37)) for p in summaries[summary]['morphophonology_success_percent']])
        phonology_success_percent = u'    '.join(
            [u'%0.2f%s' % (p, chr(37)) for p in summaries[summary]['phonology_success_percent']])
        lm_success_percent = u'    '.join(
            [u'%0.2f%s' % (p, chr(37)) for p in summaries[summary]['lm_success_percent']])

        print u'%s    %s    %s    %s    %s' % (
            summary, correctly_parsed_percent, morphophonology_success_percent,
            lm_success_percent, phonology_success_percent)


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


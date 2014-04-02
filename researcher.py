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

"""OLD Researcher --- for doing parser-focused research via a live OLD application.

The primary class defined here is ParserResearcher, which represents a
researcher using a live OLD web service to do research related to the creation
and testing of morphological parsers and their attendant machinery.

"""

import codecs
import cPickle
import os
import zipfile
import errno
import imp
import locale
import sys
from oldclient import OLDClient, Log

# Wrap sys.stdout into a StreamWriter to allow writing unicode.
# This allows piping of unicode output.
# See http://stackoverflow.com/questions/4545661/unicodedecodeerror-when-redirecting-to-file
#sys.stdout = codecs.getwriter(locale.getpreferredencoding())(sys.stdout)

# The global ``log`` instance can be used instead of ``print`` and output can be
# silenced by setting ``log.silent`` to ``True``.
log = Log()


class Keeper(object):
    """Filters everything from a unicode string except the characters in ``keep``.

    """

    def __init__(self, keep):
        self.keep = set(map(ord, keep))

    def __getitem__(self, n):
        if n not in self.keep:
            return None
        return unichr(n)

    def __call__(self, s):
        return unicode(s).translate(self)


class ParserResearcher(object):
    """Functionality for performing parser-related research on a live OLD web service.

    Provides general-purpose methods for creating searches, corpora,
    morphologies, phonologies, morpheme language models and morphological
    parsers.

    Also provides convenience methods for creating specific instances of the
    above-mentioned parser-related resources.

    TODO:

    1. unknown_category and morpheme_splitter need to be property attributes
       of the researcher's old_client instance. See the Researcher.well_analyzed
       method.

    """

    def __init__(self, username, password, host, **kwargs):
        """Connect and authenticate to a live OLD web application.

        """

        port = kwargs.get('port', '80')
        self.my_dir = os.path.abspath(os.path.dirname(__file__))
        self.set_record_path(**kwargs)
        self.setup_localstore(**kwargs)
        self.old = OLDClient(host, port)
        try:
            assert self.old.login(username, password) == True
        except AssertionError:
            print ('Unable to login to the OLD application at %s:%s using '
                'username %s and password %s') % (host, port, username,
                password)
            sys.exit()

    # This is what is stored in record.pickle
    default_record = {
        'searches': {},
        'corpora': {},
        'morphologies': {},
        'phonologies': {},
        'language models': {},
        'parsers': {},
        'parse_summaries': {},
        'users': {}
    }

    def set_record_path(self, **kwargs):
        record_file = kwargs.get('record_file')
        if record_file:
            self.record_path = os.path.join(self.my_dir, record_file)

    def setup_localstore(self, **kwargs):
        localstore = kwargs.get('localstore', 'localstore')
        self.localstore = os.path.join(self.my_dir, localstore)
        self.make_directory_safely(self.localstore)
        for object_type in self.default_record.keys():
            subdir = os.path.join(self.localstore, object_type)
            self.make_directory_safely(subdir)

    @property
    def record(self):
        """The ``record`` of a researcher is a pickled dict for persisting
        researcher state.  It is useful for avoiding repetition of costly
        computations.

        """

        try:
            return self._record
        except AttributeError:
            try:
                self._record = cPickle.load(open(self.record_path, 'rb'))
            except Exception:
                self._record = self.default_record
            return self._record

    @record.setter
    def record(self, value):
        self._record = value

    def dump_record(self):
        """Try to pickle the researcher's record.

        """

        try:
            cPickle.dump(self.record, open(self.record_path, 'wb'))
        except Exception:
            log.warn(u'Attempt to to pickle-dump to %s failed.' % self.record_path)

    def clear_record(self, clear_corpora=False):
        """Set record to {} and persist.

        """

        log.info(u"Clearing the researcher's record.")
        corpora = self.record['corpora']
        self.record = self.default_record
        if not clear_corpora:
            self.record['corpora'] = corpora
        self.dump_record()

    def make_directory_safely(self, path):
        """Create a directory and avoid race conditions.

        Taken from
        http://stackoverflow.com/questions/273192/python-best-way-to-create-directory-if-it-doesnt-exist-for-file-write.
        Listed as ``make_sure_path_exists``.

        """

        try:
            os.makedirs(path)
        except OSError, exception:
            if exception.errno != errno.EEXIST:
                raise

    ################################################################################
    # General-purpose methods for creating parser-related resources.
    ################################################################################

    def create_search(self, name, query, **kwargs):
        """Create an OLD form search.

        :param unicode name: the name of the search.
        :param dict query: the search/query that forms the core of the search.
        :returns: a dict representing the search.

        Create the specified search; if one already exists with the specified
        name, update it if necessary.

        """

        description = kwargs.get('description', None)
        params = self.old.form_search_create_params.copy()
        params.update({
            'name': name,
            'description': description,
            'search': query
        })
        create_response = self.old.post('formsearches', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            search = self.old.search('formsearches',
                {'query': {'filter': ['FormSearch', 'name', '=', name]}})[0]
            if search['search'] != query:
                result = self.old.put('formsearches/%s' % search['id'], params)
            else:
                result = search
        elif create_response.get('id'):
            result = create_response
        else:
            log.info(create_response)
            raise Exception('Unable to create search named "%s".' % name)
        return result

    def create_corpus(self, name, **kwargs):
        """Create an OLD corpus based on an existing OLD search model.

        :param unicode name: the name of the corpus.
        :param int search_id: the ``id`` value of an OLD search model to be used
            to create the corpus.
        :returns: a dict representing the newly created corpus.

        Create the specified corpus; if one already exists with the specified name,
        update it if necessary.

        """

        search_id = kwargs.get('search_id')
        content = kwargs.get('content')
        params = self.old.corpus_create_params.copy()
        params.update({
            'name': name,
            'form_search': search_id,
            'content': content
        })
        create_response = self.old.create('corpora', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            # A corpus with this name exists already.
            corpus = [c for c in self.old.get('corpora') if c['name'] == name][0]
            corpus_form_search = corpus.get('form_search', {})
            if not corpus_form_search or corpus_form_search.get('id') != search_id:
                # The existing corpus has the wrong form_search value -- update it.
                result = self.old.put('corpora/%s' % corpus['id'], params)
            else:
                result = corpus
        elif create_response.get('id'):
            result = create_response
        else:
            raise Exception('Unable to create corpus named "%s".' % name)
        return result

    def get_corpus_forms(self, corpus):
        query = {
            'query': {
                'filter': ['Form', 'corpora', 'id', '=', corpus['id']]}}
        return self.old.search('forms', query)

    def well_analyzed(self, word):
        """Return ``True`` if the word is well analyzed, i.e., contains no unknown
        categories in its syntactic category string; else ``False``.

        :param tuple word: a quadruple representing a word: (tr, mb, mg, cat).

        """

        # Some BLA OLD-specific ad hoc stipulations.
        # (Really these should be retrieved from the live application.)
        unknown_category = u'?'
        splitter = lambda w: w.split('-')
        return unknown_category not in splitter(word[3])

    def get_form_words(self, form_list, filter_=False):
        """Return a sorted list of all unique words in the form dicts of ``form_list``.

        :param bool filter_: if set to ``True``, a word will not be added if it
            is not well analyzed according to ``self.well_analyzed``.

        The representation of each word is a quadruple of the form (tr, mb, mg, cat).

        """

        words = set()
        for form in form_list:
            if form['syntactic_category_string']:
                for word in zip(
                    form['transcription'].split(),
                    form['morpheme_break'].split(),
                    form['morpheme_gloss'].split(),
                    form['syntactic_category_string'].split()):
                    if not filter_ or self.well_analyzed(word):
                        words.add(word)
            else:
                for word in form['transcription'].split():
                    words.add((word, None, None, None))
        words = sorted(words)
        return words

    def create_phonology(self, name, script, **kwargs):
        """Create a foma phonology.

        :param unicode name: the name of the phonology.
        :param unicode script: the ``script`` value of the phonology.
        :returns: a dict representing the newly created phonology.

        Create the specified phonology; if one already exists with the
        specified name, update it if necessary.

        """

        description = kwargs.get('description')
        params = self.old.phonology_create_params.copy()
        params.update({
            'name': name,
            'description': description,
            'script': script
        })
        create_response = self.old.create('phonologies', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            # A phonology with this name exists already.
            phonology = [p for p in self.old.get('phonologies') if p['name'] == name][0]
            if phonology.get('script') != self.old.normalize(script):
                # The existing phonology has an incorrect script value -- update it.
                result = self.old.put('phonologies/%s' % phonology['id'], params)
                return result
            else:
                return phonology
        elif create_response.get('id'):
            return create_response
        else:
            raise Exception('Unable to create phonology named "%s".' % name)

    def create_morphology(self, name, **kwargs):
        """Create a morphology.

        :param unicode name: the name of the morphology.
        :param int kwargs['lexicon_corpus_id']: the ``id`` value of a corpus for
            generating the lexicon.
        :param int kwargs['rules_corpus_id']: the ``id`` value of a corpus for
            generating the rules.
        :returns: a dict representing the newly created morphology.

        Create the specified morphology; if one already exists with the
        specified name, update it if necessary.

        """

        script_type = kwargs.get('script_type', 'regex')
        rich_upper = kwargs.get('rich_upper', True)
        rich_lower = kwargs.get('rich_lower', False)
        lexicon_corpus_id = kwargs.get('lexicon_corpus_id')
        rules_corpus_id = kwargs.get('rules_corpus_id')
        include_unknowns = kwargs.get('include_unknowns')
        extract_morphemes_from_rules_corpus = kwargs.get(
            'extract_morphemes_from_rules_corpus')

        rules = kwargs.get('rules')
        morphology_params = self.old.morphology_create_params.copy()
        morphology_params.update({
            'name': name,
            'lexicon_corpus': lexicon_corpus_id,
            'rules_corpus': rules_corpus_id,
            'rules': rules,
            'script_type': script_type,
            'rich_upper': rich_upper,
            'rich_lower': rich_lower,
            'include_unknowns': include_unknowns,
            'extract_morphemes_from_rules_corpus': extract_morphemes_from_rules_corpus
        })
        create_response = self.old.create('morphologies', morphology_params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            # A morphology with this name exists already.
            morphology = [m for m in self.old.get('morphologies') if m['name'] == name][0]
            if ((lexicon_corpus_id and morphology['lexicon_corpus'] and
                    morphology['lexicon_corpus']['id'] != lexicon_corpus_id) or
                (rules_corpus_id and morphology['rules_corpus'] and
                    morphology['rules_corpus']['id'] != rules_corpus_id) or
                (rules and morphology['rules'] != rules) or
                morphology['script_type'] != script_type or morphology['rich_upper'] != rich_upper):
                # The existing morphology has some incorrect values -- update it.
                return self.old.put('morphologies/%s' % morphology['id'], morphology_params)
            else:
                return morphology
        elif create_response.get('id'):
            return create_response
        else:
            print create_response
            raise Exception('Unable to create morphology named "%s".' % name)

    def generate_morphology(self, morphology_id, compile_=False, vocal=False):
        """Generate and (optionally) compile a morphology.

        :param int morphology_id: the ``id`` value of the morphology to generate.
        :param bool compile_: to compile or not to compile.
        :param bool vocal: to voice complaints or not to so voice.
        :returns: a dict representation of the  morphology object.

        """

        if compile_:
            response = self.old.put('morphologies/%s/generate_and_compile' % morphology_id)
            key = 'compile_attempt'
            attempt = response[key]
            wait = 10
        else:
            response = self.old.put('morphologies/%s/generate' % morphology_id)
            key = 'generate_attempt'
            attempt = response[key]
            wait = 1
        requester = lambda: self.old.get('morphologies/%s' % morphology_id)
        response = self.old.poll(requester, key, attempt, log, wait=wait,
            vocal=vocal, task_descr='"generate/compile morphology %s"' % morphology_id)
        return response

    def compile_phonology(self, phonology_id):
        """Compile a phonology.

        :param int phonology_id: the ``id`` value of the phonology to generate.
        :returns: a dict representation of the phonology object.

        """

        response = self.old.put('phonologies/%s/compile' % phonology_id)
        key = 'compile_attempt'
        attempt = response[key]
        wait = 1
        requester = lambda: self.old.get('phonologies/%s' % phonology_id)
        response = self.old.poll(requester, key, attempt,
            log, wait=wait, vocal=True, task_descr='"compile phonology %s"' % phonology_id)
        return response

    def create_language_model(self, name, corpus_id, **kwargs):
        """Create a morpheme language model.

        :param unicode name: the name of the language model.
        :param int corpus_id: the ``id`` value of a corpus for generating the LM.
        :param unicode kwargs['toolkit']: the toolkit to be used to generate the LM.
        :returns: a dict representing the newly created language model.

        Create the specified language model; if one already exists with the
        specified name, update it if necessary.

        """

        toolkit = kwargs.get('toolkit', 'mitlm')
        categorial = kwargs.get('categorial', False)
        params = self.old.morpheme_language_model_create_params.copy()
        params.update({
            'name': name,
            'corpus': corpus_id,
            'toolkit': toolkit,
            'categorial': categorial
        })
        create_response = self.old.create('morphemelanguagemodels', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            # An LM with this name exists already.
            language_model = [lm for lm in self.old.get('morphemelanguagemodels')
                              if lm['name'] == name][0]
            lm_corpus = language_model.get('corpus')
            if not lm_corpus or lm_corpus.get('id') != corpus_id:
                # The existing LM has an incorrect corpus value -- update it.
                return self.old.put('morphemelanguagemodels/%s' % language_model['id'], params)
            else:
                return language_model
        elif create_response.get('id'):
            return create_response
        else:
            raise Exception('Unable to create language model named "%s".' % name)

    def generate_language_model(self, lm_id):
        """Generate the files of the LM using the toolkit.

        Note that the generate request and subsequent polling of the resource
        for termination are both performed.

        """

        response = self.old.put('morphemelanguagemodels/%s/generate' % lm_id)
        lm_generate_attempt = response['generate_attempt']
        requester = lambda: self.old.get('morphemelanguagemodels/%s' % lm_id)
        response = self.old.poll(requester, 'generate_attempt', lm_generate_attempt,
            log, wait=1, vocal=True, task_descr='"generate LM %s"' % lm_id)
        return response

    def create_parser(self, name, phonology_id, morphology_id, lm_id):
        """Create a morphological parser.

        :param unicode name: the name of the parser.
        :param int phonology_id: the ``id`` value of a phonology for generating the parser.
        :param int morphology_id: the ``id`` value of a morphology for generating the parser.
        :param int lm_id: the ``id`` value of a language model for generating the parser.
        :returns: a dict representing the newly created parser.

        Create the specified parser; if one already exists with the specified name,
        update it if necessary.

        """

        params = self.old.morphological_parser_create_params.copy()
        params.update({
            'name': name,
            'phonology': phonology_id,
            'morphology': morphology_id,
            'language_model': lm_id
        })
        create_response = self.old.create('morphologicalparsers', params)
        if create_response.get('errors') and 'name' in create_response['errors']:
            # A parser with this name exists already.
            parser = [p for p in self.old.get('morphologicalparsers')
                              if p['name'] == name][0]
            phonology = parser.get('phonology')
            morphology = parser.get('morphology')
            language_model = parser.get('language_model')
            if (not phonology or not morphology or not language_model or
                phonology.get('id') != phonology_id or
                morphology.get('id') != morphology_id or
                language_model.get('id') != lm_id):
                # The existing parser has incorrect values -- update it.
                return self.old.put('morphologicalparsers/%s' % parser['id'], params)
            else:
                return parser
        elif create_response.get('id'):
            return create_response
        else:
            raise Exception('Unable to create morphological parser named "%s".' % name)

    def compile_parser(self, parser_id):
        """Generate and compile a morphological parser.

        :param int parser_id: the ``id`` value of the parser to compile.
        :returns: the compiled parser object.

        """
        compile_response = self.old.put('morphologicalparsers/%s/generate_and_compile' % parser_id)
        compile_attempt = compile_response['compile_attempt']
        requester = lambda: self.old.get('morphologicalparsers/%s' % parser_id)
        response = self.old.poll(requester, 'compile_attempt', compile_attempt,
            log, wait=10, vocal=True, task_descr='"compile parser %s"' % parser_id)
        return response

    def save_parser_locally(self, id_, dirpath):
        """Request a parser export, save the .zip archive locally and unzip it. Return
        the absolute path to the directory containing the locally saved parser.

        """
        export_response = self.old.get('morphologicalparsers/%s/export' % id_,
            params=None, verbose=False)
        archive_path = os.path.join(dirpath, 'archive.zip')
        self.make_directory_safely(dirpath)
        try:
            with open(archive_path, 'wb') as f:
                f.write(export_response.content)
        except AttributeError:
            print 'error in writing archive to disk'
            raise
        zip_archive = zipfile.ZipFile(archive_path)
        zip_archive.extractall(dirpath)
        zip_archive.close()
        return os.path.join(dirpath, 'archive')

    def parse(self, parser, transcriptions):
        """Parse the ``transcriptions`` list using the OLD app's parser with ``id==parser['id']``.

        """
        return self.old.put('morphologicalparsers/%s/parse' % parser['id'],
                                      {'transcriptions': transcriptions})


    def parse_locally(self, parser, transcriptions, batch_size=0):
        """Return the locally stored parser's parses of ``transcriptions``.

        """
        parse_module = self.get_parse_module(parser)
        if batch_size:
            parses = {}
            n = len(transcriptions)
            for chunk in (transcriptions[pos: pos + batch_size] for pos in
                          xrange(0, len(transcriptions), batch_size)):
                chunk_parsed = parse_module.parser.parse(chunk, parse_objects=True)
                parses.update(chunk_parsed)
                print '%d of %d parsed' % (len(parses), n)
            return parses
        else:
            return parse_module.parser.parse(transcriptions, parse_objects=True)

    def get_parse_module(self, parser):
        """Return the imported-as-module executable ``lib/parse.py``.

        """

        parser_dir = parser['local_copy_path']
        parse_module_path = os.path.join(parser_dir, 'parse.py')
        return imp.load_source('archive', parse_module_path)

    def phonologize_locally(self, parser, morpheme_sequences):
        """Return the locally stored phonology's phonologizations (apply up) ``morpheme_sequences``.

        """

        return self.get_parse_module(parser).phonology.applydown(morpheme_sequences)

    def clean_transcription(self, transcription):
        """This method cleans transcriptions of certain characters. It will probably be
        overridden in language-specific researcher subclasses.

        """
        return transcription

    def inspect_parses(self, parser, parses, corpus_dict, corpus_id):
        """Iterate through parses and return a dict and a set:

        :param dict parser: attributes and values of a parser.
        :param dict parses: keys are transcriptions and values are 2-tuples whose first 
            element is a ``Parse`` instance and whose second is a list of candidates generated
            by the morphophonology.
        :param dict corpus_dict: keys are (uncleaned) transcriptions and values are list triples
            comprised of the word's morpho-phonemic transcription, its glosses and its categories.
        :param int corpus_id: the id of the corpus whose parses are being inspected.
        :returns: a 2-tuple consisting of objects that constitute a record of failed parses. The
            ``morpheme_sequences`` dict has sequences of user-supplied morpheme forms as keys
            and corresponding user-supplied transcriptions as values.  The ``category_sequences``
            set holds the sequences of categories and delimiters corresponding to these unparsed
            transcriptions.
        :side-effects: prettily write unparsed transcriptions (and any user-provided parses) to disk,
            e.g., in /localhost/parsers/parser_1/unparsed_corpus_1.txt

        """

        log.info('Inspecting parses of parser "%s".' % parser['name'])
        morpheme_sequences = {} # A dict from morpheme/delimiter sequences to lists of corresponding transcriptions
        category_sequences = set()
        key = 'parsers'
        parser_dir = os.path.join(self.localstore, key, 'parser_%s' % parser['id'])
        file_path = os.path.join(parser_dir, 'unparsed_corpus_%s.txt' % corpus_id)
        with codecs.open(file_path, 'w', 'utf8') as f:
            for transcription, (parse, candidates) in sorted(parses.items()):
                if not parse.parse:
                    cleaned_transcription = self.clean_transcription(transcription)
                    gold_parse = filter(None,
                        corpus_dict.get(transcription,
                                        corpus_dict.get(cleaned_transcription, [])))
                    if gold_parse:
                        morpheme_sequences.setdefault(gold_parse[0], set()).add(transcription)
                        if cleaned_transcription != transcription:
                            morpheme_sequences.setdefault(gold_parse[0], set()).add(cleaned_transcription)
                        category_sequences.add(gold_parse[2])
                    try:
                        f.write(u'%-30s%s\n' % (transcription, u' '.join(gold_parse)))
                    except:
                        f.write(u'%s\n' % transcription)
        log.info('Saved unparsed words to %s.' % file_path)
        return morpheme_sequences, category_sequences

    def save_phonological_failures(self, parser, phonologizations, morpheme_sequences, corpus_id):
        """Write a file containing parses and their user-supplied
        transcriptions where ``parser``'s phonology does *not* map the parse to
        any of the user-supplied transcriptions.  This is useful for
        determining where the phonology is insufficient.

        :param dict parser: holds attributes/values defining the parser.
        :param dict phonologizations: keys are morpheme sequence strings,
            values are lists of transcriptions generated from the morpheme
            sequences by the parser's phonology.
        :param dict morpheme_sequences: keys are morpheme sequence strings,
            values are lists of transcriptions supplied by the user data from the
            corpus.
        :param int corpus_id: the id of the corpus against which the parser is being tested.

        """

        key = 'parsers'
        parser_dir = os.path.join(self.localstore, key, 'parser_%s' % parser['id'])
        file_path = os.path.join(parser_dir, 'phonology_failures_corpus_%s.txt' % corpus_id)
        with codecs.open(file_path, 'w', 'utf8') as f:
            for morpheme_sequence in sorted(morpheme_sequences.keys()):
                transcriptions = morpheme_sequences[morpheme_sequence]
                ph_transcriptions = phonologizations[morpheme_sequence]
                if not set(transcriptions) & set(ph_transcriptions):
                    f.write('    users %-30s-> %s\n' % (morpheme_sequence,
                                                        u' '.join(sorted(transcriptions))))
                    try:
                        f.write('phonology %-30s-> %s\n\n' % (morpheme_sequence,
                                u' '.join(sorted(ph_transcriptions))))
                    except:
                        f.write('phonology %-30s-> None\n\n' % morpheme_sequence)
        log.info('Saved phonological failures to %s.' % file_path)

    def evaluate_parse(self, parses, corpus_dict, parser, vocal=False):
        """Evaluate a parse.

        :param dict parses: keys are transcriptions, values are 2-tuples: (parser.Parse(), [c1, c2, ...]).
        :param dict corpus_dict: keys are transcriptions, values are [break, gloss, category] triples (lists).
        :param class Parse: the Parse class from the parser module.
        :returns: a dict summarizing the success of the parser on a particular corpus.

        """

        n = len(parses)
        correctly_parsed = 0            # correct parse was generated
        candidates_generated = 0        # at least one candidate parse was generated
        morphophonology_success = 0     # the morphophonology generated the correct parse
        correct = []
        correct_mp = []
        incorrect_mp = []
        no_gen = []
        # Precision and recall; precision = correct_proposed_morphemes / total_proposed_morphemes
        # recall = correct_proposed_morphemes / total_actual_morphemes
        correct_proposed_morphemes = 0
        total_proposed_morphemes = 0
        total_actual_morphemes = 0
        for transcription, (parse_object, candidates) in parses.iteritems():
            cleaned_transcription = self.clean_transcription(transcription)
            no_gold = [u'nada', u'nada', u'nada']
            gold_parse = filter(None,
                corpus_dict.get(transcription,
                                corpus_dict.get(cleaned_transcription, no_gold)))
            gold_parse_object = parser.get_parse_object(gold_parse)
            total_actual_morphemes += len(gold_parse_object.morphemes)
            if parse_object.parse:
                candidates_generated += 1
                total_proposed_morphemes += len(parse_object.morphemes)
                correct_proposed_morphemes += len([m for m in parse_object.morphemes if m in gold_parse_object.morphemes])
                if parse_object.triplet == gold_parse:
                    correctly_parsed += 1
                    correct.append((transcription, gold_parse))
                if gold_parse in [c.triplet for c in candidates]:
                    morphophonology_success += 1
                    if parse_object.triplet != gold_parse:
                        correct_mp.append((transcription, gold_parse))
                else:
                    incorrect_mp.append((transcription, gold_parse, candidates))
            else:
                no_gen.append((transcription, gold_parse))
        if vocal:
            print 'Parse success %d/%d\n%s\n' % (len(correct), n, u'#'*80)
            print u'\n'.join('%-30s%-30s%-30s%-30s' % (tr, mb, mg, cat) for tr, (mb, mg, cat)
                    in sorted(correct, key=lambda x: x[0]))

            print '\n\nParse fail, morphophonology success %d/%d\n%s\n' % (len(correct_mp), n, u'#'*80)
            print u'\n'.join('%-30s%-30s%-30s%-30s' % (tr, mb, mg, cat) for tr, (mb, mg, cat)
                    in sorted(correct_mp, key=lambda x: x[0]))

            print '\n\nParse fail, morphophonology fail %d/%d\n%s\n' % (len(incorrect_mp), n, u'#'*80)
            print u'\n'.join('%-30s%-30s%-30s%-30s' % (tr, mb, mg, cat)
                for tr, (mb, mg, cat), candidates
                in sorted(incorrect_mp, key=lambda x: x[0]))

            print '\n\nNo candidates %d/%d\n%s\n' % (len(no_gen), n, u'#'*80)
            print u'\n'.join('%-30s%-30s%-30s%-30s' % (tr, mb, mg, cat) for tr, (mb, mg, cat)
                    in sorted(no_gen, key=lambda x: x[0]))

        # Precision and recall; precision = correct_proposed_morphemes / total_proposed_morphemes
        # recall = correct_proposed_morphemes / total_actual_morphemes
        precision = P = self.safe_div(correct_proposed_morphemes, total_proposed_morphemes)
        recall = R = self.safe_div(correct_proposed_morphemes, total_actual_morphemes)
        return {
            'attempted_count': n,
            'correctly_parsed_count': correctly_parsed,
            'correctly_parsed': correctly_parsed / float(n),
            'candidates_generated_count': candidates_generated,
            'candidates_generated': candidates_generated / float(n),
            'morphophonology_success_count': morphophonology_success,
            'morphophonology_success': morphophonology_success / float(n),
            'lm_success': self.safe_div(correctly_parsed, morphophonology_success),
            'precision': precision,
            'recall': recall,
            'f_measure': self.safe_div((2 * P * R), (P + R))
        }

    def safe_div(self, numer, denom):
        try:
            return numer / float(denom)
        except ZeroDivisionError:
            return 0.0

    def get_user_contributions(self, force_recreate=False):
        """Request the users of the OLD app and count their forms entered and elicited.

        """

        log.info(u'Retrieving users.')
        key = 'users'
        record = self.record.get(key, {})
        if record.get('created') and not force_recreate:
            log.info(u'Users have already been retrieved.')
            return record['users']

        users = self.old.get('users')
        for user in users:
            entered_query = {
                'query': {
                    'filter': ['Form', 'enterer', 'id', '=', user['id']]},
                'paginator': {
                    'page': 1, 'items_per_page': 1}}
            user['entered_count'] = self.old.search('forms', entered_query)['paginator']['count']
            elicited_query = {
                'query': {
                    'filter': ['Form', 'elicitor', 'id', '=', user['id']]},
                'paginator': {
                    'page': 1, 'items_per_page': 1}}
            user['elicited_count'] = self.old.search('forms', elicited_query)['paginator']['count']
        log.info(u'Users retrieved.')

        record = self.record.get(key, {})
        record['created'] = True
        record['users'] = users
        self.record[key] = record
        self.dump_record()
        return users

    def print_user_contributions(self, users):

        log.info('')
        log.info('Users ranked by forms entered')
        for user in sorted(users, key=lambda u: u['entered_count'], reverse=True):
            if user['entered_count'] > 0:
                log.info('%-40s %s' % (u'%s %s' % (user['first_name'], user['last_name']),
                                    user['entered_count']))

        log.info('')
        log.info('Users ranked by forms elicited')
        for user in sorted(users, key=lambda u: u['elicited_count'], reverse=True):
            if user['elicited_count'] > 0:
                log.info('%-40s %s' % (u'%s %s' % (user['first_name'], user['last_name']),
                                    user['elicited_count']))

    def get_phonology_success(self, parser, corpus_list):
        morpheme_sequences = [x[1] for x in corpus_list if x[1]]
        phonologizations = self.phonologize_locally(parser, morpheme_sequences)
        phonology_success = len([t for t, b, g, c in corpus_list if t in phonologizations.get(b, [])])
        return {'phonology_success_count': phonology_success,
                'phonology_success': phonology_success / float(len(corpus_list))}
        #'morphophonology_success': morphophonology_success,
        #'morphophonology_success_percent': 100 * morphophonology_success / float(n),

    def parse_corpus(self, parser, corpus, batch_size=0):
        """Parse all of the transcriptions in the locally saved corpus using the
        locally saved parser.

        """
        print 'in parse_corpus in researcher.py'
        corpus_list = cPickle.load(open(corpus['local_copy_path'], 'rb'))
        transcriptions = list(set([t for t, m, g, c in corpus_list]))
        log.info('About to parse all %s unique transcriptions in corpus "%s".' % (
            len(transcriptions), corpus['name']))
        start_time = time.time()
        parses = self.parse_locally(parser, transcriptions, batch_size)
        end_time = time.time()
        log.info('Time elapsed: %s' % self.old.human_readable_seconds(end_time - start_time))
        return parses, corpus_list

    def evaluate_parser_against_corpora(self, parser, corpora, **kwargs):
        """Use ``parser`` to parse all corpora in the ``corpora`` dict, save
        unparsed words to disk, save phonology failures to disk, and print a
        summary of the parser's success on each corpus.

        :param object parser: parser object.
        :param dict corpora: keys are corpus names and values are corpus metadata.
        :returns: a list of dicts summarizing the parse results on each corpus.

        """

        test_phonology = kwargs.get('test_phonology', True)
        get_phonology_success = kwargs.get('get_phonology_success', False)
        batch_size = kwargs.get('batch_size', 0)
        force_recreate = kwargs.get('force_recreate', False)
        vocal = kwargs.get('vocal', False)

        # E.g., self.record['parse_summaries'][48][273] is a summary of the success of parser 48 on corpus 273
        key = 'parse_summaries'
        record = self.record.get(key, {}).get(parser['id'], {})

        parse_summaries = []
        for corpus_name in sorted(corpora.keys()):

            corpus = corpora[corpus_name]

            if record.get(corpus['id']) and not force_recreate:
                parse_summaries.append(record[corpus['id']])
                continue

            # Parse the corpus of words
            parses, corpus_list = self.parse_corpus(parser, corpus, batch_size)
            corpus_dict = dict((self.clean_transcription(t), [b, g, c]) for t, b, g, c in corpus_list)

            # Here we do stuff to try to figure out what's going wrong with the parser.

            # Get the morpheme and category sequences of the words that could not be parsed;
            # also, save unparsed transcriptions to disk.
            # morpheme_sequences: a dict, keys are sequences of user-supplied morpheme shapes, values are the corresponding user-supplied transcriptions.
            # category_sequences: a set of sequences of categories and delimiters corresponding to the unparsed transcriptions.
            morpheme_sequences, category_sequences = self.inspect_parses(
                parser, parses, corpus_dict, corpus['id'])

            # ``evaluation`` is a dict holding stats about the success of the parser on the corpus
            parser_object = self.get_parse_module(parser).parser
            evaluation = self.evaluate_parse(parses, corpus_dict, parser_object, vocal=vocal)

            if test_phonology:
                # Map morpheme sequences to phonologizations, i.e., transcriptions.
                # WARNING: where phonologies take gloss and category information into account, this will fail ...
                phonologizations = self.phonologize_locally(parser, morpheme_sequences.keys())

                # Write phonological failures to disk.
                self.save_phonological_failures(parser, phonologizations, morpheme_sequences, corpus['id'])

            if get_phonology_success:
                phonology_success = self.get_phonology_success(parser, corpus_list)
                evaluation.update(phonology_success)

            name_list = corpus_name.split()
            type_ = (('well' in name_list and 'well') or
                     ('analyzed' in name_list and 'analyzed') or
                     'words')
            relation, entity = (
                ('elicitor' in name_list and ('elicitor', name_list[name_list.index('elicitor') + 3])) or
                ('enterer' in name_list and ('enterer', name_list[name_list.index('enterer') + 3])) or
                ('dialect' in name_list and ('dialect', name_list[name_list.index('dialect') + 2])) or
                ('speaker' in name_list and ('speaker', name_list[name_list.index('speaker') + 3])) or
                ('id' in name_list and ('source', str(name_list[name_list.index('id') + 2]))) or
                ('source' in name_list and ('source', name_list[name_list.index('source') + 4])) or
                ('all', ''))
            evaluation.update({
                'type': type_,
                'relation': relation,
                'entity': entity,
                'id': corpus['id']
            })
            parse_summaries.append(evaluation)
            record[corpus['id']] = evaluation
            # relation, (attribute, value) in relations.items():

        # Cache and return the summaries
        self.record[key] = {}
        self.record[key][parser['id']] = record
        self.dump_record()
        return parse_summaries

    def format_parse_summary(self, parse_summary):
        """Return a parse summary as a string.

        """
        return u'%-24s %-30s %-20s %0.2f%s' % (
            parse_summary['type'],
            u'%s %s (#%s)' % (parse_summary['relation'], parse_summary['entity'], parse_summary['id']),
            u'%s/%s' % (parse_summary['parsed_count'], parse_summary['attempted_count']),
            parse_summary['parsed_percent'],
            chr(37))


    def run_phonology_tests(self, phonology, condition=False):
        response = self.old.get('phonologies/%s/runtests' % phonology['id'])
        successful = 0
        unsuccessful = []
        for morpheme_sequence in sorted(response.keys()):
            results = response[morpheme_sequence]
            expected = results['expected']
            actual = results['actual']
            success = set(expected) & set(actual) != set()
            test_count = len(response)
            if success:
                successful += 1
            else:
                unsuccessful.append(morpheme_sequence)
                if not condition or condition(morpheme_sequence):
                    log.info('%s\n\texpected: %s\n\tactual:   %s' % (morpheme_sequence,
                        u', '.join(expected), u', '.join(actual)))
        log.info('%s / %s (%0.2f) success rate' % (successful, test_count, 100.0 * successful / test_count))
        return unsuccessful, test_count

    def get_categories(self):
        """Return a dict from category names to dict representations of the categories.

        """

        categories = self.old.get('syntacticcategories')
        return dict((c['name'], c) for c in categories)


================================================================================
  OLD Parser Research
================================================================================

The OLD Parser Research library contains utilities and examples to help with
performing research involving the morphological parser functionality of a live
OLD application.


Using ``oldclient.py``
================================================================================

Probably the most useful general-purpose script is ``oldclient.py`` which is a
thin OLD-specific wrapper around the Python Requests library. This module
facilitates HTTP-based interaction with a live OLD web service. Assuming that
you have an OLD web service (https://github.com/jrwdunham/old) being served at
127.0.0.1 on port 5000, an example of usage of ``oldclient.py`` is as follows::

    >>> import oldclient
    >>> old = oldclient.OLDClient('127.0.0.1', '5000')
    >>> old.login('yourusername', 'yourpassword') # True
    >>> forms = old.get('forms') # `forms` is a list of dicts
    >>> forms[0]['transcription'] # u'transcription value'


Example foma phonology scripts in `resources/`
================================================================================

The ``resources/`` directory contains example phonology scripts written in the
regular expression rewrite rule formalism accepted by FST programs like foma
and XFST. Example usage is as follows::

    $ foma
    foma[0]: source resources/blackfoot_phonology_frantz91.script
    foma[0]: regex phonology ;
    foma[1]: down nit-ihpiyi # Returns nitsspiyi and nitsiihpiyi

See the foma page (https://code.google.com/p/foma/) for more details.


Other potentially useful files
================================================================================


researcher.py
--------------------------------------------------------------------------------

Module that defines the ``ParserResearcher`` class which represents an OLD
researcher which creates form searches, corpora, phonologies, morphologies, LMs,
and parsers, and which provides conveniences for storing representations of
these locally and for parsing and testing parsers.


blackfoot_research.py
--------------------------------------------------------------------------------

Executable that exemplifies using the functionality in ``researcher.py`` (and in
``oldclient.py``) in order to perform parser-based research on a specific
language via an OLD web service. While language-specific and rife with ad hoc
code, it may be useful as an example.


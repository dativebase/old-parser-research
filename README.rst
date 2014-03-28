================================================================================
  OLD Parser Research
================================================================================

The OLD Parser Research library contains utilities and examples to help with
performing research involving the morphological parser functionality of a live
OLD application.


Directory Structure
================================================================================


oldclient.py
--------------------------------------------------------------------------------

Module that defines the OLDClient class which encapsulates functionality for
connecting to and manipulating a live OLD web service.


researcher.py
--------------------------------------------------------------------------------

Module that defines the ParserResearcher class which represents an OLD
researcher which creates form searches, corpora, phonologies, morphologies, LMs,
and parsers, and which provides conveniences for storing representations of
these locally and for parsing and testing parsers.


blackfoot_research.py
--------------------------------------------------------------------------------

Executable that exemplifies using the functionality in ``researcher.py`` (and in
``oldclient.py`` in order to perform parser-based research on a specific language
via an OLD web service. While language-specific, it may be useful as an example.


record.pickle
--------------------------------------------------------------------------------

A pickled Python dict which holds a record of the research results garnered by
``research.py``. The name of this file can be configured in the executable.


localstore/
--------------------------------------------------------------------------------

A directory created by researcher instances which holds local copies of, and
data related to, resources requested from the OLD application.


resources/
--------------------------------------------------------------------------------

A directory for resources that are needed by the researcher object. For
example, a foma phonology script for a particular language or a copy of a
MySQL dump file of a language-specific OLD web service.


store/
--------------------------------------------------------------------------------

The directory created by a locally served OLD application to hold various
files, e.g., compiled foma scripts, generated and pickled LMs, etc.


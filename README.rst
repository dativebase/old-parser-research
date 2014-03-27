================================================================================
  OLD Parser Researcher
================================================================================

This directory contains code for performing research involving the morphological
parser functionality of a live OLD application.


Directory Structure
================================================================================

oldclient.py
--------------------------------------------------------------------------------

Library that defines the OLDClient class which encapsulates functionality for
connecting to and manipulating a live OLD web service.


researcher.py
--------------------------------------------------------------------------------

Module that defines the ParserResearcher class which represents an OLD 
researcher who creates form searches, corpora, phonologies, morphologies, LMs,
and parsers, and which provides conveniences for storing representations of these
locally and for parsing and testing parsers.



localstore
--------------------------------------------------------------------------------

A directory created by the researcher object in ``research.py`` which holds
local copies of, and data related to, resources requested from the OLD
application.


record.pickle
--------------------------------------------------------------------------------

A pickled Python dict which holds a record of the research results garnered by
``research.py``. The name of this file can be configured in the executable.


resources
--------------------------------------------------------------------------------

A directory for resources that are needed by the researcher object. For
example, a foma phonology script for Blackfoot, a copy of the MySQL dump file
of the db.


store
--------------------------------------------------------------------------------

The directory created by the OLD application to hold various files, e.g.,
compiled foma scripts, generated and pickled LMs, etc.




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 09:53:59 2019

@authors: dan.wendling@nih.gov

Last modified: 2019-11-11

** Search query analyzer, Part 2 **

This script: For items that were not matched, generate options to post to the
interface in 03.

THIS SCRIPT MUST BE RUN MANUALLY, ONE MODULE AT A TIME.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Generate spelling suggestion file using CSpell
(Consider a step that updates spellings before MetaMap)
3. Run MetaMapLite API

"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import pie, axis, show
import numpy as np
import requests
import json
import lxml.html as lh
from lxml.html import fromstring
import time
import os


# Set working directory, read/write locations
# CHANGE AS NEEDED
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')


#%%


#%%
# ==========================================================
# x. Add spelling suggestions from CSpell
# ==========================================================
'''
See wiki for installation, help, etc.: 
    https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki/3.-Installing-and-running-CSpell

No data yet on file size limits; 10,000 rows can be processed in around 12
minutes on a normal workstation, which uses these options:

cspell -I:cspell_infile.txt -si -o:cspell_result.txt

A 30,000-row file was processed in around 1 hour.

The order of the file is search frequency - probably the best order to use.
'''

"""

# You could limit by search frequency
# CSpell_infile = UnmatchedAfterJournals.loc[(UnmatchedAfterJournals['TotalSearchFreq'] >= 4)]
# If something is searched many times, it's probably not misspelled.

# You could limit by eyeballing the df; would be a way to select the part of the
# df most amenable to spelling corrections. 
# cspell_infile = UnmatchedAfterJournals.iloc[378:2800]
# cspell_infile = UnmatchedAfterJournals.iloc[2801:12800]
# cspell_infile = UnmatchedAfterJournals.iloc[12800:12800]
cspell_infile = UnmatchedAfterJournals.iloc[12801:59397]

# reduce to one col
cspell_infile = cspell_infile[['AdjustedQueryTerm']]

# Write out
cspell_infile.to_csv(dataInterim + 'cspell_infile.txt', encoding='utf-8', index=False)



# ---------------------------------------
# NOW PROCESS THE FILE OUTSIDE OF PYTHON
# BEFORE RESUMING WITH THE BELOW.
# ---------------------------------------


cspellSuggestions = pd.read_csv(dataInterim + 'cspell_resultsFull.txt', sep='|') # , index_col=False, skiprows=7, 
cspellSuggestions.columns
'''
'AdjustedQueryTerm', 'adjusted query term'
'''

# Drop rows where input and output are the same
# https://stackoverflow.com/questions/43951558/remove-rows-that-two-columns-have-the-same-values-by-pandas
cspellSuggestions = cspellSuggestions[cspellSuggestions['AdjustedQueryTerm'] != cspellSuggestions['adjusted query term']]

# Prep destination column in log
cspellSuggestions.rename(columns={'adjusted query term': 'cspell'}, inplace=True)

# Join to full list
LogAfterSpellingSugg = pd.merge(LogAfterJournals, cspellSuggestions, how='left', left_on=['AdjustedQueryTerm'], right_on=['AdjustedQueryTerm'])
LogAfterSpellingSugg.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType', 'cspell'
'''

# Re-arrange for manual check
LogAfterSpellingSugg = LogAfterSpellingSugg[['Query', 'cspell', 'AdjustedQueryTerm', 'TotalSearchFreq', 'ui', 'PreferredTerm', 'SemanticType']]


# Write out
writer = pd.ExcelWriter(dataInterim + 'LogAfterSpellingSugg.xlsx')
LogAfterSpellingSugg.to_excel(writer,'LogAfterSpellingSugg', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()

"""


# ==================================================
# 2. Generate spelling suggestion file using CSpell
# ==================================================
'''
Install the Java application CSpell, "a distributable spell checker for consumer
language," from https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/index.html

Specifically, https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/download.html
'''

# TODO - Write code to run the Java jar file from within this script - automate.

'''
** RUN MANUALLY FROM COMMAND LINE **

Currently I am running this manually, using the following command in Terminal.
CSpell -i:unmatchedUniquesFromStep1.txt -si -o:csplell-out.txt

File is written to /Projects/semanticsearch/.
'''

CSColNames = ['sourceID', 'Suggestion']

CSResultsRaw = pd.read_csv('csplell-out.txt', sep = '|', names=CSColNames) # , skiprows=2
CSResultsRaw.columns


#%%
# ============================================
# 2. Start-up / What to put into place, where
# ============================================

MMColNames = ['sourceID', 'OutputType', 'Score', 'PreferredName', 'CUI', 'SemanticType', 
            'TriggerInfo', 'PositionalInfo', 'MeSHTreeCode']

# Skip 2 lines
MMResultsRaw = pd.read_csv('test/MmOutput.txt', sep = '|', names=MMColNames) # , skiprows=2
MMResultsRaw.columns


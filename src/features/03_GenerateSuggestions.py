#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 09:53:59 2019

@authors: dan.wendling@nih.gov

Last modified: 2019-11-18


** Search query analyzer, Part 3 **

This script: For items that were not matched, derive "ListToCheck," highest 
frequency unmatched, and generate options from MetaMap, CSpell and FuzzyWuzzy.
Now that the safe bets have been taken out, let's allow more liberal guesses 
and resolve some tagging using human review.

THIS SCRIPT MUST BE RUN MANUALLY.

Consider how much work will benefit you. Solving 75-80% of your total search 
volume, might be the limit to what you can accomplish in a reasonable amount 
of time. Terms with multiple searches are more likely to be real things, such 
as terms from web site pages. Items searched only once or twice may not have 
enough information for classification. Real example: "halloween genetics". ??


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Build suggestions from MetaMap Lite API, suggestionsFromMM
3. Build suggestions from CSpell spelling checker, suggestionsFromCSpell
4. Build suggestions from FuzzyWuzzy, suggestionsFromFuzzyLoose
5. Unite all suggestions into one Excel file for manual work
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

import pandas as pd
import numpy as np
import os
# For MetaMap
import sys
import argparse
import requests # http://python-requests.org/
# For fuzzy matching
from fuzzywuzzy import fuzz, process

# Set working directory, read/write locations
# CHANGE AS NEEDED
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')

dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily

# Open file of unmatched terms
unmatchedTerms = pd.read_excel(dataInterim + 'UnmatchedAfterMetathesaurus.xlsx')
unmatchedTerms.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq'
'''

'''
Eyeball the df and determine the appropriate cutoff; focus on solving the most
frequently searched items THAT YOU HAVE TIME FOR. Terms searched more than 5 
times, the top 500 unresolved per month - something along those lines.
RECOMMENDATION: Start with the top 100 terms by frequency and run them all the
way through to updating the match files; see you can improve the earlier 
processing.
'''

# Pilot site, month analyzed: 1148 untagged terms were searched 5 times or more.
ListToCheck = unmatchedTerms.iloc[0:1148].reset_index()
# ListToCheck = unmatchedTerms.loc[(unmatchedTerms['TotalSearchFreq'] >= 5)].reset_index()
ListToCheck = ListToCheck.rename(columns={'index': 'tempID'})
ListToCheck.drop(['TotalSearchFreq'], axis=1, inplace=True)

# Send to file
ListToCheck.to_csv(r'data/interim/SuggestionsNeeded.txt', header=False, index=False, sep='|')


#%%
# ===============================================================
# 2. Build suggestions from MetaMap Lite API, suggestionsFromMM
# ===============================================================
'''
The version of this for license holders may be better, but requires a 
license agrement and local installation. The code below is for an https-only 
API. (Switch later if you need an extra boost.)

RECOMMENDATION: To see what MetaMapLite is doing, go to 
https://ii-public1.nlm.nih.gov/metamaplite/rest and run a search for smallpox. 
The result will be:
    
C0037354: smallpox: Smallpox : [dsyn]: [LCH, NCI_NICHD, MTH, CHV, CSP, MSH, MEDLINEPLUS, LCH_NW, NCI, ICD9CM, NDFRT, DXP]: 0 : 8 : 0.0
C0037355: smallpox: Smallpox Vaccine : [imft, phsu]: [MTH, LCH, CHV, CSP, MSH, LCH_NW, RXNORM, NDFRT, HL7V2.5, HL7V3.0, VANDF]: 0 : 8 : 0.0
C0037356: smallpox: Smallpox Viruses : [virs]: [MTH, CHV, LNC, NCI_CDISC, CSP, MSH, NCI, NCBI]: 0 : 8 : 0.0

If the best match for a search term is the vaccine entry, what's important to 
you will be:
    C0037355 - the CUI
    Smallpox Vaccine - the Preferred term
    [imft, phsu] - the Semantic Type abbreviations

In this example, you have classified your term as both Immunologic Factor (imft) 
and Pharmacologic Substance (phsu).

The MetaMap home page is https://metamap.nlm.nih.gov

The most important change from NLM's MetaMap script is this line, which allows
you to link dataframe terms with MetaMap output (sldiwi):
    '--docformat', default='sldiwi',
'''


# -----------------------------------
# PROCESS THE FILE OUTSIDE OF PYTHON
# -----------------------------------

'''
Go to the terminal / command line and run mmlrestclient.py, like this:

cd ~/Projects/classifysearches/data/interim

python mmlrestclient.py https://ii-public1.nlm.nih.gov/metamaplite/rest/annotate SuggestionsNeeded.txt --output mm_outfile.txt
'''


# ------------------------------------
# Merge source and result into one df
# ------------------------------------

'''
89|MMI|0.46|Calliphoridae|C0322495|[euka]|"blowfly"-text-0-"blowfly"-NN-0|0/7|
C0037354: smallpox: Smallpox : [dsyn]: [LCH, NCI_NICHD, MTH, CHV, CSP, MSH, MEDLINEPLUS, LCH_NW, NCI, ICD9CM, NDFRT, DXP]: 0 : 8 : 0.0

Described at https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki/4.-Understanding-MetaMap-output
'''

colList = ['tempID', 'Score', 'PreferredName', 'CUI', 'SemTypeList']
mmOutput = pd.read_csv(dataInterim + 'mm_outfile.txt', sep='|', usecols=[0,2,3,4,5], names=colList)

# Join
suggestionsFromMM = pd.merge(ListToCheck, mmOutput, how='left', on=['tempID'])
suggestionsFromMM.columns
'''
'tempID', 'AdjustedQueryTerm', 'Score', 'PreferredName', 'CUI',
       'SemTypeList'
'''

# Drop
suggestionsFromMM.drop(['tempID'], axis=1, inplace=True)

# Add source info
suggestionsFromMM['Source'] = 'MetaMap'


#%%
# =========================================================================
# 3. Build suggestions from CSpell spelling checker, suggestionsFromCSpell
# =========================================================================
'''
See wiki for installation, help, etc.: 
    https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki/3.-Installing-and-running-CSpell

Install the Java application CSpell, "a distributable spell checker for consumer
language," from https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/index.html

Specifically, https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/download.html
No data yet on file size limits; 10,000 rows can be processed in around 12
minutes on a normal workstation, which uses these options:

cspell -I:cspell_infile.txt -si -o:cspell_result.txt

A 30,000-row file was processed in around 1 hour. RECOMMENDATION: Limit size 
to what fits into your available work time. Here we use the same highest-freq
unmatched terms, as above.

# reduce to one col
cspell_infile = ListToCheck[['AdjustedQueryTerm']]

# Write out
cspell_infile.to_csv(dataInterim + 'cspell_infile.txt', encoding='utf-8', index=False)
'''


# ---------------------------------------
# NOW PROCESS THE FILE OUTSIDE OF PYTHON
# ---------------------------------------
'''
Run from terminal command line; location similar to:
    
cd C:\tools\cSpell2018\bin

cspell -i:SuggestionsNeeded.txt -si -o:cspell_result.txt
'''


# ------------------------------------
# Merge source and result into one df
# ------------------------------------

suggestionsFromCSpell = pd.read_csv(dataInterim + 'cspell_resultsFull.txt', sep='|') # , index_col=False, skiprows=7, 
suggestionsFromCSpell.columns
'''
'AdjustedQueryTerm', 'adjusted query term'
'''

# Drop rows where input and output are the same
# https://stackoverflow.com/questions/43951558/remove-rows-that-two-columns-have-the-same-values-by-pandas
suggestionsFromCSpell = suggestionsFromCSpell[suggestionsFromCSpell['AdjustedQueryTerm'] != suggestionsFromCSpell['adjusted query term']]

# Prep destination column in log
suggestionsFromCSpell.rename(columns={'adjusted query term': 'cspell'}, inplace=True)

# Join to full list
suggestionsFromCSpell = pd.merge(suggestionsFromCSpell, ListToCheck, how='inner', on='AdjustedQueryTerm')
suggestionsFromCSpell.columns
'''
'tempID', 'AdjustedQueryTerm', 'cspell'
'''

# Drop dupes
suggestionsFromCSpell = suggestionsFromCSpell.drop_duplicates(subset=['AdjustedQueryTerm'], keep='last')

# Drop
suggestionsFromCSpell.drop(['tempID'], axis=1, inplace=True)

# Add source info
suggestionsFromCSpell['Source'] = 'CSpell'


#%%
# ====================================================================
# 3. Build suggestions from fuzzy matching, suggestionsFromFuzzyLoose
# ====================================================================
'''
Over time you can change the parameters to match your time and desired level
of effort. You can reduce the list, change the type of match (full phrase or 
any word), and change the score, to change the number of candidates to 
match how much time you want to spend making manual assignments. 

When starting with a new site you should probably spend a good deal of time 
here, to make connections the other steps can't make. Decisions you make 
here will provide training data that the machine learning component can use.

Some configuration options are described at 
https://www.neudesic.com/blog/fuzzywuzzy-using-python/.
See for example fuzz.ratio (conservative) vs. fuzz.partial_ratio (medium) vs.
fuzz.token_set_ratio (any single word in the phrases, very liberal). The more
liberal you get here, the more you will see multiple-concept searches, which
you don't need to see at this point. This is not a good time to solve those.

5,000 in ~25 minutes; ~10,000 in ~50 minutes (at score_cutoff=85)

Python's FuzzyWuzzy was written for single inputs to a web form; here, however, 
we use it to compare one dataframe column to another dataframe's column. 
Takes extra lines of code to match the tokenized function output back 
to the original untokenized term, which is necessary for this work.

# Quick test, if you want - punctuation difference
fuzz.ratio('Testing FuzzyWuzzy', 'Testing FuzzyWuzzy!!')

FuzzyWuzzyResults - What the results of this function mean:
('hippocratic oath', 100, 2987)
('Best match string from dataset_2' (PastMatches), 'Score of best match', 'Index of best match string in PastMatches')

Re-start:
uniqueUnassignedAfterStep2 = pd.read_excel(dataInterim + 'uniqueUnassignedAfterStep2.xlsx')
'''


# Bring in and combine existing match files: SiteSpecificMatches, PastMatches


# Match to our unmatched list, ListToCheck



def fuzzy_match(x, choices, scorer, cutoff):
    return process.extractOne(
        x, choices=choices, scorer=scorer, score_cutoff=cutoff
    )

# Create series FuzzyWuzzyResults
FuzzyWuzzyProcResult1 = fuzzySourceZ.loc[:, 'AdjustedQueryTerm'].apply(
        fuzzy_match,
    args=( PastMatches.loc[:, 'AdjustedQueryTerm'],
            fuzz.ratio,
            75 # Items must have this score or higher to appear in the results
        )
)


# Convert FuzzyWuzzyResults Series to df
FuzzyWuzzyProcResult2 = pd.DataFrame(FuzzyWuzzyProcResult1)

# Move Index (IDs) into 'FuzzyIndex' col because Index values will be discarded
FuzzyWuzzyProcResult2 = FuzzyWuzzyProcResult2.reset_index()
FuzzyWuzzyProcResult2 = FuzzyWuzzyProcResult2.rename(columns={'index': 'FuzzyIndex'})

# Remove nulls
FuzzyWuzzyProcResult2 = FuzzyWuzzyProcResult2[FuzzyWuzzyProcResult2.AdjustedQueryTerm.notnull() == True] # remove nulls

# Move tuple output into 3 cols
FuzzyWuzzyProcResult2[['ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex']] = FuzzyWuzzyProcResult2['AdjustedQueryTerm'].apply(pd.Series)
FuzzyWuzzyProcResult2.drop(['AdjustedQueryTerm'], axis=1, inplace=True) # drop tuples

# Merge result to the orig source list cols
FuzzyWuzzyProcResult3 = pd.merge(FuzzyWuzzyProcResult2, fuzzySourceZ, how='left', left_index=True, right_index=True)
FuzzyWuzzyProcResult3.columns
# 'FuzzyIndex', 'GSPrefTerm', 'FuzzyScore', 'PastMatchesIndex', 'AdjustedQueryTerm', 'timesSearched'
       
# Change col order for browsability if you want to analyze this by itself
FuzzyWuzzyProcResult3 = FuzzyWuzzyProcResult3[['AdjustedQueryTerm', 'ProbablyMeantGSTerm', 'FuzzyScore', 'timesSearched', 'FuzzyIndex', 'PastMatchesIndex']]

# Merge result to PastMatches supplemental info
FuzzyWuzzyProcResult4 = pd.merge(FuzzyWuzzyProcResult3, PastMatches, how='left', left_on='ProbablyMeantGSTerm', right_on='AdjustedQueryTerm')
FuzzyWuzzyProcResult4.columns
'''
'AdjustedQueryTerm_x', 'ProbablyMeantGSTerm', 'FuzzyScore',
       'timesSearched', 'FuzzyIndex', 'PastMatchesIndex', 'SemanticType',
       'AdjustedQueryTerm_y', 'preferredTerm', 'ui'
'''

# Reduce and rename. AdjustedQueryTerm_y is now redundant; okay to drop
FuzzyWuzzyProcResult4 = FuzzyWuzzyProcResult4[['ui', 'AdjustedQueryTerm_x', 
                                               'preferredTerm', 'ProbablyMeantGSTerm', 
                                               'SemanticType', 'timesSearched', 
                                               'FuzzyScore']]
FuzzyWuzzyProcResult4 = FuzzyWuzzyProcResult4.rename(columns={'AdjustedQueryTerm_x': 'AdjustedQueryTerm',
                                                              'ProbablyMeantGSTerm': 'FuzzyToken'})





#%%
# =============================================================
# 5. Unite all suggestions into one Excel file for manual work
# =============================================================
'''

'''


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 09:53:59 2019

@authors: dan.wendling@nih.gov

Last modified: 2019-11-18

------------------------------------------------------
 ** Semantic Search Analysis: Generate suggestions **
------------------------------------------------------

This script: For items that were not matched, derive "ListToCheck" - the highest 
frequency unmatched terms, that you have time to work on, and then generate 
options from MetaMap Lite, CSpell and FuzzyWuzzy. Now that the safe bets have 
been tagged and removed from view, let's allow more liberal guessing and use 
human review to resolve SOME trickier tagging.

RECOMMENDATION: Run the processes for MetaMap and CSpell, put the output files
in place, then run this entire script at once.

Consider how much work will benefit you. Solving 75-80% of your total search 
volume, might be the limit to what you can accomplish in a reasonable amount 
of time. Terms with multiple requests are more likely to be real things, such 
as terms from web site pages. Items searched only once or twice may not have 
enough information for classification. Real examples: "halloween genetics"; 
"yoga nutrition". ??

INPUTS:
    - data/interim/UnmatchedAfterMetathesaurus.xlsx (or current file of unmatched)
    - data/interim/result_mm.txt
    - data/interim/result_cspell.txt
    - data/matchFiles/SemanticNetworkReference.xlsx

OUTPUTS:
    - data/interim/03_suggestions.xlsx
    

----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Build suggestions from MetaMap Lite API, suggestionsFromMM
3. Build suggestions from CSpell spelling checker, suggestionsFromCSpell
4. Build suggestions from FuzzyWuzzy, suggestionsFromFuzzyLoose
5. Unite all suggestions into one Excel file for manual work
6. Update multiple resources, re-run Phase 1, etc.
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

python mmlrestclient.py https://ii-public1.nlm.nih.gov/metamaplite/rest/annotate SuggestionsNeeded.txt --output result_mm.txt
'''


# ------------------------------------
# Merge source and result into one df
# ------------------------------------

'''
89|MMI|0.46|Calliphoridae|C0322495|[euka]|"blowfly"-text-0-"blowfly"-NN-0|0/7|
C0037354: smallpox: Smallpox : [dsyn]: [LCH, NCI_NICHD, MTH, CHV, CSP, MSH, MEDLINEPLUS, LCH_NW, NCI, ICD9CM, NDFRT, DXP]: 0 : 8 : 0.0

Described at https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki/4.-Understanding-MetaMap-output
'''

mmCols = ['tempID', 'Score', 'SuggestedTerm', 'CUI', 'SemTypeList']
result_mm = pd.read_csv(dataInterim + 'result_mm.txt', sep='|', usecols=[0,2,3,4,5], names=mmCols)

# Join
suggestionsFromMM = pd.merge(ListToCheck, result_mm, how='left', on=['tempID'])
suggestionsFromMM.columns
'''
'tempID', 'AdjustedQueryTerm', 'Score', 'SuggestedTerm', 'CUI',
       'SemTypeList'
'''

# Drop
suggestionsFromMM.drop(['tempID'], axis=1, inplace=True)
suggestionsFromMM = suggestionsFromMM.dropna(subset=['SuggestedTerm'])

# Add source col
suggestionsFromMM['Source'] = 'MetaMap'

# Make SemTypeList content look like SemanticNetworkReference.SemanticTypeAbr
suggestionsFromMM['SemTypeList'] = suggestionsFromMM['SemTypeList'].str.replace(', ', '|')
suggestionsFromMM['SemTypeList'] = suggestionsFromMM['SemTypeList'].str.replace('\[', '')
suggestionsFromMM['SemTypeList'] = suggestionsFromMM['SemTypeList'].str.replace('\]', '')

# Bring in Sem Type info
SemTypes = pd.read_excel(dataMatchFiles + 'SemanticNetworkReference.xlsx')
# Reduce to join cols
SemTypes = SemTypes[['SemanticTypeAbr', 'SemanticType']]
# dropna
SemTypes = SemTypes.dropna(subset=['SemanticTypeAbr'])

# Join
suggestionsFromMM2 = pd.merge(suggestionsFromMM, SemTypes, how='left', left_on='SemTypeList', right_on='SemanticTypeAbr')
suggestionsFromMM2.columns
'''
'AdjustedQueryTerm', 'Score', 'SuggestedTerm', 'CUI', 'SemTypeList',
       'Source', 'SemanticTypeAbr', 'SemanticType'
'''

# Some combo types are not in SemanticNetworkReference
# Pull out nulls
fixSem = suggestionsFromMM2[suggestionsFromMM2['SemanticType'].isnull()]
# Dupe off col
fixSem['SemanticType'] = fixSem['SemTypeList']

# Move abbreviation into index
SemTypes.set_index('SemanticTypeAbr', inplace=True)

# Find and replace within fixSem using SemTypes df
for key, value in SemTypes.iterrows():
    currKey = key
    currST = value['SemanticType']
    fixSem['SemanticType'] = fixSem['SemanticType'].str.replace(currKey, currST)
  
#  drop na from main df
suggestionsFromMM2 = suggestionsFromMM2.dropna(subset=['SemanticType'])

# append the new content
suggestionsFromMM2 = suggestionsFromMM2.append([fixSem])

# drop abbrev cols
suggestionsFromMM2.drop(['SemanticTypeAbr', 'SemTypeList'], axis=1, inplace=True)
suggestionsFromMM2 = suggestionsFromMM2.reset_index(drop=True)


del [[result_mm, suggestionsFromMM, fixSem]]


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

cspell -I:cspell_infile.txt -si -o:result_cspell.txt

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

cspell -i:SuggestionsNeeded.txt -si -o:result_cspell.txt
'''


# ------------------------------------
# Merge source and result into one df
# ------------------------------------

cspellCols = ['AdjustedQueryTerm', 'SuggestedTerm']
result_cspell = pd.read_csv(dataInterim + 'result_cspell.txt', sep='|', index_col=False, usecols=[1,3], names=cspellCols)  # skiprows=7, 
result_cspell.columns
'''
'AdjustedQueryTerm', 'SuggestedTerm'
'''

# Drop rows where input and output are the same
# https://stackoverflow.com/questions/43951558/remove-rows-that-two-columns-have-the-same-values-by-pandas
suggestionsFromCSpell = result_cspell[result_cspell['AdjustedQueryTerm'] != result_cspell['SuggestedTerm']]

# Add source col
suggestionsFromCSpell['Source'] = 'CSpell'

del [[result_cspell]]


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

# -----
# Prep
# -----

# Bring in
SiteSpecificMatches = pd.read_excel(dataMatchFiles + 'SiteSpecificMatches.xlsx')
SiteSpecificMatches.columns
'''
'AdjustedQueryTerm', 'PreferredTerm', 'SemanticType'
'''

# Bring in
PastMatches = pd.read_excel(dataMatchFiles + 'PastMatches.xlsx')
PastMatches.columns
'''
'SemanticType', 'AdjustedQueryTerm', 'PreferredTerm', 'ui'
'''

# Append
TermsInUseFull = SiteSpecificMatches.append([PastMatches])

# Reduce
TermsInUseList = TermsInUseFull[['AdjustedQueryTerm']]

# Dedupe
TermsInUseList = TermsInUseList.drop_duplicates(subset=['AdjustedQueryTerm'], keep='first')    

del [[SiteSpecificMatches, PastMatches]] # free memory


# ------------------------------------
# Fuzzy match using fuzz.ratio
# ------------------------------------

# Compare ListToCheck to TermsInUseList
def fuzzy_match(x, choices, scorer, cutoff):
    return process.extractOne(
        x, choices=choices, scorer=scorer, score_cutoff=cutoff
    )

# Create series FuzzyWuzzyResults
FuzzyWuzzyProcResult1 = ListToCheck.loc[:, 'AdjustedQueryTerm'].apply(
        fuzzy_match,
    args=( TermsInUseList.loc[:, 'AdjustedQueryTerm'],
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
FuzzyWuzzyProcResult2[['SuggestedTerm', 'Score', 'TermsInUseListIndex']] = FuzzyWuzzyProcResult2['AdjustedQueryTerm'].apply(pd.Series)
FuzzyWuzzyProcResult2.drop(['AdjustedQueryTerm'], axis=1, inplace=True) # drop tuples

# Merge result to the orig source list cols
FuzzyWuzzyProcResult3 = pd.merge(FuzzyWuzzyProcResult2, ListToCheck, how='left', left_index=True, right_index=True)
FuzzyWuzzyProcResult3.columns
'''
'FuzzyIndex', 'SuggestedTerm', 'Score', 'TermsInUseListIndex',
       'tempID', 'AdjustedQueryTerm'
'''       

# Reduce/re-order
suggestionsFromFuzzyWuzzy = FuzzyWuzzyProcResult3[['AdjustedQueryTerm', 'SuggestedTerm', 'Score']]

# Add source info
suggestionsFromFuzzyWuzzy['Source'] = 'FuzzyWuzzy'


# In case the suggestion is correct, get PreferredTerm and Sem Type 
suggestionsFromFuzzyWuzzy2 = pd.merge(suggestionsFromFuzzyWuzzy, TermsInUseFull, how='left', left_on=['SuggestedTerm'], right_on='AdjustedQueryTerm')
suggestionsFromFuzzyWuzzy2.columns
'''
'AdjustedQueryTerm_x', 'SuggestedTerm', 'Score', 'Source',
       'AdjustedQueryTerm_y', 'PreferredTerm', 'SemanticType', 'ui'
'''

# drop _y and rename _x
suggestionsFromFuzzyWuzzy2.drop(['AdjustedQueryTerm_y'], axis=1, inplace=True)
suggestionsFromFuzzyWuzzy2.rename(columns={'AdjustedQueryTerm_x': 'AdjustedQueryTerm'}, inplace=True)

# del [[]]


#%%
# =============================================================
# 5. Unite all suggestions into one Excel file for manual work
# =============================================================
'''
Append into one table and prep for manual work.
'''

# Append into one df
suggestions = suggestionsFromMM2.append([suggestionsFromCSpell, suggestionsFromFuzzyWuzzy2])
suggestions.columns
'''
'AdjustedQueryTerm', 'CUI', 'Score', 'SemanticType', 'Source',
       'SuggestedTerm'
'''


# Add frequency from unmatchedTerms
unmatchedTerms = pd.read_excel(dataInterim + 'UnmatchedAfterMetathesaurus.xlsx')
unmatchedTerms.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq'
'''

# Join
suggestions2 = pd.merge(suggestions, unmatchedTerms, how='left', left_on=['AdjustedQueryTerm'], right_on='AdjustedQueryTerm')
suggestions2.columns
'''
'AdjustedQueryTerm', 'SuggestedTerm', 'SemanticType', 'CUI', 'Score',
       'Source', 'TotalSearchFreq'
'''

# Adjust
suggestions2 = suggestions2[['TotalSearchFreq', 'AdjustedQueryTerm', 'SuggestedTerm', 'SemanticType', 'CUI', 'Source', 'Score']]
suggestions2 = suggestions2.sort_values(by=['TotalSearchFreq', 'AdjustedQueryTerm', 'SemanticType'], ascending=[False,True,True])
suggestions2 = suggestions2.reset_index(drop=True)


del [[ListToCheck, SemTypes, suggestions, suggestionsFromCSpell, suggestionsFromFuzzyWuzzy, 
      suggestionsFromFuzzyWuzzy2, suggestionsFromMM2, unmatchedTerms]]
# SemanticNetworkReference, TermsInUse, 


#%%
# =============================================================
# 6. Update multiple resources, re-run Phase 1, etc.
# =============================================================
'''
Some terms should be added to the match files; do this work and re-run Phase 1.

For now we have to do this manually.

A wireframe for a suggestion-selector user interface is in the GitHub wiki.

Do what you have time for.
'''

# Write out
writer = pd.ExcelWriter(dataInterim + '03_suggestions.xlsx')
suggestions2.to_excel(writer,'Suggestions', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


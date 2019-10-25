#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 10:44:31 2018

@authors: dan.wendling@nih.gov, 

Last modified: 2019-10-16

** Site-search log file analyzer, Part 3 **

This script: Automatically update "high-confidence guesses," then use 
Django UI to build training data for machine learning, by making manual
selections for your higher-frequency queries.

Matches such as proper names, acronyms, and other "named entities" will 
not be in UMLS, but can be fed into the 01 files HighConfidenceGuesses.xlsx and 
QuirkyMatches.xlsx over time. This step helps the system get better over 
time; high-confidence corrections are automatic, but should
be checked occasionally, and lower-confidence matches need to be manually
inspected; for the second, two Django pages and a sqlite database assist.

Python's FuzzyWuzzy was written for single inputs to a web form; here, however, 
we use it to compare one dataframe column to another dataframe's column. 
Takes extra lines of code to match the tokenized function output back 
to the original untokenized term, which is necessary for this work.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Create import file for manual matching UI - importManualAssignments
3. Add result to SQLite
4. Process results in browser using http://localhost:8000/MakeAssignments/
5. Update QuirkyMatches and log from manual_assignments table
6. Create new 'uniques' dataframe from log
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
from fuzzywuzzy import fuzz, process

# Set working directory, read/write locations
# CHANGE AS NEEDED
os.chdir('/Users/name/Projects/webDS')
dataRaw = 'data/raw/search/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/search/' # Save to disk as desired, to re-start easily
dbDir = '_django/loganalysis/'

# Specific files you'll need. NOTE - Removes df if your first session is still active
uniqueUnassignedAfterStep2 = dataInterim + 'uniqueUnassignedAfterStep2.xlsx' # newest log
PastMatches = dataMatchFiles + 'PastMatches.xlsx' # historical file of vetted successful matches
logAfterStep2 = dataInterim + 'logAfterStep2.xlsx'

# Open the first files used
uniqueUnassignedAfterStep2 = pd.read_excel(dataInterim + 'uniqueUnassignedAfterStep2.xlsx')
PastMatches = pd.read_excel(PastMatches)


#%%
# =======================================================================
# 2. Create import file for manual matching UI - importManualAssignments
# =======================================================================
'''
Now that the safe bets have been taken out, let's allow more liberal matching
and finish some assignments using human review.

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

# Quick test, if you want - punctuation difference
fuzz.ratio('Testing FuzzyWuzzy', 'Testing FuzzyWuzzy!!')

FuzzyWuzzyResults - What the results of this function mean:
('hippocratic oath', 100, 2987)
('Best match string from dataset_2' (PastMatches), 'Score of best match', 'Index of best match string in PastMatches')

Re-start:
uniqueUnassignedAfterStep2 = pd.read_excel(dataInterim + 'uniqueUnassignedAfterStep2.xlsx')
'''

# This sets minimum appearances in log; helps assure we are starting with a "real" thing.
# There are many queries that are not discipherable, which appear only once and would waste time here.
fuzzySourceZ = uniqueUnassignedAfterStep2[uniqueUnassignedAfterStep2.timesSearched >= 3]

# fuzzySourceZ = listOfUniqueUnassignedAfterFuzzy1.iloc[0:900]

# Recommendation: Do a test
# fuzzySourceZ = listOfUniqueUnassignedAfterFuzzy1.iloc[0:25]

# 2018-07-08: Created FuzzyWuzzyProcResult1, 3,000 records, in 24 minutes
# 2018-07-09: 5,000 in 39 minutes
# 2018-07-09: 4,000 in 32 minutes

'''
The list is sorted so more-frequent searches are near the top. These are more
likely to be real things, such as terms from web site pages. Items searched
only once or twice may not have enough information for classification. 
Real examples: accident room; achieve; advertise purch;


'''

# fuzzySourceZ = listOfUniqueUnassignedAfterFuzzy1.iloc[0:500]

'''
Large datasets, you may want to break up...
fuzzySource1 = listOfUniqueUnassignedAfterFuzzy1.iloc[0:5000]
fuzzySource2 = listOfUniqueUnassignedAfterFuzzy1.iloc[5001:10678]
'''

def fuzzy_match(x, choices, scorer, cutoff):
    return process.extractOne(
        x, choices=choices, scorer=scorer, score_cutoff=cutoff
    )

# Create series FuzzyWuzzyResults
FuzzyWuzzyProcResult1 = fuzzySourceZ.loc[:, 'adjustedQueryTerm'].apply(
        fuzzy_match,
    args=( PastMatches.loc[:, 'adjustedQueryTerm'],
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
FuzzyWuzzyProcResult2 = FuzzyWuzzyProcResult2[FuzzyWuzzyProcResult2.adjustedQueryTerm.notnull() == True] # remove nulls

# Move tuple output into 3 cols
FuzzyWuzzyProcResult2[['ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex']] = FuzzyWuzzyProcResult2['adjustedQueryTerm'].apply(pd.Series)
FuzzyWuzzyProcResult2.drop(['adjustedQueryTerm'], axis=1, inplace=True) # drop tuples

# Merge result to the orig source list cols
FuzzyWuzzyProcResult3 = pd.merge(FuzzyWuzzyProcResult2, fuzzySourceZ, how='left', left_index=True, right_index=True)
FuzzyWuzzyProcResult3.columns
# 'FuzzyIndex', 'GSPrefTerm', 'FuzzyScore', 'PastMatchesIndex', 'adjustedQueryTerm', 'timesSearched'
       
# Change col order for browsability if you want to analyze this by itself
FuzzyWuzzyProcResult3 = FuzzyWuzzyProcResult3[['adjustedQueryTerm', 'ProbablyMeantGSTerm', 'FuzzyScore', 'timesSearched', 'FuzzyIndex', 'PastMatchesIndex']]

# Merge result to PastMatches supplemental info
FuzzyWuzzyProcResult4 = pd.merge(FuzzyWuzzyProcResult3, PastMatches, how='left', left_on='ProbablyMeantGSTerm', right_on='adjustedQueryTerm')
FuzzyWuzzyProcResult4.columns
'''
'adjustedQueryTerm_x', 'ProbablyMeantGSTerm', 'FuzzyScore',
       'timesSearched', 'FuzzyIndex', 'PastMatchesIndex', 'SemanticType',
       'adjustedQueryTerm_y', 'preferredTerm', 'ui'
'''

# Reduce and rename. adjustedQueryTerm_y is now redundant; okay to drop
FuzzyWuzzyProcResult4 = FuzzyWuzzyProcResult4[['ui', 'adjustedQueryTerm_x', 
                                               'preferredTerm', 'ProbablyMeantGSTerm', 
                                               'SemanticType', 'timesSearched', 
                                               'FuzzyScore']]
FuzzyWuzzyProcResult4 = FuzzyWuzzyProcResult4.rename(columns={'adjustedQueryTerm_x': 'adjustedQueryTerm',
                                                              'ProbablyMeantGSTerm': 'FuzzyToken'})


#%%

# ADD MACHINE LEARNING RUNS HERE, from 04
    
# Combine all predictions into one df

    


#%%

# Write to the folder containing sqlite database
writer = pd.ExcelWriter(dbDir + '04-TermPredictions.xlsx')
FuzzyWuzzyProcResult4.to_excel(writer,'manual')
# df2.to_excel(writer,'Sheet2')
writer.save()

# '_django/loganalysis/FuzzyWuzzyRawRecommendations.xlsx'

# Remove fuzzySource1, etc., FuzzyWuzzyProcResult1, etc.


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 09:20:01 2018

@authors: dan.wendling@nih.gov

Last modified: 2019-10-28

** Search query analyzer, Phase 1 **

This script: Import search queries from Google Analytics, clean up, 
match query entries against historical files. This is the only script of the 
set that can be run without human intervention. If desired.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Create dataframe from query log; globally update columns and rows
3. Exact-match to SUCCESSFUL and VETTED past matches

3. Direct match to gold standard file of previously successful matches
4. Clean up content to improve matching
5. Assign non-Roman characters to Foreign unresolved, match to umlsTermListForeign
6. Make special-case assignments with F&R, RegEx: Bibliographic, Numeric, Named entities
7. Do an exact match to umlsTermListEnglish

9. Apply matches from HighConfidenceGuesses.xlsx
10. Create new high-confidence guesses with FuzzyWuzzy
11. Apply matches from QuirkyMatches.xlsx
12. Create 'uniques' dataframe/file for APIs

12. If working with multiple processed logs at once


------------------
SEARCH QUERY DATA
------------------

To obtain data:
    1. Go to Google Analytics > Acquisition > Search Console > Queries
    2. Set date parameters (Consider starting small; you can scale up later)
    3. Select Export > Unsampled Report
    4. Copy the result to data/raw folder.
    
What you import should look like:
    
| Search Query     | Clicks | Impressions | CTR  | Average Position |
| hippocratic oath | 1037   | 19603       | 0.05 | 4.1              |


--------------------------
INPUT FILES YOU WILL NEED
--------------------------

logFileName: data/raw/GA-console-2019-09-1000.csv - Change to fit your export
data/matchFiles/PastMatches.csv - Historical file of vetted successful matches
data/matchFiles/HighConfidenceGuesses.csv - Automatically matched even though a few characters off
data/matchFiles/meshWithSemTypes.csv - Free-to-use controlled vocabulary - MeSH - with UMLS Semantic Types

Not used in this cut-down version of the project:
# QuirkyMatches = dataMatchFiles + 'QuirkyMatches.csv' # Human-chosen terms that might be misspelled, foreign, etc.
# umlsTermListForeign = dataMatchFiles + 'umlsTermListForeign.csv'
# umlsTermListEnglish = dataMatchFiles + 'umlsTermListEnglish.csv'


-------------------
OUTPUTS OF PHASE 1
-------------------

data/interim/logAfterPhase1.csv
data/interim/uniqueUnmatchedAfterPhase1.csv
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
File locations, etc.
'''

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import pie, axis, show
import matplotlib.ticker as mtick # used for example in 100-percent bars chart
import numpy as np
import os
import string
import requests
import json
import lxml.html as lh
from lxml.html import fromstring

# Set working directory and directories for read/write
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')

logFileName = 'GA-console-2019-09-1000.csv'


dataRaw = 'data/raw/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
reports = 'reports/'


#%%
# ======================================================================
# 2. Create dataframe from query log; globally update columns and rows
# ======================================================================
'''
If you need to concat multiple files, one option is
searchLog = pd.concat([x1, x2, x3], ignore_index=True)

File will have junk rows at top and bottom that this code removes.
'''

# Bring data in
searchLog = pd.read_csv(dataRaw + logFileName, 
                        sep=',', skiprows=6,
                        index_col=False) # thousands=',' did not work

searchLog.columns
'''
'Search Query', 'Clicks', 'Impressions', 'CTR', 'Average Position'
'''

# Rename cols
searchLog.rename(columns={'Search Query': 'SearchQuery', 
                          'Average Position': 'AveragePosition'}, inplace=True)

# Remove rows containing nulls - i.e., GA's summary rows at bottom
searchLog = searchLog.dropna()

# Remove the grand totals line at bottom
searchLog = searchLog[searchLog.SearchQuery.str.contains("Day Index") == False] # char entities

# Update Clicks and set term frequency
searchLog['Clicks'].replace({',': ''}, inplace=True, regex=True)
searchLog['Clicks'] = searchLog['Clicks'].astype(int)
# Frequency limit is not required but reduces your startup work - this group 
# will be easist to tag - if a term was searched this many times it must be a 
# 'real thing' and close to the real name. 
# Reduce the count over time as you improve PastMatches.csv
searchLog = searchLog[searchLog['Clicks'] >= 5]

# Dupe off Query column into lower-cased 'AdjustedQueryTerm', which will
# be the column to clean up and match against
searchLog['AdjustedQueryTerm'] = searchLog['SearchQuery'].str.lower()


#%%
# ======================================================================
# 3. Exact-match to SUCCESSFUL and VETTED past matches
# ======================================================================
'''
Build a file of terms your site visitors are most commonly searching for,
which might be handled poorly by the resources in Phase 2, to include:
    1. Your product and service names, as people search for them
    2. Person names, whether staff, authors, etc.
    3. Organizational names specific to your organization
    4. Any homonymns, etc., that you review after Phase 2 that you want to 
        control tagging for to PREVENT the Phase 2 tools from tagging.

Focus on queries that are correct as typed and can be extact-matched to terms
that Phase 2 might handle incorrectly. Over time this will lighten the manual 
work in later steps.

DO use correct spellings, because later we fuzzy match off of the terms here. 
Okay to add previously matched foreign terms here.

** TO BUILD A NEW FILE **
Export the top 1,000 queries from the past 12 months and 
cluster them using the code at x. Then process similar BRANDED PRODUCTS, etc.
(ONLY the categories above!) in a spreadsheet, building the additional column 
information as you go, following what's in the model PastMatches file.
'''


# ----------------
# PastMatches.csv
# ----------------

# Bring in file containing this site's historical matches
PastMatches = pd.read_csv(dataMatchFiles + 'PastMatches.csv', sep = ',') # , skiprows=2
PastMatches.columns
'''
'SemanticType', 'AdjustedQueryTerm', 'PreferredTerm', 'ui'
'''

# Not getting expected matches; is the col type mixed? Looks like from checking df
# logAfterUmlsTerms['AdjustedQueryTerm'] = logAfterUmlsTerms['AdjustedQueryTerm'].astype(str)

# First, focus on PreferredTerm in PastMatches. Success rate probably low, but a few.
logAfterPastMatches = pd.merge(searchLog, PastMatches, left_on=['AdjustedQueryTerm'], right_on=['PreferredTerm'], how='left')
logAfterPastMatches.columns
'''
'SearchQuery', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'AdjustedQueryTerm_x', 'AdjustedQueryTerm_y', 'PreferredTerm',
       'SemanticType', 'ui', 'Unnamed: 4', 'Unnamed: 5', 'Unnamed: 6'
'''

# AdjustedQueryTerm_y will not be needed; otherwise same update as above
logAfterPastMatches.drop(['AdjustedQueryTerm_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'AdjustedQueryTerm_x':'AdjustedQueryTerm'}, inplace=True)

# Reclaim text cols as strings
# logAfterPastMatches = logAfterPastMatches.astype({'AdjustedQueryTerm': str, 'ui': str, 'PreferredTerm': str, 'SemanticType': str})

# Second, focus on AdjustedQueryTerm in PastMatches; higher success rate.
logAfterPastMatches = pd.merge(logAfterPastMatches, PastMatches, how='left', left_on=['AdjustedQueryTerm'], right_on=['AdjustedQueryTerm'])
logAfterPastMatches.columns
'''
'SearchQuery', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'AdjustedQueryTerm', 'PreferredTerm_x', 'SemanticType_x', 'ui_x',
       'PreferredTerm_y', 'SemanticType_y', 'ui_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. 
# Temporary fix: Move _y into _x if _x is empty; or here: where _x has content, use _x, otherwise use _y
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_x'].where(logAfterPastMatches['ui_x'].notnull(), logAfterPastMatches['ui_y'])
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_y'].where(logAfterPastMatches['ui_y'].notnull(), logAfterPastMatches['ui_x'])
logAfterPastMatches['PreferredTerm2'] = logAfterPastMatches['PreferredTerm_x'].where(logAfterPastMatches['PreferredTerm_x'].notnull(), logAfterPastMatches['PreferredTerm_y'])
logAfterPastMatches['PreferredTerm2'] = logAfterPastMatches['PreferredTerm_y'].where(logAfterPastMatches['PreferredTerm_y'].notnull(), logAfterPastMatches['PreferredTerm_x'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_x'].where(logAfterPastMatches['SemanticType_x'].notnull(), logAfterPastMatches['SemanticType_y'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_y'].where(logAfterPastMatches['SemanticType_y'].notnull(), logAfterPastMatches['SemanticType_x'])

logAfterPastMatches.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)

    
# -------------------
# JournalMatches.csv
# -------------------
# TODO - Add later if needed
    

# -------------
# How we doin?
# -------------
rowCount = len(logAfterPastMatches)
TotUniqueEntries = logAfterPastMatches['AdjustedQueryTerm'].nunique()

Assigned = logAfterPastMatches['SemanticType'].count()
# Assigned = (logAfterPastMatches['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterPastMatches['SemanticType'].value_counts().head(15)))
print("\n\n=====================================================\n ** logAfterPastMatches stats - {} **\n=====================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))

    
# Remove from memory. PastMatches is used below, so leave that.
# del [[searchLog]]


#%%
# ========================================
# 3. Clean up content to improve matching
# ========================================
'''
NOTE: Be careful what you remove, because the data you're matching to, DOES
CONTAIN non-alpha-numeric characters such as %.

Future: Later there is discussion of the UMLS file, MRCONSO.RRF; get a list 
of non-alpha-numeric characters used, then decide which ones in visitor 
queries cause more trouble than they're worth. Faster but 
may damage your ability to match:
    searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.extract('(\w+)', expand = False)
'''


"""
TODO - Easier to edit:
    stuffToUpdate = [ 
        ('<AUTHORS>', '<AUTHORS><AUTHOR>'),
        ('</AUTHORS>', '</AUTHOR></AUTHORS>'),
        ('<KEYWORDS>', '<KEYWORDS><KEYWORD>'),
        ('</KEYWORDS>', '</KEYWORD></KEYWORDS>'),
        (' & ', ' and ')
        ]

for txtIn, txtOut in stuffToUpdate:
    nowAString = nowAString.replace(txtIn, txtOut)
    
But, could separate into removals and replaces...
"""



# Remove selected punctuation...
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('"', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("'", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("`", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('(', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace(')', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('.', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace(',', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('!', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('*', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('$', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('+', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('?', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('~', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('!', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('#', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace(':', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace(';', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('{', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('}', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('|', '')
# Remove control characters
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\^', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\[', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\]', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\<', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\>', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('\\', '')
# Remove high ascii etc.
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('•', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("“", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("”", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("‘", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("«", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("»", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("»", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("¿", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("®", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("™", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("¨", "")
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace("（", "(")

# searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('-', '')
# searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('%', '')

# First-character issues
# searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^[0-9]{4}") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^-") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^/") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^@") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^;") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^<") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^>") == False] # char entities

# If removing punct caused a preceding space, remove the space.
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^  ', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^ ', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^ ', '')

# Drop junk rows with entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.startswith("&#") == False] # char entities
searchLog = searchLog[searchLog.AdjustedQueryTerm.str.contains("^&[0-9]{4}") == False] # char entities
# Alternatively, could use searchLog = searchLog[(searchLog.AdjustedQueryTerm != '&#')

# Remove modified entries that are now dupes or blank entries
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('  ', ' ') # two spaces to one
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.strip() # remove leading and trailing spaces
searchLog = searchLog.loc[(searchLog['AdjustedQueryTerm'] != "")]


# Test - Does the following do anything, good or bad? Can't tell. Remove non-ASCII; https://www.quora.com/How-do-I-remove-non-ASCII-characters-e-g-%C3%90%C2%B1%C2%A7%E2%80%A2-%C2%B5%C2%B4%E2%80%A1%C5%BD%C2%AE%C2%BA%C3%8F%C6%92%C2%B6%C2%B9-from-texts-in-Panda%E2%80%99s-DataFrame-columns
# I think a previous operation converted these already, for example, &#1583;&#1608;&#1588;&#1606;
# def remove_non_ascii(Query):
#    return ''.join(i for i in Query if ord(i)<128)
# testingOnly = uniqueSearchTerms['Query'] = uniqueSearchTerms['Query'].apply(remove_non_ascii)
# Also https://stackoverflow.com/questions/20078816/replace-non-ascii-characters-with-a-single-space?rq=1



# Should investigate how this happens? Does one browser not remove "search" from input?
# Examples: search ketamine, searchmedline, searchcareers, searchtuberculosis
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^search ', '')
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^search', '')

# Is this one different than the above? Such as, pathology of the lung
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('^pathology of ', '')

# Space clean-up as needed
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.replace('  ', ' ') # two spaces to one
searchLog['AdjustedQueryTerm'] = searchLog['AdjustedQueryTerm'].str.strip() # remove leading and trailing spaces
searchLog = searchLog.loc[(searchLog['AdjustedQueryTerm'] != "")]

# searchLog.head()
searchLog.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'AdjustedQueryTerm', 'SemanticType', 'PreferredTerm'
'''


#%%
# ====================================================================================
# 5. Assign non-Roman characters to Foreign unresolved, match to umlsTermListForeign
# ====================================================================================
'''
The local UMLS files can process non-Roman languages (Chinese, Cyrillic, etc.),
but the API cannot. Flag these so later you can remove them from the API 
request lists; no point trying to match something unmatchable.

Don't change placement; this will wipe both PreferredTerm and SemanticType.
Future procedures can replace this content, which is fine.

FIXME - Some of these are not foreign; R&D how to avoid assigning as foreign;
start by seeing whether orig term had non-ascii characters. 

Mistaken assignments that are 1-4-word single-concept searches will be overwritten with 
the correct data. And a smaller number of other types will be reclaimed as well.
- valuation of fluorescence in situ hybridization as an ancillary tool to urine cytology in diagnosing urothelial carcinoma
- comparison of a light‐emitting diode with conventional light sources for providing phototherapy to jaundiced newborn infants
- crystal structure of ovalbumin
- diet exercise or diet with exercise 18–65 years old

2019-08: Matched UMLS to log at 141 unique terms of 2749, ~5% of foreign uniques.
'''

def checkForeign(row):
    # print(row)
    foreignYes = {'AdjustedQueryTerm':row.AdjustedQueryTerm, 'PreferredTerm':'Foreign unresolved', 'SemanticType':'Foreign unresolved'}
    foreignNo = {'AdjustedQueryTerm':row.AdjustedQueryTerm, 'PreferredTerm':'','SemanticType':''}
    try:
       row.AdjustedQueryTerm.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
       return pd.Series(foreignYes)
    else:
       # return row
       return pd.Series(foreignNo)
   
searchLog[['AdjustedQueryTerm', 'PreferredTerm','SemanticType']] = searchLog.apply(checkForeign, axis=1)

# ForeignCounts = searchLog['SemanticType'].value_counts()

# Attempt an exact match to UMLS foreign terms. Intentionally overwrites SemanticType == 'Foreign unresolved'

# Create list of log uniques where SemanticType = 'Foreign unresolved'
foreignAgainstUmls = searchLog.loc[searchLog['SemanticType'] == 'Foreign unresolved']
foreignAgainstUmls = foreignAgainstUmls.groupby('AdjustedQueryTerm').size()
foreignAgainstUmls = pd.DataFrame({'timesSearched':foreignAgainstUmls})
foreignAgainstUmls = foreignAgainstUmls.sort_values(by='timesSearched', ascending=False)
foreignAgainstUmls = foreignAgainstUmls.reset_index()

# Open ~1.7 million row file
umlsTermListForeign = pd.read_csv(umlsTermListForeign, sep='|')
umlsTermListForeign.columns
'''
'PreferredTerm', 'ui', 'SemanticType', 'wordCount'
'''

# Reduce to matches
foreignUmlsMatches = pd.merge(foreignAgainstUmls, umlsTermListForeign, how='inner', left_on=['AdjustedQueryTerm'], right_on=['PreferredTerm'])
foreignUmlsMatches.columns
'''
'AdjustedQueryTerm', 'timesSearched', 'PreferredTerm', 'ui',
       'SemanticType', 'wordCount'
'''

# Reduce cols
foreignUmlsMatches = foreignUmlsMatches[['AdjustedQueryTerm', 'PreferredTerm', 'ui', 'SemanticType']]

# Combine with searchLog
logAfterForeign = pd.merge(searchLog, foreignUmlsMatches, how='left', left_on=['AdjustedQueryTerm', 'PreferredTerm', 'SemanticType'], right_on=['AdjustedQueryTerm', 'PreferredTerm', 'SemanticType'])
logAfterForeign.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'AdjustedQueryTerm', 'SemanticType', 'PreferredTerm', 'ui'
'''

# searchLog
del [[searchLog, umlsTermListForeign, foreignAgainstUmls]]


#%%
# =========================================================================================
# 6. Make special-case assignments with F&R, RegEx: Bibliographic, Numeric, Named entities
# =========================================================================================
'''
Later procedures can't match the below very well, so match them here.
'''

'''
If you think one page is skewing results - an outlier, maybe you'll want special handling.

outlierCheck = logAfterForeign[logAfterForeign.Referrer.str.contains("/bsd/pmresources.html") == True]
outlierCheck = logAfterForeign['Query'].value_counts()
outlierCheck = pd.DataFrame({'Count':outlierCheck})
outlierCheck = outlierCheck.reset_index()
outlierCheck = outlierCheck.head(n=25)
outlierCheck['PercentShare'] = outlierCheck.Count / TotQueries * 100
print("\nTop searches with percent share\n{}".format(outlierCheck))

# You can make these a separate category with something like,
logAfterForeign.loc[logAfterForeign['Referrer'].str.contains('/bsd/pmresources.html'), 'PreferredTerm'] = 'pmresources.html'
'''


# --- Bibliographic Entity ---
# Assign ALL queries over x char to 'Bibliographic Entity' (often citations, search strategies, publication titles...)
logAfterForeign.loc[(logAfterForeign['AdjustedQueryTerm'].str.len() > 30), 'PreferredTerm'] = 'Bibliographic Entity'

# logAfterForeign.loc[(logAfterForeign['AdjustedQueryTerm'].str.len() > 25) & (~logAfterForeign['PreferredTerm'].str.contains('pmresources.html', na=False)), 'PreferredTerm'] = 'Bibliographic Entity'

# Search strategies might also be in the form "clinical trial" and "step 0"
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('[a-z]{3,}" and "[a-z]{3,}', na=False), 'PreferredTerm'] = 'Bibliographic Entity'

# Search strategies might also be in the form "clinical trial" and "step 0"
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('[a-z]{3,}" and "[a-z]{3,}', na=False), 'PreferredTerm'] = 'Bibliographic Entity'

# Queries about specific journal titles
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('^journal of', na=False), 'PreferredTerm'] = 'Bibliographic Entity'
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('^international journal of', na=False), 'PreferredTerm'] = 'Bibliographic Entity'

# Add SemanticType
logAfterForeign.loc[logAfterForeign['PreferredTerm'].str.contains('Bibliographic Entity', na=False), 'SemanticType'] = 'Bibliographic Entity' # 'Intellectual Product'


# --- Numeric ID ---
# Assign entries starting with 3 digits
# FIXME - Clarify and grab the below, PMID, ISSN, ISBN 0-8016-5253-7), etc.
# logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('^[0-9]{3,}', na=False), 'PreferredTerm'] = 'Numeric ID'
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('[0-9]{5,}', na=False), 'PreferredTerm'] = 'Numeric ID'
logAfterForeign.loc[logAfterForeign['AdjustedQueryTerm'].str.contains('[0-9]{4,}-[0-9]{4,}', na=False), 'PreferredTerm'] = 'Numeric ID'

# Add SemanticType
logAfterForeign.loc[logAfterForeign['PreferredTerm'].str.contains('Numeric ID', na=False), 'SemanticType'] = 'Numeric ID'


'''
# When experimenting it's useful to write out a cleaned up version; if you 
# do re-processing, you can skip a bunch of work.
writer = pd.ExcelWriter(dataInterim + 'logAfterForeign.xlsx')
logAfterForeign.to_excel(writer,'logAfterForeign')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

# -------------
# How we doin?
# -------------

rowCount = len(logAfterForeign)
TotUniqueEntries = logAfterForeign['AdjustedQueryTerm'].nunique()

Assigned = (logAfterForeign['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = (logAfterForeign['SemanticType'].values == '').sum() # .isnull().sum()
PercentAssigned = round(Assigned / TotUniqueEntries * 100)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterForeign['SemanticType'].value_counts().head(10)))
print("\n\n=================================================\n ** logAfterForeign stats - {} **\n=================================================\n\n{}% of rows unclassified / {}% classified\n{:,} unique queries in logAfterForeign;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), TotQueries, Unassigned, Assigned))


#%%
# ====================================================================
# 7. Do an exact match to umlsTermListEnglish
# ====================================================================
'''
Optional. Attempt local exact matching against 3.7-million-term UMLS file. 
Because of the license agreement this file will not be shared, but it is a 
combination of MRCONSO.RFF and MRSTY.RRF that is reduced to only the 
preferred "atom" for each concept (CUI) in the vocabulary, and each concept 
includes its semantic type assignment(s). Saves a lot of time with the API, 
but not necessary for the project.

Restart?
logAfterForeign = pd.read_excel('01_Import-transform_files/logAfterForeign.xlsx')
'''

# Reviewing from above
logAfterForeign.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'AdjustedQueryTerm', 'SemanticType', 'PreferredTerm', 'ui'
'''

# ~3.2 million rows. To see what this HUGE df contains
# ViewSomeUmlsTerms = umlsTermListEnglish[10000:10500]
umlsTermListEnglish = pd.read_csv(umlsTermListEnglish, sep='|') # , index_col=False
umlsTermListEnglish.drop('wordCount', axis=1, inplace=True)
umlsTermListEnglish.columns
'''
'PreferredTerm', 'ui', 'SemanticType'
'''

# Combine
logAfterUmlsTerms = pd.merge(logAfterForeign, umlsTermListEnglish, how='left', left_on=['AdjustedQueryTerm'], right_on=['PreferredTerm'])
logAfterUmlsTerms.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'AdjustedQueryTerm', 'SemanticType_x', 'PreferredTerm_x', 'ui_x',
       'PreferredTerm_y', 'ui_y', 'SemanticType_y'
'''

# numpy.where(condition[, x, y])
# logAfterUmlsTerms['SemanticType2'] = np.where(logAfterUmlsTerms.SemanticType_x.isna(), logAfterUmlsTerms.SemanticType_y, logAfterUmlsTerms.SemanticType_x)


# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterUmlsTerms['ui2'] = logAfterUmlsTerms['ui_x'].where(logAfterUmlsTerms['ui_x'].notnull(), logAfterUmlsTerms['ui_y'])
logAfterUmlsTerms['ui2'] = logAfterUmlsTerms['ui_y'].where(logAfterUmlsTerms['ui_y'].notnull(), logAfterUmlsTerms['ui_x'])
logAfterUmlsTerms['PreferredTerm2'] = logAfterUmlsTerms['PreferredTerm_x'].where(logAfterUmlsTerms['PreferredTerm_x'].notnull(), logAfterUmlsTerms['PreferredTerm_y'])
logAfterUmlsTerms['PreferredTerm2'] = logAfterUmlsTerms['PreferredTerm_y'].where(logAfterUmlsTerms['PreferredTerm_y'].notnull(), logAfterUmlsTerms['PreferredTerm_x'])
logAfterUmlsTerms['SemanticType2'] = logAfterUmlsTerms['SemanticType_x'].where(logAfterUmlsTerms['SemanticType_x'].notnull(), logAfterUmlsTerms['SemanticType_y'])
logAfterUmlsTerms['SemanticType2'] = logAfterUmlsTerms['SemanticType_y'].where(logAfterUmlsTerms['SemanticType_y'].notnull(), logAfterUmlsTerms['SemanticType_x'])
logAfterUmlsTerms.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y', 'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterUmlsTerms.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)
    
    
'''
# Adjust cols
logAfterUmlsTerms.drop(['ui_x', 'PreferredTerm_y'], axis=1, inplace=True)
logAfterUmlsTerms.rename(columns={'PreferredTerm_x':'PreferredTerm'}, inplace=True)

# Attempting to remove all traces of 3.6-million-row df from memory, and logAfterForeign
# is no longer needed. Assuming this is correct:
# https://stackoverflow.com/questions/32247643/how-to-delete-multiple-pandas-python-dataframes-from-memory-to-save-ram
'''

del [[foreignUmlsMatches, logAfterForeign, umlsTermListEnglish, TermReport]]

'''
# Write out the work so far
writer = pd.ExcelWriter(dataInterim + 'logAfterUmlsTerms.xlsx')
logAfterUmlsTerms.to_excel(writer,'logAfterUmlsTerms')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

# -------------
# How we doin?
# -------------
rowCount = len(logAfterUmlsTerms)
TotUniqueEntries = logAfterUmlsTerms['AdjustedQueryTerm'].nunique()

Assigned = (logAfterUmlsTerms['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterUmlsTerms['SemanticType'].value_counts().head(10)))
print("\n\n=====================================================\n ** umlsTermListEnglish stats - {} **\n=====================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


# -----------------
# Visualize results
# -----------------
'''
# Interesting to run but may disrupt auto-run

# Pie for percentage of rows assigned
Assigned = (logAfterUmlsTerms['PreferredTerm'].values != '').sum()
Unassigned = (logAfterUmlsTerms['PreferredTerm'].values == '').sum()
labels = ['Assigned', 'Unassigned']
sizes = [Assigned, Unassigned]
colors = ['steelblue', '#fc8d59'] # more intense-#FF7F0E; lightcoral #FF9966
explode = (0.1, 0)  # explode 1st slice
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'UmlsTerms' processing - \n{:,} queries with {:,} unassigned".format(TotUniqueEntries, Unassigned))
plt.show()


# Bar of SemanticType categories, horizontal
# 
ax = logAfterUmlsTerms['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(8,6),
                                                 color="steelblue", fontsize=10); # slateblue
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'UmlsTerms' \nprocessing with {:,} of {:,} unassigned".format(Unassigned, TotUniqueEntries), fontsize=14)
ax.set_xlabel("Number of searches", fontsize=9);
ax.set_ylabel("Number of searches", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.31, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.5)
'''


#%%
# =================================================
# 8. Apply matches from HighConfidenceGuesses.xlsx
# =================================================
'''
This data comes from fuzzy matching later on; some of these can be sketchy,
so they are separated from "gold standard" matches. Entries here can be 
proper names, misspellings, foreign terms, that Python FuzzyWuzzy scored at 
90% or higher - just a few characters off from what the UMLS is able to 
match to, or what can be read from the web site spidering that made it into 
the PastMatches. You should edit this file a bit more frequently than you 
edit the PastMatches file; these are automatically assigned.
'''

# Bring in historical file of lightly edited matches
HighConfidenceGuesses = dataMatchFiles + 'HighConfidenceGuesses.xlsx' # Automatically matched even though a few characters off
HighConfidenceGuesses = pd.read_excel(HighConfidenceGuesses)

# FIXME - Update in file
HighConfidenceGuesses.rename(columns={'SemanticTypeName': 'SemanticType'}, inplace=True)
    

logAfterHCGuesses = pd.merge(logAfterPastMatches, HighConfidenceGuesses, left_on='AdjustedQueryTerm', right_on='AdjustedQueryTerm', how='left')
logAfterHCGuesses.columns
'''
'Unnamed: 0_x', 'Referrer', 'Query', 'Date', 'SessionID',
       'CountForPgDate', 'AdjustedQueryTerm', 'Unnamed: 0_y', 'ui_x',
       'PreferredTerm_x', 'SemanticType_x', 'Unnamed: 0',
       'ProbablyMeantGSTerm', 'SemanticType_y', 'PreferredTerm_y', 'ui_y'
'''

# FIXME - Set Excel to stop exporting and import index col
# logAfterHCGuesses.drop(['Unnamed: 0_x', 'Unnamed: 0_y', 'Unnamed: 0'], axis=1, inplace=True)

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterHCGuesses['ui2'] = logAfterHCGuesses['ui_x'].where(logAfterHCGuesses['ui_x'].notnull(), logAfterHCGuesses['ui_y'])
logAfterHCGuesses['ui2'] = logAfterHCGuesses['ui_y'].where(logAfterHCGuesses['ui_y'].notnull(), logAfterHCGuesses['ui_x'])
logAfterHCGuesses['PreferredTerm2'] = logAfterHCGuesses['PreferredTerm_x'].where(logAfterHCGuesses['PreferredTerm_x'].notnull(), logAfterHCGuesses['PreferredTerm_y'])
logAfterHCGuesses['PreferredTerm2'] = logAfterHCGuesses['PreferredTerm_y'].where(logAfterHCGuesses['PreferredTerm_y'].notnull(), logAfterHCGuesses['PreferredTerm_x'])
logAfterHCGuesses['SemanticType2'] = logAfterHCGuesses['SemanticType_x'].where(logAfterHCGuesses['SemanticType_x'].notnull(), logAfterHCGuesses['SemanticType_y'])
logAfterHCGuesses['SemanticType2'] = logAfterHCGuesses['SemanticType_y'].where(logAfterHCGuesses['SemanticType_y'].notnull(), logAfterHCGuesses['SemanticType_x'])
logAfterHCGuesses.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterHCGuesses.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)


# -------------
# How we doin?
# -------------
rowCount = len(logAfterHCGuesses)
TotUniqueEntries = logAfterHCGuesses['AdjustedQueryTerm'].nunique()

# Assigned = logAfterHCGuesses['SemanticType'].count()
Assigned = (logAfterHCGuesses['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterHCGuesses['SemanticType'].value_counts().head(10)))
print("\n\n===================================================\n ** logAfterHCGuesses stats - {} **\n===================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


# Remove from memory. HighConfidenceGuesses will be used below so don't remove here
del [[logAfterUmlsTerms, logAfterPastMatches]]



#%%
# ======================================================
# 9. Create new high-confidence guesses with FuzzyWuzzy
# ======================================================
'''
FuzzyAutoAdd - When phrase-match score is 90 or higher, assign without 
manual checking. By using past successful matches as the basis, we pull in
the vocabulary used by our audiences, product/service names, organizational
names, etc., with slight variations, AND as a tiny subset of the UMLS corpus,
this can be run quickly.

Isolate terms that might be a minor misspelling or might be a foreign version 
of the term. Some of these matches will be wrong, but overall, it's a good use 
of time to assign to what they look very similar to. Here we set the scorer to 
match whole terms/phrases, and the fuzzy matching score must be 90 or higher.

# Quick test, if you want - punctuation difference
fuzz.ratio('Testing FuzzyWuzzy', 'Testing FuzzyWuzzy!!')

FuzzyWuzzyResults - What the results of this function mean:
('hippocratic oath', 100, 2987)
('Best match string from dataset_2' (PastMatches), 'Score of best match', 'Index of best match string in PastMatches')

Re-start:
listOfUniqueUnassignedAfterUmls11 = pd.read_excel('02_Run_APIs_files/listOfUniqueUnassignedAfterUmls11.xlsx')
PastMatches = pd.read_excel('01_Import-transform_files/PastMatches.xlsx')
'''


# FIXME - Need to solve the issue around NaN vs '', which keeps coming up. Solve it the same way everywhere.
# Make the code fit what's easiest for Python so you don't have to keep changing
# listOfUniqueUnassignedAfterHC = logAfterHCGuesses.replace(np.nan, '', regex=True)


# Create list of unique entries that were searched more than x times.
listOfUniqueUnassignedAfterHC = logAfterHCGuesses.loc[logAfterHCGuesses['SemanticType'] == '']
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.groupby('AdjustedQueryTerm').size()
listOfUniqueUnassignedAfterHC = pd.DataFrame({'timesSearched':listOfUniqueUnassignedAfterHC})
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.sort_values(by='timesSearched', ascending=False)
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.reset_index()

# This sets minimum appearances in log; helps assure we are starting with a "real" thing.
# There are many queries that are not discipherable, which appear only once.
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC[listOfUniqueUnassignedAfterHC.timesSearched >= 2]
# Or you can eyeball and use a row range, # listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.iloc[0:200]


def fuzzy_match(x, choices, scorer, cutoff):
    return process.extractOne(
        x, choices=choices, scorer=scorer, score_cutoff=cutoff
    )

# Create series FuzzyWuzzyResults
FuzzyAutoAdd1 = listOfUniqueUnassignedAfterHC.loc[:, 'AdjustedQueryTerm'].apply(
        fuzzy_match,
    args=( PastMatches.loc[:, 'AdjustedQueryTerm'], # Consider also running on PastMatches.PreferredTerm
            fuzz.ratio, # also fuzz.token_set_ratio
            90
        )
)

# Convert FuzzyWuzzyResults Series to df
FuzzyAutoAdd2 = pd.DataFrame(FuzzyAutoAdd1)
FuzzyAutoAdd2 = FuzzyAutoAdd2.dropna() # drop the nulls


# The below procedures will fail if the df has zero rows
if FuzzyAutoAdd2.empty:
    logAfterFuzzyAuto = logAfterHCGuesses
    print('\n=================================\n FuzzyAutoAdd dataframe is empty\n=================================\n')
else:
    # Move Index (IDs) into 'FuzzyIndex' col because Index values will be discarded
    FuzzyAutoAdd2 = FuzzyAutoAdd2.reset_index()
    FuzzyAutoAdd2 = FuzzyAutoAdd2.rename(columns={'index': 'FuzzyIndex'})
    FuzzyAutoAdd2 = FuzzyAutoAdd2[FuzzyAutoAdd2.AdjustedQueryTerm.notnull() == True] # remove nulls
    # Move tuple output into 3 cols
    FuzzyAutoAdd2[['ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex']] = FuzzyAutoAdd2['AdjustedQueryTerm'].apply(pd.Series)
    FuzzyAutoAdd2.drop(['AdjustedQueryTerm'], axis=1, inplace=True) # drop tuples
    # Merge result to the orig source list cols
    FuzzyAutoAdd3 = pd.merge(FuzzyAutoAdd2, listOfUniqueUnassignedAfterHC, how='left', left_index=True, right_index=True)
    FuzzyAutoAdd3.columns
    # 'FuzzyIndex', 'ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex', 'AdjustedQueryTerm', 'timesSearched'
    # Change col order for browsability if you want to analyze this by itself
    FuzzyAutoAdd3 = FuzzyAutoAdd3[['AdjustedQueryTerm', 'ProbablyMeantGSTerm', 'FuzzyScore', 'timesSearched', 'FuzzyIndex', 'PastMatchesIndex']]
    # Join to PastMatches "probably meant" to acquire columns from the source of the match
    resultOfFuzzyMatch = pd.merge(FuzzyAutoAdd3, PastMatches, how='left', left_on='ProbablyMeantGSTerm', right_on='AdjustedQueryTerm')
    resultOfFuzzyMatch.columns
    '''
    'AdjustedQueryTerm_x', 'ProbablyMeantGSTerm', 'FuzzyScore',
           'timesSearched', 'FuzzyIndex', 'PastMatchesIndex', 'ui',
           'AdjustedQueryTerm_y', 'PreferredTerm', 'SemanticType'
    '''   
    # AdjustedQueryTerm_x is the term that was previously unmatchable; rename as AdjustedQueryTerm
    # AdjustedQueryTerm_y, AdjustedQueryTerm from PastMatches, can be dropped
    # ProbablyMeantGSTerm is the PastMatches AdjustedQueryTerm; keep so future editors understand the entry
    resultOfFuzzyMatch.rename(columns={'AdjustedQueryTerm_x': 'AdjustedQueryTerm'}, inplace=True)
    resultOfFuzzyMatch = resultOfFuzzyMatch[['ui', 'AdjustedQueryTerm', 'ProbablyMeantGSTerm', 'PreferredTerm', 'SemanticType']]
    # The below append breaks if data type is not str
    resultOfFuzzyMatch['AdjustedQueryTerm'] = resultOfFuzzyMatch['AdjustedQueryTerm'].astype(str)
    # Append new entries to HighConfidenceGuesses
    newHighConfidenceGuesses = HighConfidenceGuesses.append(resultOfFuzzyMatch, sort=True)
    # Write out for future runs
    writer = pd.ExcelWriter(dataMatchFiles + 'HighConfidenceGuesses.xlsx')
    newHighConfidenceGuesses.to_excel(writer,'HighConfidenceGuesses')
    # df2.to_excel(writer,'Sheet2')
    writer.save()
    # Join new entries to search log
    logAfterFuzzyAuto = pd.merge(logAfterHCGuesses, newHighConfidenceGuesses, how='left', left_on='AdjustedQueryTerm', right_on='AdjustedQueryTerm')
    logAfterFuzzyAuto.columns
    '''
    'SearchID', 'SessionID', 'StaffYN', 'Referrer', 'Query', 'Timestamp',
           'AdjustedQueryTerm', 'ui_x', 'ProbablyMeantGSTerm_x', 'ui_x',
           'PreferredTerm_x', 'SemanticType_x', 'ProbablyMeantGSTerm_y',
           'SemanticType_y', 'PreferredTerm_y', 'ui_y'
    '''
    # Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
    logAfterFuzzyAuto['ui2'] = logAfterFuzzyAuto['ui_x'].where(logAfterFuzzyAuto['ui_x'].notnull(), logAfterFuzzyAuto['ui_y'])
    logAfterFuzzyAuto['ui2'] = logAfterFuzzyAuto['ui_y'].where(logAfterFuzzyAuto['ui_y'].notnull(), logAfterFuzzyAuto['ui_x'])
    logAfterFuzzyAuto['ProbablyMeantGSTerm2'] = logAfterFuzzyAuto['ProbablyMeantGSTerm_x'].where(logAfterFuzzyAuto['ProbablyMeantGSTerm_x'].notnull(), logAfterFuzzyAuto['ProbablyMeantGSTerm_y'])
    logAfterFuzzyAuto['ProbablyMeantGSTerm2'] = logAfterFuzzyAuto['ProbablyMeantGSTerm_y'].where(logAfterFuzzyAuto['ProbablyMeantGSTerm_y'].notnull(), logAfterFuzzyAuto['ProbablyMeantGSTerm_x'])
    logAfterFuzzyAuto['PreferredTerm2'] = logAfterFuzzyAuto['PreferredTerm_y'].where(logAfterFuzzyAuto['PreferredTerm_y'].notnull(), logAfterFuzzyAuto['PreferredTerm_x'])
    logAfterFuzzyAuto['SemanticType2'] = logAfterFuzzyAuto['SemanticType_x'].where(logAfterFuzzyAuto['SemanticType_x'].notnull(), logAfterFuzzyAuto['SemanticType_y'])
    logAfterFuzzyAuto['SemanticType2'] = logAfterFuzzyAuto['SemanticType_y'].where(logAfterFuzzyAuto['SemanticType_y'].notnull(), logAfterFuzzyAuto['SemanticType_x'])
    logAfterFuzzyAuto.drop(['ui_x', 'ui_y', 'ProbablyMeantGSTerm_x', 'ProbablyMeantGSTerm_y',
                            'PreferredTerm_x', 'PreferredTerm_y',
                            'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
    logAfterFuzzyAuto.rename(columns={'ui2': 'ui', 'ProbablyMeantGSTerm2': 'ProbablyMeantGSTerm', 
                                      'PreferredTerm2': 'PreferredTerm',
                                      'SemanticType2': 'SemanticType'}, inplace=True)
    # Re-sort full file
    logAfterFuzzyAuto = logAfterFuzzyAuto.sort_values(by='AdjustedQueryTerm', ascending=True)
    logAfterFuzzyAuto = logAfterFuzzyAuto.reset_index()
    logAfterFuzzyAuto.drop(['index'], axis=1, inplace=True)


del [[logAfterHCGuesses, FuzzyAutoAdd3, resultOfFuzzyMatch]]


# -------------
# How we doin?
# -------------
rowCount = len(logAfterFuzzyAuto)
TotUniqueEntries = logAfterFuzzyAuto['AdjustedQueryTerm'].nunique()

# Assigned = logAfterFuzzyAuto['SemanticType'].count()
Assigned = (logAfterFuzzyAuto['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterFuzzyAuto['SemanticType'].value_counts().head(10)))
print("\n\n===================================================\n ** logAfterFuzzyAuto stats - {} **\n===================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned\n".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


del [[FuzzyAutoAdd1, FuzzyAutoAdd2, HighConfidenceGuesses, listOfUniqueUnassignedAfterHC]]


#%%
# ==========================================
# 10. Apply matches from QuirkyMatches.xlsx
# ==========================================
'''
The QuirkyMatches data comes from step 03, where a human selects entries 
from a matching / vetting interface. 

THESE ARE FREE-FORM ASSIGNMENTS WHERE SEMANTIC TYPE INFORMATION IS GUESSED AT.

While the PastMatches and HighConfidenceGuesses
entries could be incorporated into follow-on fuzzy matching, clustering, and
classification procedures, QuirkyMatches should be used more carefully, 
because these are misspelled, in a foreign language, are PARTIAL product/
service names, etc.

Periodically you can clean entries here and move them into PastMatches, if 
you decide they pass muster.
'''

# Open QuirkyMatches
QuirkyMatches = dataMatchFiles + 'QuirkyMatches.xlsx' # Human-chosen terms that might be misspelled, foreign, etc.
QuirkyMatches = pd.read_excel(QuirkyMatches)

# FIXME - Update in file
# QuirkyMatches.rename(columns={'SemanticTypeName': 'SemanticType'}, inplace=True)

# FIXME - R&D why it's not stored in the file this way...
QuirkyMatches['SemanticType2'] = QuirkyMatches['SemanticTypeName'].where(QuirkyMatches['SemanticTypeName'].notnull(), QuirkyMatches['NewSemanticTypeName'])
QuirkyMatches.drop(['Unnamed: 0', 'NewSemanticTypeName','SemanticTypeName'], axis=1, inplace=True)
QuirkyMatches.rename(columns={'SemanticType2': 'SemanticType'}, inplace=True)


# Join new UMLS API adds to the current search log master
logAfterStep1 = pd.merge(logAfterFuzzyAuto, QuirkyMatches, left_on='AdjustedQueryTerm', right_on='AdjustedQueryTerm', how='left')
logAfterStep1.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'AdjustedQueryTerm', 'Unnamed: 0_x', 'Unnamed: 0_y',
       'ProbablyMeantGSTerm', 'ui', 'PreferredTerm_x', 'SemanticType',
       'Unnamed: 0', 'NewSemanticTypeName', 'SemanticTypeName',
       'PreferredTerm_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterStep1['PreferredTerm2'] = logAfterStep1['PreferredTerm_x'].where(logAfterStep1['PreferredTerm_x'].notnull(), logAfterStep1['PreferredTerm_y'])
logAfterStep1['PreferredTerm2'] = logAfterStep1['PreferredTerm_y'].where(logAfterStep1['PreferredTerm_y'].notnull(), logAfterStep1['PreferredTerm_x'])
logAfterStep1['SemanticType2'] = logAfterStep1['SemanticType_x'].where(logAfterStep1['SemanticType_x'].notnull(), logAfterStep1['SemanticType_y'])
logAfterStep1['SemanticType2'] = logAfterStep1['SemanticType_y'].where(logAfterStep1['SemanticType_y'].notnull(), logAfterStep1['SemanticType_x'])

logAfterStep1.drop(['PreferredTerm_x', 'PreferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterStep1.rename(columns={'PreferredTerm2': 'PreferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)

# Re-sort full file
logAfterStep1 = logAfterStep1.sort_values(by='AdjustedQueryTerm', ascending=True)
logAfterStep1 = logAfterStep1.reset_index()
logAfterStep1.drop(['index'], axis=1, inplace=True)


# Save to file so you can open in future sessions, if needed
writer = pd.ExcelWriter(dataInterim + logFileName + '-logAfterStep1.xlsx')
logAfterStep1.to_excel(writer,'logAfterStep1')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -------------
# How we doin?
# -------------
rowCount = len(logAfterStep1)
TotUniqueEntries = logAfterStep1['AdjustedQueryTerm'].nunique()

# Assigned = logAfterStep1['SemanticType'].count()
Assigned = (logAfterStep1['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterStep1['SemanticType'].value_counts().head(10)))
print("\n\n===============================================\n ** logAfterStep1 stats - {} **\n===============================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


del [[PastMatches, logAfterFuzzyAuto, QuirkyMatches, newHighConfidenceGuesses]]



#%%
# =============================================
# 11. Create 'uniques' dataframe/file for API
# =============================================
'''
Prepare a list of unique terms to process with API.

Re-starting?
listOfUniqueUnassignedAfterStep1 = pd.read_excel(dataInterim + 'listOfUniqueUnassignedAfterStep1.xlsx')
'''

# Unique unassigned terms and frequency of occurrence
uniquesForApiNormalized = logAfterStep1.loc[logAfterStep1['SemanticType'] == '']
uniquesForApiNormalized = uniquesForApiNormalized.groupby('AdjustedQueryTerm').size()
uniquesForApiNormalized = pd.DataFrame({'timesSearched':uniquesForApiNormalized})
uniquesForApiNormalized = uniquesForApiNormalized.sort_values(by='timesSearched', ascending=False)
uniquesForApiNormalized = uniquesForApiNormalized.reset_index()


# ---------------------------------------------------------------
# Eyeball for fixes - Don't give the API things it can't resolve
# ---------------------------------------------------------------
'''
Act based on what the dataframes say; drop, modify, etc.
'''

# Save to file so you can open in future sessions
writer = pd.ExcelWriter(dataInterim + logFileName + '-uniquesForStep2.xlsx')
uniquesForApiNormalized.to_excel(writer,'uniquesForApiNormalized')
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%


# =====================================================
# 12. If working with multiple processed logs at once
# =====================================================
'''
For start-up / multiple runs, I run whole script on each of several log files, 
renaming output files after each run, then open and combine, for the API work
that is next.
'''

# ----------------
# Combine uniques
# ----------------

# Open step 1 files for uniques (the API)
uniques01 = pd.read_excel(dataInterim + 'SiteSearch2018-12-uniquesForStep2.xlsx')
uniques02 = pd.read_excel(dataInterim + 'SiteSearch2019-01-uniquesForStep2.xlsx')
uniques03 = pd.read_excel(dataInterim + 'SiteSearch2019-02-uniquesForStep2.xlsx')
uniques04 = pd.read_excel(dataInterim + 'SiteSearch2019-03-uniquesForStep2.xlsx')
uniques05 = pd.read_excel(dataInterim + 'SiteSearch2019-04-uniquesForStep2.xlsx')
uniques06 = pd.read_excel(dataInterim + 'SiteSearch2019-05-uniquesForStep2.xlsx')


# Append new data
combinedLogs = uniques01.append([uniques02, uniques03, uniques04, uniques05,
                                            uniques06])

del [[uniques01, uniques02, uniques03, uniques04, uniques05, uniques06]]

# Summarize across logs, 1 row per term
deDupedUniques = combinedLogs.groupby(['AdjustedQueryTerm'])['timesSearched'].sum().sort_values(ascending=False).reset_index()
   
deDupedUniques = deDupedUniques.iloc[0:10000]

combinedLogs.head(50)

# Write out
writer = pd.ExcelWriter(dataInterim + 'S1Uniques-Combined.xlsx')
deDupedUniques.to_excel(writer,'deDupedUniques')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -----------------------
# Combine processed logs
# -----------------------

# Open step 1 files for log
logAfterStep101 = pd.read_excel(dataInterim + 'SiteSearch2018-12-logAfterStep1.xlsx')
logAfterStep102 = pd.read_excel(dataInterim + 'SiteSearch2019-01-logAfterStep1.xlsx')
logAfterStep103 = pd.read_excel(dataInterim + 'SiteSearch2019-02-logAfterStep1.xlsx')
logAfterStep104 = pd.read_excel(dataInterim + 'SiteSearch2019-03-logAfterStep1.xlsx')
logAfterStep105 = pd.read_excel(dataInterim + 'SiteSearch2019-04-logAfterStep1.xlsx')
logAfterStep106 = pd.read_excel(dataInterim + 'SiteSearch2019-05-logAfterStep1.xlsx')


# Append new data
combinedLogs = logAfterStep101.append([logAfterStep102, logAfterStep103, logAfterStep104, 
                                           logAfterStep105, logAfterStep106], sort=True)

# Write out
writer = pd.ExcelWriter(dataInterim + 'S1Logs-Combined.xlsx')
combinedLogs.to_excel(writer,'combinedLogs')
# df2.to_excel(writer,'Sheet2')
writer.save() 
    
    
del [[logAfterStep101, logAfterStep102, logAfterStep103, logAfterStep104, logAfterStep105, logAfterStep106]]






del [[combinedLogs]]


#%%

"""
# -------------------------------
# How we doin? Visualize results
# -------------------------------


'''
FIXME - Add: x% of the terms searched 3 times or more, have been classified

# Full dataset, which terms were searched 3+ times?
cntThreeOrMore = logAfterStep1.groupby('AdjustedQueryTerm').size()
cntThreeOrMore = pd.DataFrame({'timesSearched':cntThreeOrMore})
cntThreeOrMore = cntThreeOrMore.sort_values(by='timesSearched', ascending=False)
cntThreeOrMore = cntThreeOrMore.reset_index()
threeOrMoreSearches = cntThreeOrMore.loc[cntThreeOrMore['timesSearched'] >= 3]

# 5454

# Count of these terms where SemanticType notnull

cutDownFull = logAfterStep1[['AdjustedQueryTerm', 'SemanticType']]

cutDownFull.loc[cutDownFull['SemanticType'].str.contains(''), 'SemanticType'] = 'Yes'
'''

print("\n\n====================================================================\n ** Import and Trasformation Completed for {}! **\n    When running multiple files, re-name each new file\n====================================================================".format(logFileName))


# -----------------
# Visualize results
# -----------------
# These break in Spyder autorun

'''
# Pie for percentage of rows assigned; https://pythonspot.com/matplotlib-pie-chart/
totCount = len(logAfterStep1)
Assigned = (logAfterStep1['PreferredTerm'].values != '').sum()
Unassigned = (logAfterStep1['PreferredTerm'].values == '').sum()
labels = ['Assigned', 'Unassigned']
sizes = [Assigned, Unassigned]
colors = ['steelblue', '#fc8d59']
explode = (0.1, 0)  # explode 1st slice
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'Step 1' processing - \n{} queries with {} unassigned".format(totCount, Unassigned))
plt.show()


# Bar of SemanticType categories, horizontal
# Source: http://robertmitchellv.com/blog-bar-chart-annotations-pandas-mpl.html
ax = logAfterStep1['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(10,6),
                                                 color="steelblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'Step 1' processing \nwith {:,} of {:,} unassigned".format(Unassigned, totCount), fontsize=14)
ax.set_xlabel("Number of searches", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.31, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.3)
'''


#%%


# =====================================================
# If working with multiple processed 'uniques' at once
# =====================================================
'''
For start-up / multiple runs, I run whole script on each of several log files, 
renaming output files after each run, then open and combine, for the API work
that is next.
'''

# Open step 1 files for uniques (the API)
uniques01 = pd.read_excel(dataInterim + 'SiteSearch2018-12-uniquesForStep2.xlsx')
uniques02 = pd.read_excel(dataInterim + 'SiteSearch2019-01-uniquesForStep2.xlsx')
uniques03 = pd.read_excel(dataInterim + 'SiteSearch2019-02-uniquesForStep2.xlsx')
uniques04 = pd.read_excel(dataInterim + 'SiteSearch2019-03-uniquesForStep2.xlsx')
uniques05 = pd.read_excel(dataInterim + 'SiteSearch2019-04-uniquesForStep2.xlsx')
uniques06 = pd.read_excel(dataInterim + 'SiteSearch2019-05-uniquesForStep2.xlsx')


# Append new data
combinedLogs = uniques01.append([uniques02, uniques03, uniques04, uniques05,
                                            uniques06])

    
# If combinedLogs is huge, you could have a look at a subset
viewRows = combinedLogs[260000:260800]

# Free memory
del [[uniques05, uniques06, uniques07, uniques08, uniques09, uniques10]]

# Running API requires time; try focusing on terms searched 3+ times, 
# i.e., it's probably a real thing. May-Oct 18, mine was 13,426 terms, nice
listToCheck1 = combinedLogs[combinedLogs.timesSearched >= 3]

# Or limit by rows
# listToCheck1 = combinedLogs[0:15000]


# ----------------------------------------------------



viewRows = combinedLogs[10000:11000]



'''
# Open step 1 files for log
logAfterStep1201805 = pd.read_excel(dataInterim + 'logAfterStep1-2018-05.xlsx')
logAfterStep1201806 = pd.read_excel(dataInterim + 'logAfterStep1-2018-06.xlsx')
logAfterStep1201807 = pd.read_excel(dataInterim + 'logAfterStep1-2018-07.xlsx')
logAfterStep1201808 = pd.read_excel(dataInterim + 'logAfterStep1-2018-08.xlsx')
logAfterStep1201809 = pd.read_excel(dataInterim + 'logAfterStep1-2018-09.xlsx')
logAfterStep1201810 = pd.read_excel(dataInterim + 'logAfterStep1-2018-10.xlsx')

# Append new data
combinedLogs = logAfterStep1201805.append([logAfterStep1201806, logAfterStep1201807, 
                                            logAfterStep1201808, logAfterStep1201809,
                                            logAfterStep1201810], sort=True)

# del [[logAfterStep1201805, logAfterStep1201806, logAfterStep1201807, logAfterStep1201808, logAfterStep1201809, logAfterStep1201810]]


combinedLogs.columns
'''
'ProbablyMeantGSTerm', 'Query', 'Referrer', 'SearchID',
'SemanticType', 'SessionID', 'StaffYN', 'Timestamp',
'AdjustedQueryTerm', 'PreferredTerm', 'ui'
'''

combinedLogs = combinedLogs[['SearchID', 'SessionID', 'Referrer', 
                             'AdjustedQueryTerm','PreferredTerm', 'ui', 
                             'ProbablyMeantGSTerm', 'SemanticType', 'StaffYN',
                             'Timestamp']]

viewRows = combinedLogs[10000:11000]

# Save to file so you can open in future sessions
writer = pd.ExcelWriter(dataInterim + 'combinedLogs.xlsx')
combinedLogs.to_excel(writer,'combinedLogs')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

'''
# I think the below can be obsoleted; I was not understanding. Replaced 9/19


# FIXME - see notes below, problem here
logAfterPastMatches = pd.merge(logAfterUmlsTerms, PastMatches, left_on=['AdjustedQueryTerm', 'ui', 'PreferredTerm', 'SemanticType'], right_on=['AdjustedQueryTerm', 'ui', 'PreferredTerm', 'SemanticType'], how='left')

logAfterPastMatches.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
'AdjustedQueryTerm', 'wordCount', 'ui_x', 'PreferredTerm_x',
'SemanticType_x', 'Unnamed: 0', 'Unnamed: 0.1', 'SemanticType_y',
'PreferredTerm_y', 'ui_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_x'].where(logAfterPastMatches['ui_x'].notnull(), logAfterPastMatches['ui_y'])
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_y'].where(logAfterPastMatches['ui_y'].notnull(), logAfterPastMatches['ui_x'])
logAfterPastMatches['PreferredTerm2'] = logAfterPastMatches['PreferredTerm_x'].where(logAfterPastMatches['PreferredTerm_x'].notnull(), logAfterPastMatches['PreferredTerm_y'])
logAfterPastMatches['PreferredTerm2'] = logAfterPastMatches['PreferredTerm_y'].where(logAfterPastMatches['PreferredTerm_y'].notnull(), logAfterPastMatches['PreferredTerm_x'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_x'].where(logAfterPastMatches['SemanticType_x'].notnull(), logAfterPastMatches['SemanticType_y'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_y'].where(logAfterPastMatches['SemanticType_y'].notnull(), logAfterPastMatches['SemanticType_x'])
logAfterPastMatches.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y', 'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)


"""

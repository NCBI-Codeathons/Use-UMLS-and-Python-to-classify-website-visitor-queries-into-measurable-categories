#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec 30 10:01:27 2018

@authors: dan.wendling@nih.gov

Last modified: 2019-11-11

--------------------------------------------------
 ** Semantic Search Analysis: Tag and Finalize **
--------------------------------------------------

This script: Add columns to support reporting, such as the high-level 
SemanticGroup, plus columns that help to output the Semantic Types hierarchy.
Also add column CustomTopics and build opioids super-concept.

INPUTS:
    - data/interim/ logAfterStep4.xlsx - Processed log
    - CustomTags.xlsx - Such as opioid constellation (optional)
    - data/matchFiles/SemanticNetworkReference.xlsx - Semantic structure
    - data/interim/LogAfterMetathesaurus.xlsx - Processed log
    
OUTPUTS:
    
    
----------------
SCRIPT CONTENTS
----------------
1. Start-up / What to put into place, where
2. Add custom tags, if any - CustomTags.xlsx
3. Add data from SemanticNetworkReference
4. Append newly processed data to historical log

FUTURE 
- Add data quality checks; try to surface data errors, outliers, etc.
- Resample from daily to weekly? The minimum summary in charts is weekly...
    Perhaps df.resample('W-MON').sum()

** THIS SCRIPT CAN BE RUN AUTOMATICALLY **

"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import os
from datetime import datetime, timedelta
# import random
from scipy.optimize import basinhopping, differential_evolution

# Set working directory and directories for read/write
home_folder = os.path.expanduser('~')
os.chdir(home_folder + '/Projects/classifysearches')

dataRaw = 'data/raw/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
dataProcessed = 'data/processed/' # Ready to visualize


#%%
# ============================================
# 2. Wrangle the tagged log
# ============================================

# Load the newly processed search log file
newlyProcessedRaw = pd.read_excel(dataInterim + 'LogAfterMetathesaurus.xlsx')
newlyProcessedRaw.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType'
'''

# Load the lightly modified original log
CombinedFullLog = pd.read_excel(dataInterim + '01_CombinedSearchFullLog.xlsx')
CombinedFullLog.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq', 'AdjustedQueryTerm'
'''


# ---------------------
# Join to original log
# ---------------------

taggedLog = pd.merge(CombinedFullLog, newlyProcessedRaw, how='inner', left_on=['Query'], right_on=['Query'])
taggedLog.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq_x', 'AdjustedQueryTerm_x', 'LocationOfSearch',
       'AdjustedQueryTerm_y', 'TotalSearchFreq_y', 'ui', 'PreferredTerm',
       'SemanticType'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. 
# Temporary fix: Move _y into _x if _x is empty; or here: where _x has content, use _x, otherwise use _y
taggedLog['TotalSearchFreq2'] = taggedLog['TotalSearchFreq_x'].where(taggedLog['TotalSearchFreq_x'].notnull(), taggedLog['TotalSearchFreq_y'])
taggedLog['TotalSearchFreq2'] = taggedLog['TotalSearchFreq_y'].where(taggedLog['TotalSearchFreq_y'].notnull(), taggedLog['TotalSearchFreq_x'])
taggedLog['AdjustedQueryTerm2'] = taggedLog['AdjustedQueryTerm_x'].where(taggedLog['AdjustedQueryTerm_x'].notnull(), taggedLog['AdjustedQueryTerm_y'])
taggedLog['AdjustedQueryTerm2'] = taggedLog['AdjustedQueryTerm_y'].where(taggedLog['AdjustedQueryTerm_y'].notnull(), taggedLog['AdjustedQueryTerm_x'])

taggedLog.drop(['TotalSearchFreq_x', 'TotalSearchFreq_y',
                          'AdjustedQueryTerm_x', 'AdjustedQueryTerm_y'], axis=1, inplace=True)
taggedLog.rename(columns={'TotalSearchFreq2': 'TotalSearchFreq',
                                    'AdjustedQueryTerm2': 'AdjustedQueryTerm'}, inplace=True)

taggedLog.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'LocationOfSearch', 'ui', 'PreferredTerm', 'SemanticType',
       'TotalSearchFreq', 'AdjustedQueryTerm'
'''


# ---------------------
# Update cals
# ---------------------

# New col describes what the search location was
CombinedFullLog['LocationOfSearch'] = ''

# Clicks + TotalSearchFreq = GoogleAndLocal
CombinedFullLog['LocationOfSearch'] = np.where( ( (CombinedFullLog['Clicks'].notnull() ) & (CombinedFullLog['TotalUniqueSearches'].notnull() ) ), 'GoogleAndLocal', CombinedFullLog['LocationOfSearch'])
# TotalSearchFreq only = LocalResults
CombinedFullLog['LocationOfSearch'] = np.where( ( (CombinedFullLog['Clicks'].isnull() ) & (CombinedFullLog['TotalUniqueSearches'].notnull() ) ), 'LocalResults', CombinedFullLog['LocationOfSearch'])
# Clicks only = GoogleResults
CombinedFullLog['LocationOfSearch'] = np.where( ( (CombinedFullLog['Clicks'].notnull() ) & (CombinedFullLog['TotalUniqueSearches'].isnull() ) ), 'GoogleResults', CombinedFullLog['LocationOfSearch'])

# Change nan to ''
taggedLog['PreferredTerm'] = taggedLog['PreferredTerm'].fillna('')
taggedLog['SemanticType'] = taggedLog['SemanticType'].fillna('')


# -------------------
# Add Semantic Group
# -------------------




SemTypesCnt = taggedLog['SemanticType'].value_counts().reset_index()

# write out
writer = pd.ExcelWriter(dataProcessed + 'taggedLog.xlsx')
taggedLog.to_excel(writer,'taggedLog', index=False)
SemTypesCnt.to_excel(writer,'SemTypesCnt')
writer.save()


# -------------
# How we doin?
# -------------

# Total queries in log
SearchesRepresentedTot = taggedLog['TotalSearchFreq'].sum().astype(int)
SearchesAssignedTot = taggedLog.loc[taggedLog['SemanticType'] != '']
SearchesAssignedTot = SearchesAssignedTot['TotalSearchFreq'].sum().astype(int)
SearchesAssignedPercent = (SearchesAssignedTot / SearchesRepresentedTot * 100).astype(int)
# PercentOfSearchesUnAssigned = 100 - PercentOfSearchesAssigned
RowsTot = len(taggedLog)
RowsAssignedCnt = (taggedLog['SemanticType'].values != '').sum() # .isnull().sum()
# RowsUnassignedCnt = TotRows - RowsAssigned
RowsAssignedPercent = (RowsAssignedCnt / RowsTot * 100).astype(int)

# print("\nTop Semantic Types\n{}".format(taggedLog['SemanticType'].value_counts().head(10)))
print("\n====================================================\n ** taggedLog: {}% of total search volume tagged **\n====================================================\n\n{:,} of {:,} searches ({}%) assigned;\n{:,} of {:,} rows ({}%) assigned".format(SearchesAssignedPercent, SearchesAssignedTot, SearchesRepresentedTot, SearchesAssignedPercent, RowsAssignedCnt, RowsTot, RowsAssignedPercent))


#%%

# Sort rows by Date
newlyProcessedRaw = newlyProcessedRaw.sort_values(by='Date', ascending=True).reset_index(drop=True)


# FIXME - MANUAL WORK!!  I'D LIKE TO RUN THIS IN PHASE 1, WHICH CAN CURRENTLY 
# RUN AUTOMATICALLY, BUT I DON'T KNOW HOW TO MAKE THIS AUTOMATIC.
    
# Eyeball beginning and end of log and remove partial weeks if needed.
# One week is Sunday through Saturday.
newlyProcessedRaw['Date'].head() # 2018
newlyProcessedRaw['Date'].tail() # 2018-12, stop with 29th

# Drop by date based on what you find. Can use != < >
# newlyProcessedRaw = newlyProcessedRaw.loc[(newlyProcessedRaw['Date'] != "2018-12-30")]



#%%
# ==========================================
# 3. Add data from SemanticNetworkReference
# ==========================================
'''
SemanticNetworkReference would be better as a database table - would be 
useful for rendering through browser, PLUS you could have a UI to help
you update it.

Source file needs to be manually updated for terms with multiple sem
types, when the sem type combination and order have not already been 
cataloged.
'''

# Add Semantic super-groups
SemanticNetworkReference = pd.read_excel(SemanticNetworkReference)

# Join
newlyProcessedComplete = pd.merge(newlyProcessedRaw, SemanticNetworkReference, how='left', on='SemanticType')
newlyProcessedComplete.columns
'''
'Referrer', 'Query', 'Date', 'CountForPgDate', 'adjustedQueryTerm',
       'ProbablyMeantGSTerm', 'ui', 'preferredTerm', 'SemanticType',
       'CustomTag', 'SemanticGroupCode', 'SemanticGroup', 'SemanticGroupAbr',
       'CustomTreeNumber', 'BranchPosition', 'Definition', 'Examples',
       'RelationName', 'SemTypeTreeNo', 'UsageNote', 'Abbreviation',
       'UniqueID', 'NonHumanFlag', 'RecordType', 'TUI'
'''

# Eyeball column label result; manual edits needed?
semGroups = newlyProcessedComplete['SemanticGroup'].value_counts().reset_index()

semTypes = newlyProcessedComplete['SemanticType'].value_counts().reset_index()

# Reduce and reorder
newlyProcessedComplete = newlyProcessedComplete[['Date', 'Referrer', 'adjustedQueryTerm', 
                               'CountForPgDate', 'ProbablyMeantGSTerm', 'ui', 
                               'preferredTerm', 'SemanticType', 'SemanticGroupCode', 
                               'SemanticGroup', 'CustomTreeNumber', 'BranchPosition', 
                               'CustomTag']]

# When SemanticType is null, set SemanticType and SemanticGroup to "unassigned"
newlyProcessedComplete.loc[newlyProcessedComplete.SemanticType.isnull(), 'SemanticType'] = 'Unassigned-Long Tail'
newlyProcessedComplete.loc[newlyProcessedComplete.SemanticGroup.isnull(), 'SemanticGroup'] = 'Unassigned-Long Tail'



#%%
# =================================================
# 4. Append newly processed data to historical log
# =================================================
'''
If this is the first log analyzed, alter this;
    SemanticSearchLogHistorical = newlyProcessedComplete
    write to file.
'''


# Load the historical log (previously compiled logs that don't yet include this week)
SemanticSearchLogHistorical = pd.read_excel(SemanticSearchLogHistorical)

# Append the new to the old
SemanticSearchLogHistorical = SemanticSearchLogHistorical.append(newlyProcessedComplete, sort=True)

# Write out
writer = pd.ExcelWriter(dataProcessed + 'SemanticSearchLogHistorical.xlsx')
SemanticSearchLogHistorical.to_excel(writer,'SemanticSearchLogHistorical') # , index=False
# df2.to_excel(writer,'Sheet2')
writer.save()




#%%
# =============================================
# 2. Add custom tags, if any - CustomTags.xlsx
# =============================================
'''
Here, the example of opiods.

Precise matching, not very useful; not forgiving of alternative spellings, etc.
logWithCustomTags = pd.merge(newlyProcessedRaw, CustomTags, how='left', on='adjustedQueryTerm')

# FIXME - Below uses 'word stems' in CustomTagsFile, but is awkward.
'''

# Load custom tags
CustomTagsFile = pd.read_excel(CustomTags)
tagList = CustomTagsFile['adjustedQueryTerm'].tolist()
# CustomTagsFile.drop(['CustomTag'], axis=1, inplace=True)  

newlyProcessedRaw['CustomTag'] = ""

# Match string in the tags list to strings in the search queries
newlyProcessedRaw['CustomTag'] = newlyProcessedRaw['adjustedQueryTerm'].str.findall('|'.join(tagList))
# Set to string
newlyProcessedRaw['CustomTag'] = newlyProcessedRaw['CustomTag'].astype(str)
# Just need the custom tag name
newlyProcessedRaw.loc[newlyProcessedRaw['CustomTag'].str.contains('[a-z]{1,}', na=False), 'CustomTag'] = 'Opioids or addiction'

# Clean up
newlyProcessedRaw['CustomTag'] = newlyProcessedRaw['CustomTag'].str.replace('\[', '')
newlyProcessedRaw['CustomTag'] = newlyProcessedRaw['CustomTag'].str.replace('\]', '')



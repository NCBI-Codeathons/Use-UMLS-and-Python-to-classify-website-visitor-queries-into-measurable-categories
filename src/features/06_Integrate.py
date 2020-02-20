#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 25 12:57:48 2020

@authors: Dan Wendling

Last modified: 2020-02-19

--------------------------------------------------
 ** Semantic Search Analysis: Integrate **
--------------------------------------------------

** CHANGE FILE NAMING BEFORE RUNNING!! **


aThis script: Join the new data to your old data (if any). For the file 
TaggedLogAllMonths.xlsx, the script replaces total search counts to existing 
query rows and adds new rows for new queries; for the Tableau discovery UI. 
The file BiggestMovers.xlsx follows the same procedure regarding row addition,
however a new column is appended for every month of data to allow for time 
series analysis over months.

After you have your second month of data, dupe off dataProcessed + 'taggedLog' + TimePeriod + '.xlsx'
to dataProcessed + 'TaggedLogAllMonths.xlsx'.


INPUTS:
    - data/processed/taggedLog-[TimePeriod].xlsx - Importable into Tableau, etc. but also summaries for Excel users
    - dataProcessed/'BiggestMovers' + TimePeriod + '.xlsx' - For PreferredTerm trends

OUTPUTS:
    - reports/TaggedLogAllMonths.xlsx - Summarize for discovery UI
    - data/processed/BiggestMovers.xlsx - Summarize for time series; study
    trends across time.
    

----------------
SCRIPT CONTENTS
----------------
1. Start-up / What to put into place, where
2. Append columns to TaggedLogAllMonths.xlsx
3. Append columns to BiggestMoversAllMonths.xlsx
4. Create summary infographic
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

from pathlib import *
# To be used with str(Path.home())

# Set working directory and directories for read/write
home_folder = str(Path.home()) # os.path.expanduser('~')
os.chdir(home_folder + '/Projects/classifysearches')

dataRaw = 'data/raw/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
dataProcessed = 'data/processed/' # Ready to visualize
reports = 'reports/'


#%%
# =============================================
# 2. Append columns to TaggedLogAllMonths.xlsx
# =============================================
'''
You'll need to build this based on what you've already done.
After processing the second month, you can create TaggedLogAllMonths.

In this example code, 3 months were processed before aggregating.
'''

# Bring in new tagged log
taggedLog201910 = pd.read_excel(dataProcessed + 'taggedLog201910.xlsx')
taggedLog201911 = pd.read_excel(dataProcessed + 'taggedLog201911.xlsx')
taggedLog201912 = pd.read_excel(dataProcessed + 'taggedLog201912.xlsx')

# Join
TaggedMerge1 = pd.merge(taggedLog201910, taggedLog201911, how='outer', on=['Query', 'AdjustedQueryTerm', 'SemanticType', 'SemanticGroup', 'LocationOfSearch'])
TaggedMerge1.columns
'''
'Query', 'AdjustedQueryTerm_x', 'TotalSearchFreq201910',
       'TotalUniqueSearches_x', 'SemanticGroup', 'SemanticType',
       'PreferredTerm_x', 'LocationOfSearch_x', 'Impressions_x', 'Clicks_x',
       'CTR_x', 'AveragePosition_x', 'ResultsPVSearch_x',
       'PercentSearchExits_x', 'PercentSearchRefinements_x',
       'TimeAfterSearch_x', 'AvgSearchDepth_x', 'ui_x', 'CustomTag1_x',
       'CustomTag2_x', 'AdjustedQueryTerm_y', 'TotalSearchFreq201911',
       'TotalUniqueSearches_y', 'PreferredTerm_y', 'LocationOfSearch_y',
       'Impressions_y', 'Clicks_y', 'CTR_y', 'AveragePosition_y',
       'ResultsPVSearch_y', 'PercentSearchExits_y',
       'PercentSearchRefinements_y', 'TimeAfterSearch_y', 'AvgSearchDepth_y',
       'ui_y', 'CustomTag1_y', 'CustomTag2_y'
'''

# Join the last
TaggedMerge2 = pd.merge(TaggedMerge1, taggedLog201912, how='outer', on=['Query', 'AdjustedQueryTerm', 'SemanticType', 'SemanticGroup', 'LocationOfSearch'])
TaggedMerge2.columns
'''
'Query', 'AdjustedQueryTerm', 'TotalSearchFreq201910',
       'TotalUniqueSearches_x', 'SemanticGroup', 'SemanticType',
       'PreferredTerm_x', 'LocationOfSearch', 'Impressions_x', 'Clicks_x',
       'CTR_x', 'AveragePosition_x', 'ResultsPVSearch_x',
       'PercentSearchExits_x', 'PercentSearchRefinements_x',
       'TimeAfterSearch_x', 'AvgSearchDepth_x', 'ui_x', 'CustomTag1_x',
       'CustomTag2_x', 'TotalSearchFreq201911', 'TotalUniqueSearches_y',
       'PreferredTerm_y', 'Impressions_y', 'Clicks_y', 'CTR_y',
       'AveragePosition_y', 'ResultsPVSearch_y', 'PercentSearchExits_y',
       'PercentSearchRefinements_y', 'TimeAfterSearch_y', 'AvgSearchDepth_y',
       'ui_y', 'CustomTag1_y', 'CustomTag2_y', 'TotalSearchFreq201912',
       'TotalUniqueSearches', 'PreferredTerm', 'Impressions', 'Clicks', 'CTR',
       'AveragePosition', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth', 'ui',
       'CustomTag1', 'CustomTag2'
'''

# Reduce and reorder
# If you changed the matchFiles over months, _x and _y may not be the same, and in that case
# you might want to reconcile them. Here the unneeded cols are dropped
TaggedMergeCleanup = TaggedMerge2[['Query', 'AdjustedQueryTerm', 
                                   'PreferredTerm', 'PreferredTerm_x', 'PreferredTerm_y', 
                                   'SemanticType', 'SemanticGroup', 
                                   'TotalSearchFreq201910', 'TotalSearchFreq201911', 'TotalSearchFreq201912', 
                                   'CustomTag1', # 'CustomTag1_x', 'CustomTag1_y', 
                                   'CustomTag2', # 'CustomTag2_x', 'CustomTag2_y', 
                                   # 'CustomTag3', # 'CustomTag3_x', 'CustomTag3_y',
                                   'LocationOfSearch']]

'''
prefNull = TaggedMergeCleanup['PreferredTerm'].isnull().sum() # 144960
prefXNull = TaggedMergeCleanup['PreferredTerm_x'].isnull().sum() # 132719
prefYNull = TaggedMergeCleanup['PreferredTerm_y'].isnull().sum() # 135750
'''

# FIXME - Same routine as other scripts use after merge, but this time to level-set PreferredTerm
TaggedMergeCleanup['PreferredTerm2'] = TaggedMergeCleanup['PreferredTerm_x'].where(TaggedMergeCleanup['PreferredTerm_x'].notnull(), TaggedMergeCleanup['PreferredTerm_y'])
TaggedMergeCleanup['PreferredTerm2'] = TaggedMergeCleanup['PreferredTerm_y'].where(TaggedMergeCleanup['PreferredTerm_y'].notnull(), TaggedMergeCleanup['PreferredTerm_x'])

# If it's still null, copy in AdjustedQueryTerm
TaggedMergeCleanup['PreferredTerm2'] = TaggedMergeCleanup['AdjustedQueryTerm'].where(TaggedMergeCleanup['PreferredTerm2'].isnull(), TaggedMergeCleanup['PreferredTerm2'])

# How many null in PreferredTerm?
# prefNull = TaggedMergeCleanup['PreferredTerm'].isnull().sum() # 144960
# prefNull


# Clean up
TaggedMergeCleanup.drop(['PreferredTerm', 'PreferredTerm_x', 'PreferredTerm_y'], axis=1, inplace=True)
TaggedMergeCleanup.rename(columns={'PreferredTerm2': 'PreferredTerm'}, inplace=True)

TaggedMergeCleanup.columns
'''
'Query', 'AdjustedQueryTerm', 'SemanticType', 'SemanticGroup',
       'TotalSearchFreq201910', 'TotalSearchFreq201911',
       'TotalSearchFreq201912', 'CustomTag1', 'CustomTag2', 'LocationOfSearch',
       'PreferredTerm'
'''

# Total month counts
TaggedMergeCleanup.fillna({'TotalSearchFreq201910': 0, 
                           'TotalSearchFreq201911': 0, 
                           'TotalSearchFreq201912': 0}, inplace = True)

# New col
TaggedMergeCleanup['TotalSearchFreq'] = ''
TaggedMergeCleanup['TotalSearchFreq'] = TaggedMergeCleanup.TotalSearchFreq201910 + TaggedMergeCleanup.TotalSearchFreq201911 + TaggedMergeCleanup.TotalSearchFreq201912

# Sort
TaggedMergeCleanup = TaggedMergeCleanup.sort_values(by=['TotalSearchFreq', 'Query'], ascending=[False, True])
TaggedMergeCleanup.reset_index(inplace=True)


# View a sample
# Top = TaggedMergeCleanup.head(50)
# TopAndBottom = Top.append(TaggedMergeCleanup.tail(50))

# Reorder again
TaggedMergeCleanup = TaggedMergeCleanup[['TotalSearchFreq', 'Query', 'AdjustedQueryTerm', 'PreferredTerm', 
                                         'SemanticType', 'SemanticGroup', 'TotalSearchFreq201910',
                                         'TotalSearchFreq201911', 'TotalSearchFreq201912', 
                                         'CustomTag1', 'CustomTag2', 'LocationOfSearch']]



# Write out
writer = pd.ExcelWriter(reports + 'TaggedLogAllMonths.xlsx')
TaggedMergeCleanup.to_excel(writer,'TaggedLogAllMonths', index=False)
writer.save()


#%%
# =================================================
# 3. Append columns to BiggestMoversAllMonths.xlsx
# =================================================
'''
BREAKS THE SCRIPT IF YOU DON'T HAVE MULTIPLE FILES WRITTEN OUT ALREADY
Creating a multi-month analysis of trends by PreferredTerm, is recommended, 
but this will be commented out, to avoid auto-run errors. Update the file 
names every time you run. The pilot project looks at 3 months at a time.
'''


# Open files that from previous analyses
BiggestMoversNew = pd.read_excel(dataProcessed + 'BiggestMovers' + TimePeriod + '.xlsx')

BiggestMovers10 = pd.read_excel(dataProcessed + 'BiggestMovers2019-10.xlsx')
BiggestMovers11 = pd.read_excel(dataProcessed + 'BiggestMovers2019-11.xlsx')

BiggestMovers10.columns
'''
'PreferredTerm', 'SemanticType', 'SemanticGroup', 'TotalSearchFreq',
       'PercentShare', 'Month'
'''

# Update col names
BiggestMovers10.rename(columns={'TotalSearchFreq': 'TotFreq201910', 'PercentShare': 'PerShare201910'}, inplace=True)
BiggestMovers11.rename(columns={'TotalSearchFreq': 'TotFreq201911', 'PercentShare': 'PerShare201911'}, inplace=True)
BiggestMovers12.rename(columns={'TotalSearchFreq': 'TotFreq201912', 'PercentShare': 'PerShare201912'}, inplace=True)

# Drop Month
BiggestMovers10.drop(['Month'], axis=1, inplace=True)
BiggestMovers11.drop(['Month'], axis=1, inplace=True)
BiggestMovers12.drop(['Month'], axis=1, inplace=True)

# Join on PreferredTerm
bgtemp = pd.merge(BiggestMovers10, BiggestMovers11, how='outer', on=['PreferredTerm', 'SemanticType', 'SemanticGroup'])
BiggestMoversFull = pd.merge(bgtemp, BiggestMovers12, how='outer', on=['PreferredTerm', 'SemanticType', 'SemanticGroup'])


# Set a floor on the last month: Had to be search 60 or more times in the month
BiggestMoversFull = BiggestMoversFull[BiggestMoversFull.TotFreq201912 >= 60]
# Track higher numbers in last month as positive, lower, negative
BiggestMoversFull['PercentDifferenceBeginningEnd'] = BiggestMoversFull.PerShare201912 - BiggestMoversFull.PerShare201910

# Don't allow nan in PercentDifferenceBeginningEnd
BiggestMoversFull = BiggestMoversFull.dropna(subset=['PercentDifferenceBeginningEnd'])

# sort by 2 cols
BiggestMoversFull = BiggestMoversFull.sort_values(by=['PercentDifferenceBeginningEnd', 'PreferredTerm'], ascending=[False, True]).reset_index(drop=True)

# Keep the extremes, remove the middle. Display what moved the most
# The 15 terms going UP the most, DOWN the most, comparing ONLY beginning month and ending month
BiggestMoversPositive = BiggestMoversFull.head(15)
BiggestMoversNegative = BiggestMoversFull.tail(15)

# Put UP and DOWN in one df
BiggestMoversRpt = BiggestMoversPositive.append(BiggestMoversNegative)


# Write out
writer = pd.ExcelWriter(reports + 'BiggestMoversRpt.xlsx')
BiggestMoversRpt.to_excel(writer,'BiggestMoversRpt', index=False)
writer.save()


# List out all dfs in memory
alldfs = [var for var in dir() if isinstance(eval(var), pd.core.frame.DataFrame)]
print(alldfs)

del [[BiggestMovers, BiggestMovers10, BiggestMovers11, BiggestMovers12, 
      BiggestMoversNegative, BiggestMoversPositive, bgtemp]]


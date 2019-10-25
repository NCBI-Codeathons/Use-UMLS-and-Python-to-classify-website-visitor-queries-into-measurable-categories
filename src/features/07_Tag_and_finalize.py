#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec 30 10:01:27 2018

@authors: dan.wendling@nih.gov,

Last modified: 2018-12-31

This script: Add columns to support reporting, such as the high-level 
SemanticGroup, plus columns that help to output the Semantic Types hierarchy.
Also add column CustomTopics and build opioids super-concept.
    

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

# Set working directory, read/write locations
# CHANGE AS NEEDED
os.chdir('/Users/wendlingd/Projects/webDS')
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/search/' # Save to disk as desired, to re-start easily
dataProcessed = 'data/processed/search/' # Ready to visualize
reports = 'reports/search/'

# Specific files you'll need
newlyProcessedRaw = dataInterim + 'logAfterStep4.xlsx' # processed log
CustomTags = dataMatchFiles + 'CustomTags.xlsx' # such as opioid constellation
SemanticNetworkReference = dataMatchFiles + 'SemanticNetworkReference.xlsx' # Semantic structure
SemanticSearchLogHistorical = dataProcessed + 'SemanticSearchLogHistorical.xlsx' # processed log

# Load the newly processed search log file
newlyProcessedRaw = pd.read_excel(newlyProcessedRaw)
newlyProcessedRaw.columns
'''
'Referrer', 'Query', 'Date', 'CountForPgDate', 'adjustedQueryTerm',
       'ProbablyMeantGSTerm', 'ui', 'preferredTerm', 'SemanticType'
'''

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


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec 30 10:01:27 2018

@authors: Dan Wendling

Last modified: 2020-02-19

--------------------------------------------------
 ** Semantic Search Analysis: Tag and Finalize **
--------------------------------------------------

** CHANGE FILE NAMING BEFORE RUNNING!! **


This script: Add columns that provide the top-down view in reporting, 
by cleaning up the Semantic Type assignments and adding the Semantic Group 
assignments. If you have Custom Topics you can add them here; we include 
custom tagging for opioids vaping. Follow the structure of the synonym
file CustomTags.xlsx to create your own custom topics.

INPUTS:
    - data/matchFiles/SemanticNetworkReference.xlsx
    - Most recently modified log; options include:
        data/interim/LogAfterJournals.xlsx - If you're coming from 01
        data/interim/LogAfterMetathesaurus.xlsx - If you're coming from 02
    - data/interim/01_CombinedSearchFullLog.xlsx - whole log
    - data/matchFiles/CustomTags.xlsx - If you have something specific to track

OUTPUTS:
    - data/processed/taggedLog-[TimePeriod].xlsx - Importable into Tableau, etc. but also summaries for Excel users
    - data/processed/BiggestMovers.xlsx - The source file for studying trends across time.
    - reports/index.html - Infographic / summary report for the newest processing


----------------
SCRIPT CONTENTS
----------------
1. Start-up / What to put into place, where
2. Open files, resolve SemTypes and SemGroups in a small df
3. Merge cleaned-up SemTypes, and SemGroups
4. Merge the new work into the original, full log
5. Add custom topics that you want to monitor
6. Create table BiggestMovers from PreferredTerm
7. Clean up and write out the report file, taggedLog.xlsx
8. Create BiggestMovers file
9. Create summary infographic
10. Optional / contingencies
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# import matplotlib.pylab as plt
# from matplotlib.colors import ListedColormap
# import matplotlib.patches as patches
import os
from datetime import datetime, timedelta
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


# --------------------------------------------------
# --------------------------------------------------
# Set your current time period
TimePeriod = '202001' # Use 6 digits, YYYYMM
HumanReadableDate = '{}-{}'.format(TimePeriod[0:4], TimePeriod[4:])
TotalSearchFreqCol = 'TotalSearchFreq' + TimePeriod
PercentShareCol = 'PercentShare' + TimePeriod
# --------------------------------------------------
# --------------------------------------------------


#%%
# ============================================================
# 2. Open files, resolve SemTypes and SemGroups in a small df
# ============================================================
'''
Should be refactored; seems to work for now on a minimal level.
'''

# -----------------------------------------------
# Bring in log
# -----------------------------------------------

# Bring in file - name depends on where you left off
# newTaggedLog = pd.read_excel(dataInterim + 'LogAfterJournals.xlsx') # Picking up after 01
newTaggedLog = pd.read_excel(dataInterim + 'LogAfterMetathesaurus.xlsx') # Picking up after 02
newTaggedLog.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType'
'''


# --------------------------------------------------
# Use SemanticReference to build a clean match list
# --------------------------------------------------

# Bring in
SemanticNetworkReference = pd.read_excel(dataMatchFiles + 'SemanticNetworkReference.xlsx')
SemanticNetworkReference.columns
'''
'SemanticTypeAbr', 'SemanticType', 'SemanticGroup', 'SemanticGroupAbr',
       'CustomTreeNumber', 'BranchPosition', 'UniqueID', 'SemanticGroupCode',
       'Definition', 'Examples', 'RelationName', 'SemTypeTreeNo', 'UsageNote',
       'NonHumanFlag', 'RecordType', 'TUI'
'''

# Reduce cols
SemMatch = SemanticNetworkReference[['SemanticType', 'SemanticGroup']]

# Split/explode columns into multiple rows
cleanSemTypeList = pd.DataFrame(SemMatch.SemanticType.str.split('|').tolist(), index=SemMatch.SemanticGroup).stack()
cleanSemTypeList = cleanSemTypeList.reset_index([0, 'SemanticGroup'])
cleanSemTypeList.columns = ['SemanticGroup', 'SemanticType']

# Only need the unique rows
cleanSemTypeList = cleanSemTypeList.drop_duplicates()
cleanSemTypeList = cleanSemTypeList.sort_values(by='SemanticType', ascending=True).reset_index(drop=True)
# Swap cols for easy viewing
cleanSemTypeList = cleanSemTypeList[['SemanticType', 'SemanticGroup']]


# SemGroups: 
cleanSemGroupList = SemMatch[['SemanticGroup']]
# Only need the unique rows
cleanSemGroupList = cleanSemGroupList.drop_duplicates()
cleanSemGroupList = cleanSemGroupList.sort_values(by='SemanticGroup', ascending=True).reset_index(drop=True)


# -----------------------------------------------------------------
# Dedupe SemTypes in uniqueSemTypesInNewLog using cleanSemTypeList
# -----------------------------------------------------------------

# Derive unique SemTypes - singles and combinations
uniqueSemTypesInNewLog = newTaggedLog['SemanticType'].value_counts().reset_index()
uniqueSemTypesInNewLog.rename(columns={'SemanticType': 'Count',
                                    'index': 'SemTypesUnmodified'}, inplace=True)

# Count - interesting to view but is not needed
uniqueSemTypesInNewLog.drop(['Count'], axis=1, inplace=True)

# Leave SemTypesUnmodified alone - it will be the col used to merge changes back in
uniqueSemTypesInNewLog['SemTypesCleanup'] = uniqueSemTypesInNewLog['SemTypesUnmodified']

# Add pipe to start and end for WHOLE-TERM mapping
uniqueSemTypesInNewLog['SemTypesCleanup'] = '|' + uniqueSemTypesInNewLog['SemTypesCleanup'] + '|'

# Build new SemType col and new groups col
uniqueSemTypesInNewLog['SemTypesDeduped'] = ''
uniqueSemTypesInNewLog['SemGroupsWithDupes'] = ''
uniqueSemTypesInNewLog['SemGroupsDeduped'] = ''

# The new col DedupedSemTypes dedupes and alphabetizes
for key, value in cleanSemTypeList.iterrows():
    currST = value['SemanticType']
    currSG = value['SemanticGroup']
    uniqueSemTypesInNewLog.loc[uniqueSemTypesInNewLog['SemTypesCleanup'].str.contains('\|' + currST + '\|', na=False), 'SemTypesDeduped'] = uniqueSemTypesInNewLog['SemTypesDeduped'] + '|' + currST
    uniqueSemTypesInNewLog.loc[uniqueSemTypesInNewLog['SemTypesCleanup'].str.contains('\|' + currST + '\|', na=False), 'SemGroupsWithDupes'] = uniqueSemTypesInNewLog['SemGroupsWithDupes'] + '|' + currSG


# -------------------------------------------------------------------
# Dedupe SemGroups in uniqueSemTypesInNewLog using cleanSemGroupList
# -------------------------------------------------------------------

'''
# Derive unique SemGroups - singles (and combinations if any)
uniqueSemGroupsWithDupes = uniqueSemTypesInNewLog['SemGroupsWithDupes'].value_counts().reset_index()
uniqueSemGroupsWithDupes.rename(columns={'SemGroupsWithDupes': 'Count',
                                    'index': 'SemGroupsWithDupes'}, inplace=True)
    
# Count - interesting to view but is not needed
uniqueSemGroupsWithDupes.drop(['Count'], axis=1, inplace=True)
'''

# Add pipe to end for WHOLE-TERM mapping
uniqueSemTypesInNewLog['SemGroupsWithDupes'] = uniqueSemTypesInNewLog['SemGroupsWithDupes'] + '|'

# Tag SemGroupsDeduped based on content in SemGroupsWithDupes
for key, value in cleanSemGroupList.iterrows():
    currSG = value['SemanticGroup']
    uniqueSemTypesInNewLog.loc[uniqueSemTypesInNewLog['SemGroupsWithDupes'].str.contains('\|' + currSG + '\|', na=False), 'SemGroupsDeduped'] = uniqueSemTypesInNewLog['SemGroupsDeduped'] + '|' + currSG

# Clean up
taggedUniques = uniqueSemTypesInNewLog[['SemTypesUnmodified', 'SemTypesDeduped', 'SemGroupsDeduped']]
taggedUniques.rename(columns={'SemGroupsDeduped': 'SemanticGroup'}, inplace=True)

# Remove start pipes
taggedUniques = taggedUniques.copy() # following line was generating 'copy of a slice' warning
taggedUniques['SemTypesDeduped'] = taggedUniques['SemTypesDeduped'].str.replace('^\|', '')
taggedUniques['SemanticGroup'] = taggedUniques['SemanticGroup'].str.replace('^\|', '')


#%%
# ===================================================================================
# 3. Merge cleaned-up SemTypes, and SemGroups to the log we've been matching against
# ===================================================================================
'''
Update the newly tagged log with clean broader categories.
'''

# Join
reportMerge1 = pd.merge(newTaggedLog, taggedUniques, how='left', left_on='SemanticType', right_on='SemTypesUnmodified')
reportMerge1.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType', 'SemTypesUnmodified', 'SemTypesDeduped',
       'SemanticGroup'
'''

# After eyeballing (if you want), drop SemanticType and SemTypesUnmodified and 
# change SemTypesDeduped to SemanticType
reportMerge1.drop(['SemanticType', 'SemTypesUnmodified'], axis=1, inplace=True)


# List out all dfs in memory
alldfs = [var for var in dir() if isinstance(eval(var), pd.core.frame.DataFrame)]
# print(alldfs)

# Remove unneeded
del [[SemMatch, SemanticNetworkReference, cleanSemGroupList, cleanSemTypeList, 
      newTaggedLog, taggedUniques, uniqueSemTypesInNewLog]]


#%%
# ==================================================
# 4. Merge the new work into the original, full log
# ==================================================
'''
The full log includes columns we dropped during tagging; let's bring what we know
back into the full log.

FIXME - In the CombinedFullLog-reportMerge1 merge, ~50 new rows are added on a
88,700 row file. Because this changes the counts, the rows should be looked at
and perhaps the same Query has been given different assignments; in that case
the assigments should be reconciled.
'''

# -------------------------
# Prep the new assignments
# -------------------------

# If SemGroup is null, drop the row
reportMerge1 = reportMerge1[reportMerge1['SemanticGroup'].notnull()]

# Avoid extra rows merging reportMerge1 - reduce to unique original Query-SemType rows
reportMerge1 = reportMerge1.drop_duplicates(subset=['Query', 'SemTypesDeduped'], keep='first')


# ---------------------
# Join to original log
# ---------------------

# Bring in the lightly modified original log
CombinedFullLog = pd.read_excel(dataInterim + '01_CombinedSearchFullLog.xlsx')
CombinedFullLog.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq', 'AdjustedQueryTerm'
'''

# Join on Query
reportMerge2 = pd.merge(CombinedFullLog, reportMerge1, how='left', left_on=['Query'], right_on=['Query'])
reportMerge2.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq_x', 'AdjustedQueryTerm_x', 'AdjustedQueryTerm_y',
       'TotalSearchFreq_y', 'ui', 'PreferredTerm', 'SemTypesDeduped',
       'SemanticGroup'
'''

# The _y cols, from reportMerge2, have less data, so drop
reportMerge2.drop(['TotalSearchFreq_y', 'AdjustedQueryTerm_y'], axis=1, inplace=True)

# Rename
reportMerge2.rename(columns={'TotalSearchFreq_x': 'TotalSearchFreq', 
                             'AdjustedQueryTerm_x': 'AdjustedQueryTerm',
                             'SemTypesDeduped': 'SemanticType'}, inplace=True)

reportMerge2.columns
'''
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq', 'AdjustedQueryTerm', 'ui', 'PreferredTerm',
       'SemanticType', 'SemanticGroup'
'''


# ---------------------
# Update cols
# ---------------------

# New col describes what the search location was
reportMerge2['LocationOfSearch'] = ''

# Clicks + TotalSearchFreq = GoogleAndLocal
reportMerge2['LocationOfSearch'] = np.where( ( (reportMerge2['Clicks'].notnull() ) & (reportMerge2['TotalUniqueSearches'].notnull() ) ), 'GoogleAndLocal', reportMerge2['LocationOfSearch'])
# TotalSearchFreq only = LocalResults
reportMerge2['LocationOfSearch'] = np.where( ( (reportMerge2['Clicks'].isnull() ) & (reportMerge2['TotalUniqueSearches'].notnull() ) ), 'LocalSearch', reportMerge2['LocationOfSearch'])
# Clicks only = GoogleResults
reportMerge2['LocationOfSearch'] = np.where( ( (reportMerge2['Clicks'].notnull() ) & (reportMerge2['TotalUniqueSearches'].isnull() ) ), 'GoogleSearch', reportMerge2['LocationOfSearch'])

# Change nan
reportMerge2['SemanticType'] = reportMerge2['SemanticType'].fillna('')
reportMerge2['SemanticGroup'] = reportMerge2['SemanticGroup'].fillna('')

# PreferredTerm
# If null or empty, bring over AdjustedQueryTerm
reportMerge2['PreferredTerm'] = reportMerge2['AdjustedQueryTerm'].where(reportMerge2['PreferredTerm'].isnull(), reportMerge2['PreferredTerm'])
reportMerge2.loc[reportMerge2['PreferredTerm'] == '', 'PreferredTerm'] = reportMerge2['AdjustedQueryTerm']
# Set all to string
reportMerge2['PreferredTerm'] = reportMerge2['PreferredTerm'].astype(str)


# Update col name for easy visualization within historical dataset
reportMerge2.rename(columns={'TotalSearchFreq': TotalSearchFreqCol}, inplace=True)
# For use below


# Free memory
del [[CombinedFullLog, reportMerge1]]


#%%
# ==============================================
# 5. Add custom topics that you want to monitor
# ==============================================
'''
Edit source file manually as desired; it's data/matchFiles/CustomTags.xlsx
Custom1: Opiods
Custom2: Vaping

Precise matching, not very useful; not forgiving of alternative spellings, etc.
logWithCustomTags = pd.merge(newlyProcessedRaw, CustomTags, how='left', on='adjustedQueryTerm')

# FIXME - Below uses 'word stems' in CustomTagsFile, but is awkward.

Adding new custom tags? Also update the rest of this script such as 'Reduce and reorder',
writing out to Excel, etc.

'''

# Load custom tagging file
CustomTags = pd.read_excel(dataMatchFiles + 'CustomTags.xlsx')
CustomTags.columns
'''
'ConceptID', 'ConceptName', 'AdjustedQueryTerm'
'''


# -------
# 1. Opiods
# -------

reportMerge2['CustomTag1'] = ''

custom1 = CustomTags[CustomTags['ConceptID'] == 1]

# The new col DedupedSemTypes dedupes and alphabetizes
for key, value in custom1.iterrows():
    currTerm = value['AdjustedQueryTerm']
    currConceptName = value['ConceptName']
    reportMerge2.loc[reportMerge2['AdjustedQueryTerm'].str.contains(currTerm, na=False), 'CustomTag1'] = currConceptName


# -------
# 2. Vaping
# -------

reportMerge2['CustomTag2'] = ''

custom2 = CustomTags[CustomTags['ConceptID'] == 2]

# The new col DedupedSemTypes dedupes and alphabetizes
for key, value in custom2.iterrows():
    currTerm = value['AdjustedQueryTerm']
    currConceptName = value['ConceptName']
    reportMerge2.loc[reportMerge2['AdjustedQueryTerm'].str.contains(currTerm, na=False), 'CustomTag2'] = currConceptName


# ---------------
# 3. Coronavirus
# ---------------

reportMerge2['CustomTag3'] = ''

custom3 = CustomTags[CustomTags['ConceptID'] == 3]

# The new col DedupedSemTypes dedupes and alphabetizes
for key, value in custom3.iterrows():
    currTerm = value['AdjustedQueryTerm']
    currConceptName = value['ConceptName']
    reportMerge2.loc[reportMerge2['AdjustedQueryTerm'].str.contains(currTerm, na=False), 'CustomTag3'] = currConceptName


# Need to reduce the breadth of this one; eyeballing, then deciding

# Keep generic 'virus' items, but untag the items mentioning other viruses
listToRemove = ('adeno', 'african fever', 'alzheimer', 'arbo', 'arthritogenic', 
                'barr', 'birna', 'blv', 'bovine', 'carcinogen', 'circo', 
                'citomega', 'crypto', 'cyano', 'cytomega', 'dengue', 'dwarf', 
                'ebola', 'encephalitis', 'entero', 'flu', 'grapevine', 'hanta', 
                'heartland', 'henta', 'hepatitis', 'herpes', 'hiv', 'hpv', 'immunodeficiency',
                'marburg',
                'influenza', 'lassa', 'leukemia', 'mancha blanca', 'mayaro', 
                'measles', 'mosaic', 'mosaik', 'mumps', 'myco', 'nephritis', 'nilo',
                'noro', 'oncogenic', 'ophiov', 'orthotospo', 'papilloma', 'papiloma',
                'papiloma', 'parvo', 'polio', 'polyhedrosis', 'potato', 'provirus', 
                'rabies', 'rhabda', 'rhino', 'rota', 'salmon', 'scarlet', 'shingles', 
                'smallpox', 'swine', 'syncytial', 'tomato', 'west nile', 
                'westnile', 'zika', 'zita', 'zoster')
reportMerge2.loc[reportMerge2['AdjustedQueryTerm'].str.contains('|'.join(listToRemove), na=False), 'CustomTag3'] = ''

# Remove other false positives
listToRemove = ('alzhiemers', 'alzeimers', 'alzhimers', 'alheimers', 'alsheimers', 'european respiratory journal',
                'opiod', 'opioid', 'polymers', 'vaping', 'mononucleosis', 'alkalosis', 'embalmers monthly')
reportMerge2.loc[reportMerge2['AdjustedQueryTerm'].str.contains('|'.join(listToRemove), na=False), 'CustomTag3'] = ''


'''
corona = reportMerge2[reportMerge2.CustomTag3.str.contains(currConceptName) == True]

coronaCounts = corona['AdjustedQueryTerm'].value_counts().reset_index()
coronaCounts.columns = ['AdjustedQueryTerm', 'Counts']

coronaTest = coronaCounts[coronaCounts.AdjustedQueryTerm.str.contains("virus") == True]
coronaTest.head(60)
'''


# Free memory
del [[CustomTags]]


#%%
# =================================================
# 6. Create table BiggestMovers from PreferredTerm
# =================================================
'''
BiggestMovers.xlsx is the source file for studying trends across time. Some 
of the most useful reporting among datasets (such as, one per month) will be, 
Within bucket x, what are the biggest movers? What are people searching for 
_more_, and what are people searching for _less_, over time? We will use 
unique PreferredTerm for this.

Removed  'LocationOfSearch', dilutes the counts...
'''

# New df
BiggestMovers = reportMerge2[['PreferredTerm', 'SemanticType', 'SemanticGroup', TotalSearchFreqCol]] 

# Groupby
BiggestMovers = BiggestMovers.groupby(['PreferredTerm', 'SemanticType', 'SemanticGroup'])[TotalSearchFreqCol].sum().reset_index()
BiggestMovers = BiggestMovers.sort_values(by=TotalSearchFreqCol, ascending=False).reset_index(drop=True)

# Derive PercentShare of search for each unique PreferredTerm
BiggestMovers[PercentShareCol] = ''
BiggestMovers[PercentShareCol] = round(BiggestMovers[TotalSearchFreqCol] / BiggestMovers[TotalSearchFreqCol].sum() * 100, 2)

# Re-arrange
BiggestMovers = BiggestMovers[['PreferredTerm', 'SemanticType', 'SemanticGroup', TotalSearchFreqCol, PercentShareCol]]


#%%
# ==========================================================
# 7. Clean up and write out the report file, taggedLog.xlsx
# ==========================================================

reportMerge2.columns
'''
(example)
'Query', 'Clicks', 'Impressions', 'CTR', 'AveragePosition',
       'TotalUniqueSearches', 'ResultsPVSearch', 'PercentSearchExits',
       'PercentSearchRefinements', 'TimeAfterSearch', 'AvgSearchDepth',
       'TotalSearchFreq201912', 'AdjustedQueryTerm', 'ui', 'PreferredTerm',
       'SemanticType', 'SemanticGroup', 'LocationOfSearch', 'CustomTag1',
       'CustomTag2', 'CustomTag3'
'''

# Reduce and reorder
taggedLog = reportMerge2[['Query', 'AdjustedQueryTerm', TotalSearchFreqCol, 'TotalUniqueSearches', 
                          'SemanticGroup', 'SemanticType', 'PreferredTerm', 'LocationOfSearch', 
                          'Impressions', 'Clicks', 'CTR', 'AveragePosition', 'ResultsPVSearch', 
                          'PercentSearchExits', 'PercentSearchRefinements', 'TimeAfterSearch', 
                          'AvgSearchDepth', 'ui', 'CustomTag1', 'CustomTag2', 'CustomTag3']]

# Update unassigned rows to 'Unassigned'
taggedLog['PreferredTerm'] = taggedLog['PreferredTerm'].str.replace('^$', 'Unassigned')
taggedLog['SemanticType'] = taggedLog['SemanticType'].str.replace('^$', 'Unassigned')
taggedLog['SemanticGroup'] = taggedLog['SemanticGroup'].str.replace('^$', 'Unassigned')

# Cols probably will not be null, but...
taggedLog.loc[taggedLog.PreferredTerm.isnull(), 'PreferredTerm'] = 'Unassigned'
taggedLog.loc[taggedLog.SemanticType.isnull(), 'SemanticType'] = 'Unassigned'
taggedLog.loc[taggedLog.SemanticGroup.isnull(), 'SemanticGroup'] = 'Unassigned'

# If col is nan (should never be nan), remove row
taggedLog = taggedLog.dropna(subset=[TotalSearchFreqCol])

# Create df BigMoversQueries for Tableau drill-down from BiggestMovers 
BigMoversQueryList = taggedLog[[TotalSearchFreqCol, 'PreferredTerm', 'Query']]


# -------------
# How we doin?
# -------------

# Total queries in log
SearchesRepresentedTot = taggedLog[TotalSearchFreqCol].sum().astype(int)
SearchesAssignedTot = taggedLog.loc[taggedLog['SemanticType'] != '']
SearchesAssignedTot = SearchesAssignedTot[TotalSearchFreqCol].sum().astype(int)
SearchesAssignedPercent = (SearchesAssignedTot / SearchesRepresentedTot * 100).astype(int)
# PercentOfSearchesUnAssigned = 100 - PercentOfSearchesAssigned
RowsTot = len(taggedLog)
RowsAssignedCnt = (taggedLog['SemanticType'].values != '').sum() # .isnull().sum()
# RowsUnassignedCnt = TotRows - RowsAssigned
RowsAssignedPercent = (RowsAssignedCnt / RowsTot * 100).astype(int)

# Report on counts by source
totPerLocation = reportMerge2.groupby(['LocationOfSearch'])['TotalUniqueSearches'].sum().sort_values(ascending=False).reset_index()


# print("\nTop Semantic Types\n{}".format(taggedLog['SemanticType'].value_counts().head(10)))
print("\n===========================================================\n ** taggedLog: {}% of total search volume tagged **\n===========================================================\n\n{:,} of {:,} searches ({}%) assigned;\n{:,} of {:,} rows ({}%) assigned\n".format(SearchesAssignedPercent, SearchesAssignedTot, SearchesRepresentedTot, SearchesAssignedPercent, RowsAssignedCnt, RowsTot, RowsAssignedPercent))

# ------------------------------
# Create reports for Excel file
# ------------------------------

# Summarize the work
LocationOfSearchSum = taggedLog.groupby(['LocationOfSearch'])[TotalSearchFreqCol].sum().sort_values(ascending=False).reset_index()
SemGroupsSum = taggedLog.groupby(['SemanticGroup'])[TotalSearchFreqCol].sum().sort_values(ascending=False).reset_index()
SemTypesSum = taggedLog.groupby(['SemanticType'])[TotalSearchFreqCol].sum().sort_values(ascending=False).reset_index()
AdjustedQueryTermTop200 = taggedLog.groupby(['AdjustedQueryTerm'])[TotalSearchFreqCol].sum().sort_values(ascending=False).reset_index().head(200)
PreferredTermTop200 = taggedLog.groupby(['PreferredTerm'])[TotalSearchFreqCol].sum().sort_values(ascending=False).reset_index().head(200)
# Custom
OpioidSearches = taggedLog.loc[taggedLog['CustomTag1'] != '']
VapingSearches = taggedLog.loc[taggedLog['CustomTag2'] != '']
CoronaVirusSearches = taggedLog.loc[taggedLog['CustomTag3'] != '']


# write out
writer = pd.ExcelWriter(reports + 'taggedLog' + TimePeriod + '.xlsx')
taggedLog.to_excel(writer,'taggedLog', index=False)
BiggestMovers.to_excel(writer,'BiggestMovers', index=False)
LocationOfSearchSum.to_excel(writer,'LocationOfSearchSum', index=False)
SemGroupsSum.to_excel(writer,'SemGroupsSum', index=False)
SemTypesSum.to_excel(writer,'SemTypesSum', index=False)
AdjustedQueryTermTop200.to_excel(writer,'AdjustedQueryTermTop200', index=False)
PreferredTermTop200.to_excel(writer,'PreferredTermTop200', index=False)
OpioidSearches.to_excel(writer,'OpioidSearches', index=False)
VapingSearches.to_excel(writer,'VapingSearches', index=False)
CoronaVirusSearches.to_excel(writer,'CoronaVirusSearches', index=False)
writer.save()

# Biggest movers by itself
writer = pd.ExcelWriter(reports + 'BiggestMovers' + TimePeriod + '.xlsx')
BiggestMovers.to_excel(writer,'BiggestMovers', index=False)
BigMoversQueryList.to_excel(writer,'BigMoversQueryList', index=False)
writer.save()


print("\n===============================================================\n ** Script 05 done! **  Results are at:\n  - data/processed/taggedLog{}.xlsx\n  - data/processed/BiggestMovers{}.xlsx\n===============================================================\n\n".format(TimePeriod, TimePeriod))
for key, value in totPerLocation.iterrows():
    print("| {} | {:,} |".format(value[0], value[1]))


'''
# List out all dfs in memorys
alldfs = [var for var in dir() if isinstance(eval(var), pd.core.frame.DataFrame)]
print(alldfs)
'''

del [[reportMerge2]]

# custom1, custom2, custom3, 
# OpioidSearches, PreferredTermTop200, SemGroupsSum, SemTypesSum, VapingSearches, taggedLog



#%%
# =================================================
# 9. Create summary infographic
# =================================================

'''
Modeled after GSA's https://blog.usa.gov/top-google-queries-on-usa.gov-for-2019-0-0

Started with colors from Tableau "colorblind" palette but made changes

    #164581 - Blue from GSA, darker than Tableau
    #C85200 - Dark orange
    #57606C - Dark gray
    #884483 - Purple (from GSA infographic, not Tableau)
    #FC7D0B - Orange
    
    #E7E8E8 - Gray, GSA, push to background, for first chart, #6-end

    #1170AA - Darkest blue 
    #7B848F - Dark gray
    #A3ACB9 - Light gray
    #A3CCE9 - light blue
    #FFBC79 - Lightest orange
    #5FA2CE - Midrange blue
    
'''

# ----------------------------------------
# Horizontal bar - Semantic Group summary
# ----------------------------------------

SemGroupsSumTop20 = SemGroupsSum.copy().head(20)
SemGroupsSumTop20.set_index('SemanticGroup', inplace=True)

ax = SemGroupsSumTop20.plot(kind='barh', figsize=(10,8), color="steelblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.suptitle(HumanReadableDate + ': Top 20 Most-Popular Semantic Groups', fontsize=16, fontweight='bold')
ax.set_title("The highest-level summary, representing {:,} total queries".format(SearchesRepresentedTot), fontsize=10)
ax.set_xlabel("Queries", fontsize=9);
# set individual bar labels using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.2, i.get_y()+.43, "{:,}".format(i.get_width()), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
ax.get_legend().remove()
plt.gcf().subplots_adjust(left=0.4)

plt.savefig(reports + 'SG0-Top15SemanticGroups' + HumanReadableDate + '.png')



# ----------------------------------------------------------------
# Horizontal bars - loop over Semantic Types by the Sem Group sum
# ----------------------------------------------------------------
'''
https://stackoverflow.com/questions/21800004/pandas-for-loop-on-a-group-by

https://stackoverflow.com/questions/19189488/use-a-loop-to-plot-n-charts-python
'''
taggedLog.columns
'''
'Query', 'AdjustedQueryTerm', 'TotalSearchFreq202001',
       'TotalUniqueSearches', 'SemanticGroup', 'SemanticType', 'PreferredTerm',
       'LocationOfSearch', 'Impressions', 'Clicks', 'CTR', 'AveragePosition',
       'ResultsPVSearch', 'PercentSearchExits', 'PercentSearchRefinements',
       'TimeAfterSearch', 'AvgSearchDepth', 'ui', 'CustomTag1', 'CustomTag2',
       'CustomTag3'
'''

# Create list of the top 5 groups, excluding Unassigned, Bibliographic Entity, Numeric ID
TopGroups = SemGroupsSum[SemGroupsSum.SemanticGroup.str.contains("Unassigned") | SemGroupsSum.SemanticGroup.str.contains("Bibliographic Entity") | SemGroupsSum.SemanticGroup.str.contains("Numeric ID") == False]
TopGroups = TopGroups.reset_index(drop=True)
TopGroups = TopGroups.head(5).reset_index()
TopGroups['index'] = TopGroups['index'] + 1
TopGroups['index'] = TopGroups['index'].astype(str)
# Assign colors
TopGroups['color'] = ''
TopGroups.loc[TopGroups['index'].str.contains('1', na=False), 'color'] = '#164581' # Blue from GSA's, darker than Tableau
TopGroups.loc[TopGroups['index'].str.contains('2', na=False), 'color'] = '#C85200' # Dark orange
TopGroups.loc[TopGroups['index'].str.contains('3', na=False), 'color'] = '#884483' # Purple; from GSA, darker than Tableau
TopGroups.loc[TopGroups['index'].str.contains('4', na=False), 'color'] = '#57606C' # Dark gray
TopGroups.loc[TopGroups['index'].str.contains('5', na=False), 'color'] = '#5FA2CE' # Midrange blue
# else: color = 'E7E8E8'


# Within the top 5 SemGroups, locate the highest SemType count so we can lock x axis
# to enforce visual comparisons across charts
# Get all rows for the top 5
TopGroupsList = TopGroups['SemanticGroup'].values.tolist()

TopTypesRows = taggedLog[taggedLog['SemanticGroup'].isin(TopGroupsList)]
TopTypesSum = TopTypesRows.groupby(['SemanticGroup', 'SemanticType'])['TotalSearchFreq' + TimePeriod].sum().sort_values(ascending=False).reset_index()
TopTypeMax = TopTypesSum['TotalSearchFreq' + TimePeriod].max()

htmlNames = ['SG0-Top15SemanticGroups' + HumanReadableDate + '.png']


# viz ------------------------------------
for key, value in TopGroups.iterrows():
    currSG = value['SemanticGroup']
    currKey = value['index']
    currTotFreq = value['TotalSearchFreq' + TimePeriod]
    currPercent = round(currTotFreq / SearchesRepresentedTot * 100, 1)
    currColor = value['color']
    currSGRows = taggedLog[taggedLog.SemanticGroup.str.contains(currSG) == True]
    TypesByGroup = currSGRows.groupby(['SemanticType'])['TotalSearchFreq' + TimePeriod].sum().sort_values(ascending=False)
    TypesByGroup = TypesByGroup.head(5)
    # Prepare to lock each chart's x axis to the length of the biggerst SemType count
    plt.figure()
    ax = TypesByGroup.plot(kind='barh', figsize=(10,2.8), color=currColor, fontsize=10);
    ax.set_alpha(0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    suptitle = plt.suptitle("{} ({:,} searches / {}% of total)".format(currSG, currTotFreq, currPercent), fontsize=15, fontweight='bold', color='white', backgroundcolor=currColor)
    suptitle._bbox_patch._mutation_aspect = 0.01
    suptitle.get_bbox_patch().set_boxstyle("square", pad=20) # pad is horizontal
    # ax.set_title("Mid-level (Semantic Types) summary, representing {:,} queries".format(SearchesRepresentedTot), fontsize=10)
    # ax.set_title("Title", bbox=dict(facecolor='black', alpha=0.5))
    # Lock axis to highest count to enforce visual comparisons between charts
    ax.set_autoscalex_on(False)
    ax.set_xlim([0,TopTypeMax])
    ax.yaxis.label.set_visible(False)
    # ax.set_xlabel("Queries", fontsize=9);
    # set individual bar labels using above list
    for i in ax.patches:
        # get_width pulls left or right; get_y pushes up or down
        ax.text(i.get_width()+.1, i.get_y()+.38, "{:,}".format(i.get_width()), fontsize=10, color='dimgrey')
    # invert for largest on top 
    ax.invert_yaxis()
    # ax.get_legend().remove()
    plt.gcf().subplots_adjust(left=0.4)
    plt.show()
    # Remove slashes
    currSG = currSG.replace("/", "-")
    filename = 'SG' + currKey + '-' + currSG + '-Top_5_SemTypes.png'
    htmlNames.append(filename)
    plt.savefig(reports + filename)


# -------------------------
# Write to HTML
# -------------------------

htmlWrapSum = ['<html>\n<head>\n<title>Most-Popular Searches</title>\n<style>\n \
               img {padding-top:1rem;}\nbody {font-family: Arial, Helvetica, sans-serif; \
               margin-left: 1.5em;}\n</style>\n</head>\n<body>\n \
               <h1 style="margin-bottom:0;">Our Most-Popular Searches for ' + HumanReadableDate + '</h1>\n\n \
               <p style="margin-top:0.5em;max-width:63em;">From google.com search results \
               where the searcher landed within our site, AND from our site search. \
               Six charts: <strong>Semantic Group</strong> counts, then the <strong>Top 5 \
               Semantic Types</strong> (sub-categories) for 5 of the top groups. Notes: \
               Three categories have no sub-categories: Unassigned, Bibliographic Entity, and Numeric ID. \
               In &quot;Our Programs/Products/Services/People,&quot; items are tagged \
               to the narrowest sub-category possible; cross-organizational items are \
               tagged with broader terms. Many visitor queries require multiple \
               category assignments. Tagged log file and summary spreadsheets: <a href="taggedLog' 
               + TimePeriod + '.xlsx">taggedLog' + TimePeriod + '.xlsx.</a></p>\n\n']

for i in htmlNames:
    item = '<img src="' + i + '" alt="summarized in spreadsheet">\n'
    htmlWrapSum.append(item)

# htmlWrapSum.append(htmlNames.to_html(index=False))
htmlWrapSum.append('\n</body>\n</html>')

htmlSum = ''.join(htmlWrapSum)
htmlFile = open(reports + 'index.html', 'w')
htmlFile.write(htmlSum)
htmlFile.close()

# Report out
print("\n\n=====================================================================\n** Script 05 done **  Summary report available at /report/index.html\n=====================================================================\n".format(SearchesAssignedPercent))


#%%
# ============================
# 10. Optional / contingencies
# ============================

"""
# Eyeball sample
viewRows = BGTEMP[26000:26800]


# From https://github.com/NCBI-Hackathons/Semantic-search-log-analysis-pipeline/blob/master/afterGSprocessing.py,
# d = data.groupby('SemanticGroup').resample('1H').count()['SemanticGroup'].unstack().T


# Free memory
del [[BiggestMovers, BiggestMovers10, BiggestMovers11]]

"""




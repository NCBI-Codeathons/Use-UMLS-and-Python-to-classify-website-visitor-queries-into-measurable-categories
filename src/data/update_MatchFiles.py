#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov  9 21:23:40 2019

@authors: dan.wendling@nih.gov

Last modified: 2019-11-11

------------------------------------------------------
 ** Semantic Search Analysis: Maintain Match Files **
------------------------------------------------------

Update things like removing dupes that sneak in over time, punctuation, resorting...

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
import re
import string
import requests
import json
import lxml.html as lh
from lxml.html import fromstring

# Set working directory and directories for read/write
home_folder = os.path.expanduser('~')
os.chdir(home_folder + '/Projects/classifysearches')

dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required


#%%
# ========================================================================
# To update SiteSpecificMatches.xlsx, such as punctuation, removing dupes
# ========================================================================

SiteSpecificMatches = pd.read_excel('data/matchFiles/SiteSpecificMatches.xlsx')

# Replace hyphen with space because the below would replace with nothing
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('-', ' ')
# Remove https:// if used
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('http://', '')
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('https://', '')

# Drop nulls
SiteSpecificMatches = SiteSpecificMatches.dropna(subset=['AdjustedQueryTerm'])

# Remove all chars except a-zA-Z0-9 and leave foreign chars alone
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace(r'[^\w\s]+', '')

# Removing punct may mean that some entries will be duplicates
SiteSpecificMatches = SiteSpecificMatches.drop_duplicates(subset=['AdjustedQueryTerm'])

# Sort for easier editing
SiteSpecificMatches = SiteSpecificMatches.sort_values(by=['PreferredTerm', 'AdjustedQueryTerm'], ascending=[True, True])

# Write out
writer = pd.ExcelWriter('data/matchFiles/SiteSpecificMatches.xlsx')
SiteSpecificMatches.to_excel(writer,'SiteSpecificMatches', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%
# ================================================================
# To update PastMatches.xlsx, such as punctuation, removing dupes
# ================================================================

PastMatches = pd.read_excel('data/matchFiles/PastMatches.xlsx')

# Replace hyphen with space because the below would replace with nothing
PastMatches['AdjustedQueryTerm'] = PastMatches['AdjustedQueryTerm'].str.replace('-', ' ')
# Remove https:// if used
PastMatches['AdjustedQueryTerm'] = PastMatches['AdjustedQueryTerm'].str.replace('http://', '')
PastMatches['AdjustedQueryTerm'] = PastMatches['AdjustedQueryTerm'].str.replace('https://', '')

# Drop nulls
PastMatches = PastMatches.dropna(subset=['AdjustedQueryTerm'])

# Remove all chars except a-zA-Z0-9 and leave foreign chars alone
PastMatches['AdjustedQueryTerm'] = PastMatches['AdjustedQueryTerm'].str.replace(r'[^\w\s]+', '')

# Removing punct may mean that some entries will be duplicates
PastMatches = PastMatches.drop_duplicates(subset=['AdjustedQueryTerm'])

# Merge PastMatches with SiteSpecificMatches
PastMatches = pd.merge(PastMatches, SiteSpecificMatches, indicator=True, how='outer')
# Drop rows of all dupes in AdjustedQuery col
PastMatches = PastMatches.drop_duplicates(subset=['AdjustedQueryTerm'], keep=False)
# Reduce to only the rows that came from PastMatches
PastMatches = PastMatches[PastMatches._merge.str.contains("left_only") == True]
# Remove unneeded col
PastMatches.drop('_merge', axis=1, inplace=True)

# Sort for easier editing
PastMatches = PastMatches.sort_values(by=['PreferredTerm', 'AdjustedQueryTerm'], ascending=[True, True])


# Write out
writer = pd.ExcelWriter('data/matchFiles/PastMatches.xlsx')
PastMatches.to_excel(writer,'PastMatches', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%
# ============================================================
# To update UmlsMesh.csv, such as punctuation, removing dupes
# ============================================================

UmlsMesh = pd.read_csv('data/matchFiles/UmlsMesh.csv', sep='|') 

# Replace hyphen with space because the below would replace with nothing
UmlsMesh['AdjustedQueryTerm'] = UmlsMesh['AdjustedQueryTerm'].str.replace('-', ' ')
# Remove https:// if used
UmlsMesh['AdjustedQueryTerm'] = UmlsMesh['AdjustedQueryTerm'].str.replace('http://', '')
UmlsMesh['AdjustedQueryTerm'] = UmlsMesh['AdjustedQueryTerm'].str.replace('https://', '')

# Drop nulls
UmlsMesh = UmlsMesh.dropna(subset=['AdjustedQueryTerm'])

# Remove all chars except a-zA-Z0-9 and leave foreign chars alone
UmlsMesh['AdjustedQueryTerm'] = UmlsMesh['AdjustedQueryTerm'].str.replace(r'[^\w\s]+', '')

# Removing dupes if removing punct created them
UmlsMesh = UmlsMesh.drop_duplicates(subset=['AdjustedQueryTerm'])

# Sort for easier editing
UmlsMesh = UmlsMesh.sort_values(by=['PreferredTerm', 'AdjustedQueryTerm'], ascending=[True, True])

# Write out
UmlsMesh.to_csv('data/matchFiles/UmlsMesh.csv', 
                               sep='|', encoding='utf-8',
                               columns=['AdjustedQueryTerm', 'PreferredTerm', 'SemanticType', 'wordCount', 'ui', 'LAT', 'SAB'],
                               index=False)



#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 26 12:48:32 2019

@author: wendlingd@nih.gov

Last modified: 2019-10-28

This script: Convert NLM journals list match list by title, two official 
abbreviation formats, or ISSNs for print or online versions of the publication. 
For sites where many people search for journal info.

Assigns the full version of the title as "PreferredTitle" and pivots the other
data around it. Steps include: 
    1. Download TXT file from https://www.nlm.nih.gov/bsd/serfile_addedinfo.html
    2. Open in text editor; run two RegEx find and replace:
        F: \n
        R:  | 

        F: \| -------------------------------------------------------- \|
        R: \n
    3. Remove the last pipe in the file to match other rows.
    4. Copy column names into top row:
            JrId|JournalTitle|MedAbbr|ISSN (Print)|ISSN (Online)|IsoAbbr|NlmId
    3. Run this script.


--------------------------
INPUT FILES YOU WILL NEED
--------------------------

data/external/J_Medline.txt (see above)


----------------------
OUTPUT OF THIS SCRIPT
----------------------

data/matchfiles/JournalMatches.csv
"""

import pandas as pd
import os

# Set working directory and directories for read/write
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')


#%%

journals2df = pd.read_csv('data/external/J_Medline.txt', sep='|', encoding="utf-8", skipinitialspace=True)
#  names=['JrId', 'JournalTitle', 'MedAbbr', 'IssnPrint', 'IssnOnline', 'IsoAbbr', 'NlmId']
journals2df.columns
'''
'JrId', 'JournalTitle', 'MedAbbr', 'ISSN (Print)', 'ISSN (Online)',
       'IsoAbbr', 'NlmId'
'''

# Remove col name
journals2df['JournalTitle'] = journals2df['JournalTitle'].str.replace('JournalTitle: ', '')
journals2df['MedAbbr'] = journals2df['MedAbbr'].str.replace('MedAbbr: ', '')
journals2df['ISSN (Print)'] = journals2df['ISSN (Print)'].str.replace('ISSN \(Print\): ', '')
journals2df['ISSN (Online)'] = journals2df['ISSN (Online)'].str.replace('ISSN \(Online\):', '')
journals2df['IsoAbbr'] = journals2df['IsoAbbr'].str.replace('IsoAbbr: ', '')
journals2df['NlmId'] = journals2df['NlmId'].str.replace('NlmId: ', '')

# Don't need col
journals2df.drop('JrId', axis=1, inplace=True)

# Rename
journals2df.rename(columns={'ISSN (Print)': 'IssnPrint',
                                     'ISSN (Online)': 'IssnOnline'}, inplace=True)

# Check results if you want
# lookIt = journals2df.iloc[0:100]

# Dupe off title into PreferredTerm
journals2df['PreferredTerm'] = journals2df['JournalTitle']

# Pivot around 2 cols
journalList = pd.melt(journals2df, id_vars=['PreferredTerm', 'NlmId'], 
                      value_vars=['JournalTitle', 'MedAbbr', 'IssnPrint', 'IssnOnline', 'IsoAbbr'])    

# Adjust cols
journalList.rename(columns={'value': 'AdjustedQueryTerm', 'NlmId': 'ui'}, inplace=True)
journalList.drop('variable', axis=1, inplace=True)
journalList['SemanticType'] = 'Journal Title'
journalList = journalList[['AdjustedQueryTerm', 'PreferredTerm', 'SemanticType', 'ui']]

# Drop nan rows
journalList = journalList.dropna()

# The empty cols have been pivoted; drop empty AdjustedQueryTerm (has 2 or 1 space)
journalList = journalList[journalList.AdjustedQueryTerm.str.contains("^  $") == False]
journalList = journalList[journalList.AdjustedQueryTerm.str.contains("^ $") == False]

# Replace hyphen with space because the below would replace with nothing
journalList['AdjustedQueryTerm'] = journalList['AdjustedQueryTerm'].str.replace('-', ' ')

# Remove all chars except a-zA-Z0-9 and leave foreign chars alone
journalList['AdjustedQueryTerm'] = journalList['AdjustedQueryTerm'].str.replace(r'[^\w\s]+', '')

# Some entries have a leading space
journalList['AdjustedQueryTerm'] = journalList['AdjustedQueryTerm'].str.strip()

# Drop dupe rows; source lists two abbreviations per entry - some are the same
journalList = journalList.drop_duplicates(subset=['AdjustedQueryTerm'], keep='first')

# Remove leading "The "
journalList['AdjustedQueryTerm'] = journalList['AdjustedQueryTerm'].str.replace('^The ', '')

# Sort so easier to understand when a person looks at the file
journalList = journalList.sort_values(by='PreferredTerm', ascending=True).reset_index(drop=True)


# Write out
journalList.to_csv('data/matchfiles/JournalMatches.txt', encoding='utf-8', sep='|', index=False)



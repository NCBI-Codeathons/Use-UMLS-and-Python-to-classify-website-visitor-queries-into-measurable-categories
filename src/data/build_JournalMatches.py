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
        F: \n(.*): 
        R: |
        
        F: --------------------------------------------------------\|
        R: 
        And then update top and bottom of file so they match other rows.
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



journals2df = pd.read_csv('J_Medline.txt', sep='|',
                          names=['JrId', 'JournalTitle', 'MedAbbr', 'IssnPrint', 'IssnOnline', 'IsoAbbr', 'NlmId'])

# Don't need col
journals2df.drop('JrId', axis=1, inplace=True)

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

# Drop dupe rows; source lists two abbreviations per entry - some are the same
journalList = journalList.drop_duplicates(keep='last')

# Sort so easier to understand when a person looks at the file
journalList = journalList.sort_values(by='PreferredTerm', ascending=True).reset_index(drop=True)

# Write out
journalList.to_csv('data/matchfiles/JournalMatches.csv', encoding='utf-8', index=False)



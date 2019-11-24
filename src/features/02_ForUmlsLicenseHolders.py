#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
Created on Thu Jun 28 15:33:33 2018

@authors: dan.wendling@nih.gov

Last modified: 2019-11-24

---------------------------------------------------
 ** Semantic Search Analysis: Metathesaurus API **
---------------------------------------------------

 - For UMLS license holders -
 
This script: Run unmatched search queries against the UMLS Metathesaurus https
API, which has many vocabularies and a lexical toolset specific to biomedicine. 
This script uses normalized string matching, which is conservative enough to 
assume that almost all the matches returned, are correct. Some clean-up will 
be needed later in your PastMatches file.

You can skip this step if you don't have a (free) UMLS license and don't 
want to get one now. This step can be integrated later if you find you 
aren't satisfied with the percentage of search volume you are able to tag 
(the pilot project aimed for 80 percent).


----------------
SCRIPT CONTENTS
----------------

1. Start-up
2. Match to foreign terms list
3. Set an appropriate dataset size for API, and run
4. Integrate Metathesaurus data
5. Append new API results to PastMatches

"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
# Re-starting?
UnmatchedAfterJournals = pd.read_excel('01_Import-transform_files/UnmatchedAfterJournals.xlsx')
'''

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import pie, axis, show
import requests
import json
import os
import lxml.html as lh
from lxml.html import fromstring
# import hunspell
# https://anaconda.org/conda-forge/hunspell
# hunspell doc: http://hunspell.github.io/
import numpy as np
# import time


# Set working directory, read/write locations
# CHANGE AS NEEDED
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')

dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
reports = 'reports/' # Where to write images, etc., to

# Specific files you'll need. NOTE - Removes df if your first session is still active
UnmatchedAfterJournals = dataInterim + 'UnmatchedAfterJournals.xlsx' # newest log
PastMatches = dataMatchFiles + 'PastMatches.xlsx' # historical file of vetted successful matches
LogAfterJournals = dataInterim + 'LogAfterJournals.xlsx'

# HighConfidenceGuesses = dataMatchFiles + 'HighConfidenceGuesses.xlsx' # Automatically matched even though a few characters off
# QuirkyMatches = dataMatchFiles + 'QuirkyMatches.xlsx' # Human-chosen terms that might be misspelled, foreign, etc.

# djangoDir = '_django/loganalysis/'


# Get local API key (after you have set it)
def get_umls_api_key(filename=None):
    key = os.environ.get('UMLS_API_KEY', None)
    if key is not None:
        return key
    if filename is None:
          path = os.environ.get('HOME', None)
          if path is None:
               path = os.environ.get('USERPROFILE', None)
          if path is None:
               path = '.'
          filename = os.path.join(path, '.umls_api_key')
    with open(filename, 'r') as f:
           key = f.readline().strip()
    return key

myUTSAPIkey = get_umls_api_key()


# UMLS Terminology Services (UTS): Generate a one-day Ticket-Granting-Ticket (TGT)
tgt = requests.post('https://utslogin.nlm.nih.gov/cas/v1/api-key', data = {'apikey':myUTSAPIkey})
# For API key get a license from https://www.nlm.nih.gov/research/umls/
# tgt.text
response = fromstring(tgt.text)
todaysTgt = response.xpath('//form/@action')[0]

uiUri = "https://uts-ws.nlm.nih.gov/rest/search/current?"
semUri = "https://uts-ws.nlm.nih.gov/rest/content/current/CUI/"


#%%
# ===================================
# 2. Match to foreign terms list
# ===================================
'''
The foreign vocab file is created with the script src/data/build_FullUmls_file.py.

License holders should move this processing before the foreign term 
processing in Phase 1, for the best use - at this point in the process
it's only getting foreign words keyboarded in the English character set
(still useful for many Spanish terms...)
'''

# Open log df
LogAfterJournals = pd.read_excel(dataInterim + 'LogAfterJournals.xlsx')
LogAfterJournals.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType'
'''

# Open unmatched df
UnmatchedAfterJournals = pd.read_excel(dataInterim + 'UnmatchedAfterJournals.xlsx')
UnmatchedAfterJournals.columns

# Open ~1.7 million row UMLS file
umlsTermListForeign = pd.read_csv(dataMatchFiles + 'LicensedData/umlsTermListForeign.csv', sep='|')
umlsTermListForeign.columns
'''
'preferredTerm', 'ui', 'SemanticType', 'wordCount'
'''

umlsTermListForeign.rename(columns={'preferredTerm': 'PreferredTerm'}, inplace=True)

# Reduce to matches
foreignUmlsMatches = pd.merge(UnmatchedAfterJournals, umlsTermListForeign, how='inner', left_on=['AdjustedQueryTerm'], right_on=['PreferredTerm'])
foreignUmlsMatches.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'PreferredTerm', 'ui',
       'SemanticType', 'wordCount'
'''

# Reduce cols
foreignUmlsMatches = foreignUmlsMatches[['AdjustedQueryTerm', 'PreferredTerm', 'ui', 'SemanticType']]

# Combine with searchLog
LogAfterForeign = pd.merge(LogAfterJournals, foreignUmlsMatches, how='left', left_on=['AdjustedQueryTerm'], right_on=['AdjustedQueryTerm'])
LogAfterForeign.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui_x',
       'PreferredTerm_x', 'SemanticType_x', 'PreferredTerm_y', 'ui_y',
       'SemanticType_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. 
# Temporary fix: Move _y into _x if _x is empty; or here: where _x has content, use _x, otherwise use _y
LogAfterForeign['ui2'] = LogAfterForeign['ui_x'].where(LogAfterForeign['ui_x'].notnull(), LogAfterForeign['ui_y'])
LogAfterForeign['ui2'] = LogAfterForeign['ui_y'].where(LogAfterForeign['ui_y'].notnull(), LogAfterForeign['ui_x'])
LogAfterForeign['PreferredTerm2'] = LogAfterForeign['PreferredTerm_x'].where(LogAfterForeign['PreferredTerm_x'].notnull(), LogAfterForeign['PreferredTerm_y'])
LogAfterForeign['PreferredTerm2'] = LogAfterForeign['PreferredTerm_y'].where(LogAfterForeign['PreferredTerm_y'].notnull(), LogAfterForeign['PreferredTerm_x'])
LogAfterForeign['SemanticType2'] = LogAfterForeign['SemanticType_x'].where(LogAfterForeign['SemanticType_x'].notnull(), LogAfterForeign['SemanticType_y'])
LogAfterForeign['SemanticType2'] = LogAfterForeign['SemanticType_y'].where(LogAfterForeign['SemanticType_y'].notnull(), LogAfterForeign['SemanticType_x'])

LogAfterForeign.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
LogAfterForeign.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)

LogAfterForeign.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType'
'''

# Change nan to ''
LogAfterForeign['PreferredTerm'] = LogAfterForeign['PreferredTerm'].fillna('')
LogAfterForeign['SemanticType'] = LogAfterForeign['SemanticType'].fillna('')


# Reduce to unmatched for API
UnmatchedAfterForeign = LogAfterForeign.loc[LogAfterForeign['SemanticType'] == '']
UnmatchedAfterForeign = UnmatchedAfterForeign[['AdjustedQueryTerm', 'TotalSearchFreq']].reset_index(drop=True)


# ----------------------
# Append to PastMatches
# ----------------------

# Bring in file containing this site's historical matches
PastMatches = pd.read_excel(dataMatchFiles + 'PastMatches.xlsx')
PastMatches.columns
'''
'AdjustedQueryTerm', 'PreferredTerm', 'SemanticType', 'ui'
'''

# Align foreignUmlsMatches to PastMatches
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'PreferredTerm', 'ui',
       'SemanticType', 'wordCount'
'''

foreignUmlsMatches = foreignUmlsMatches[['AdjustedQueryTerm', 'PreferredTerm', 'SemanticType', 'ui']]

# Append to PastMatches
PastMatches = PastMatches.append(foreignUmlsMatches, sort=True)

# Sort
PastMatches = PastMatches.sort_values(by=['PreferredTerm', 'AdjustedQueryTerm'], ascending=[True, True])

# Write out the updated PastMatches
writer = pd.ExcelWriter(dataMatchFiles + 'PastMatches.xlsx')
PastMatches.to_excel(writer,'PastMatches', index=False)
writer.save()


# -------------
# How we doin?
# -------------

# Total queries in log
SearchesRepresentedTot = LogAfterForeign['TotalSearchFreq'].sum().astype(int)
SearchesAssignedTot = LogAfterForeign.loc[LogAfterForeign['SemanticType'] != '']
SearchesAssignedTot = SearchesAssignedTot['TotalSearchFreq'].sum().astype(int)
SearchesAssignedPercent = (SearchesAssignedTot / SearchesRepresentedTot * 100).astype(int)
# PercentOfSearchesUnAssigned = 100 - PercentOfSearchesAssigned
RowsTot = len(LogAfterForeign)
RowsAssignedCnt = (LogAfterForeign['SemanticType'].values != '').sum() # .isnull().sum()
# RowsUnassignedCnt = TotRows - RowsAssigned
RowsAssignedPercent = (RowsAssignedCnt / RowsTot * 100).astype(int)

# print("\nTop Semantic Types\n{}".format(LogAfterForeign['SemanticType'].value_counts().head(10)))
print("\n===========================================================\n ** LogAfterForeign: {}% of total search volume tagged **\n===========================================================\n\n{:,} of {:,} searches ({}%) assigned;\n{:,} of {:,} rows ({}%) assigned".format(SearchesAssignedPercent, SearchesAssignedTot, SearchesRepresentedTot, SearchesAssignedPercent, RowsAssignedCnt, RowsTot, RowsAssignedPercent))



# searchLog
del [[LogAfterJournals, UnmatchedAfterJournals, foreignUmlsMatches]]



#%%
# ===============================================
# 3. Set an appropriate dataset size for API run
# ===============================================
'''
In this run the API calls use the Normalized String setting. Example:
for the input string Yellow leaves, normalizedString would return two strings,
leaf yellow and leave yellow. Each string would be matched exactly to the
strings in the normalized string index to return a result.
Re-start:
# listOfUniqueUnmatchedAfterJournals = pd.read_excel('listOfUniqueUnmatchedAfterJournals.xlsx')
listToCheck6 = pd.read_excel(dataInterim + 'listToCheck6.xlsx')
listToCheck7 = pd.read_excel(dataInterim + 'listToCheck7.xlsx')

listToCheck1 = pd.read_excel(dataInterim + 'listToCheck1.xlsx')
listToCheck1 = UnmatchedAfterJournals[0:30]
listToCheck1 = listOfUniqueUnassignedAfterFindReplace[0:20]

writer = pd.ExcelWriter(dataInterim + 'listToCheck1.xlsx')
listToCheck1.to_excel(writer,'listToCheck1')
# df2.to_excel(writer,'Sheet2')
writer.save()

# uniqueSearchTerms = search['AdjustedQueryTerm'].unique()

# Reduce entry length, to focus on single concepts that UTS API can match

'''



# -------------------------------------------
# Batch rows if you want to do separate runs
# Arbitrary max of 5,000 rows per run...
# -------------------------------------------

# listToCheck1 = UnmatchedAfterJournals[UnmatchedAfterJournals.timesSearched >= 3]

# listToCheck1 = UnmatchedAfterJournals

listToCheck1 = LogAfterForeign.iloc[0:7400]

'''
listToCheck1 = UnmatchedAfterJournals.iloc[0:10000]
listToCheck2 = UnmatchedAfterJournals.iloc[10001:20000]
listToCheck3 = UnmatchedAfterJournals.iloc[20001:30000]
listToCheck4 = UnmatchedAfterJournals.iloc[30001:40000]
listToCheck5 = UnmatchedAfterJournals.iloc[40001:55000]
listToCheck6 = UnmatchedAfterJournals.iloc[55001:65264]
# listToCheck7 = UnmatchedAfterJournals.iloc[60001:65264]

# If multiple sessions required, saving to file might help
writer = pd.ExcelWriter(dataInterim + 'listToCheck1.xlsx')
listToCheck1.to_excel(writer,'listToCheck1')
# df2.to_excel(writer,'Sheet2')
writer.save()

OPTION - Bring in from file
listToCheck3 = pd.read_excel(dataInterim + 'listToCheck3.xlsx')
'''


#%%
# ----------------------------------------------------------
# Run this block after changing listToCheck top and bottom
# ----------------------------------------------------------

# Create df
apiGetNormalizedString = pd.DataFrame()
apiGetNormalizedString['AdjustedQueryTerm'] = ""
apiGetNormalizedString['ui'] = ""
apiGetNormalizedString['preferredTerm'] = ""
apiGetNormalizedString['SemanticType'] = list()

for index, row in listToCheck1.iterrows():
    currLogTerm = row['AdjustedQueryTerm']
    # === Get 'preferred term' and its concept identifier (CUI/UI) =========
    stTicket = requests.post(todaysTgt, data = {'service':'http://umlsks.nlm.nih.gov'}) # Get single-use Service Ticket (ST)
    tQuery = {'string':currLogTerm, 'searchType':'normalizedString', 'ticket':stTicket.text} # removed 'sabs':'MSH', 
    getPrefTerm = requests.get(uiUri, params=tQuery)
    getPrefTerm.encoding = 'utf-8'
    tItems  = json.loads(getPrefTerm.text)
    tJson = tItems["result"]
    # Capture info
    if tJson["results"][0]["ui"] != "NONE": # Sub-loop to resolve "NONE"
        currUi = tJson["results"][0]["ui"]
        currPrefTerm = tJson["results"][0]["name"]
        # === Get 'semantic type' =========
        stTicket = requests.post(todaysTgt, data = {'service':'http://umlsks.nlm.nih.gov'}) # Get another single-use Service Ticket (ST)
        semQuery = {'ticket':stTicket.text}
        getPrefTerm = requests.get(semUri+currUi, params=semQuery)
        getPrefTerm.encoding = 'utf-8'
        semItems  = json.loads(getPrefTerm.text)
        semJson = semItems["result"]
        currSemTypes = []
        for name in semJson["semanticTypes"]:
            currSemTypes.append(name["name"]) #  + " ; "
        # === Post to dataframe =========
        apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'AdjustedQueryTerm': currLogTerm, 
                                                       'ui': currUi,
                                                       'PreferredTerm': currPrefTerm, 
                                                       'SemanticType': currSemTypes}), ignore_index=True)
        print('{} --> {}'.format(currLogTerm, currSemTypes)) # Write progress to console
        # time.sleep(.06)
    else:
       # Post "NONE" to database and restart loop
        apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'AdjustedQueryTerm': currLogTerm, 'preferredTerm': "NONE"}, index=[0]), ignore_index=True)
        print('{} --> NONE'.format(currLogTerm, )) # Write progress to console
        # time.sleep(.06)
print ("* Done *")

# Experiment - Convert to one concept per row, with multiple SemanticType separated with pipe
# This makes joins easier, but adds step to later counting. What works best?
apiGetNormalizedString = apiGetNormalizedString.groupby(['ui','AdjustedQueryTerm', 'preferredTerm'])['SemanticType'].apply('|'.join).reset_index()

# Save
writer = pd.ExcelWriter(dataInterim + 'ApiNormalizedString1.xlsx')
apiGetNormalizedString.to_excel(writer,'ApiNormalizedString', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%
# ===========================================
# 3. Integrate Metathesaurus data
# ===========================================

LogAfterJournals = pd.read_excel(dataInterim + 'LogAfterJournals.xlsx')
LogAfterJournals.columns

# apiGetNormalizedString.rename(columns={'preferredTerm': 'PreferredTerm'}, inplace=True)


# Join to full list
LogAfterMetathesaurus = pd.merge(LogAfterJournals, apiGetNormalizedString, how='left', left_on=['AdjustedQueryTerm'], right_on=['AdjustedQueryTerm'])
LogAfterMetathesaurus.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui_x',
       'PreferredTerm_x', 'SemanticType_x', 'ui_y', 'PreferredTerm_y',
       'SemanticType_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. 
# Temporary fix: Move _y into _x if _x is empty; or here: where _x has content, use _x, otherwise use _y
LogAfterMetathesaurus['ui2'] = LogAfterMetathesaurus['ui_x'].where(LogAfterMetathesaurus['ui_x'].notnull(), LogAfterMetathesaurus['ui_y'])
LogAfterMetathesaurus['ui2'] = LogAfterMetathesaurus['ui_y'].where(LogAfterMetathesaurus['ui_y'].notnull(), LogAfterMetathesaurus['ui_x'])
LogAfterMetathesaurus['PreferredTerm2'] = LogAfterMetathesaurus['PreferredTerm_x'].where(LogAfterMetathesaurus['PreferredTerm_x'].notnull(), LogAfterMetathesaurus['PreferredTerm_y'])
LogAfterMetathesaurus['PreferredTerm2'] = LogAfterMetathesaurus['PreferredTerm_y'].where(LogAfterMetathesaurus['PreferredTerm_y'].notnull(), LogAfterMetathesaurus['PreferredTerm_x'])
LogAfterMetathesaurus['SemanticType2'] = LogAfterMetathesaurus['SemanticType_x'].where(LogAfterMetathesaurus['SemanticType_x'].notnull(), LogAfterMetathesaurus['SemanticType_y'])
LogAfterMetathesaurus['SemanticType2'] = LogAfterMetathesaurus['SemanticType_y'].where(LogAfterMetathesaurus['SemanticType_y'].notnull(), LogAfterMetathesaurus['SemanticType_x'])

LogAfterMetathesaurus.drop(['ui_x', 'ui_y', 'PreferredTerm_x', 'PreferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
LogAfterMetathesaurus.rename(columns={'ui2': 'ui', 'PreferredTerm2': 'PreferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)

LogAfterMetathesaurus.columns
'''
'AdjustedQueryTerm', 'TotalSearchFreq', 'Query', 'ui', 'PreferredTerm',
       'SemanticType'
'''

# Write outLogAfterMetathesaurus
writer = pd.ExcelWriter(dataInterim + 'LogAfterMetathesaurus.xlsx')
LogAfterMetathesaurus.to_excel(writer,'LogAfterMetathesaurus', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


# Separate next operations so previous matches won't be overwritten
UnmatchedAfterMetathesaurus = LogAfterMetathesaurus.loc[LogAfterMetathesaurus['SemanticType'] == '']
UnmatchedAfterMetathesaurus = UnmatchedAfterMetathesaurus[['AdjustedQueryTerm', 'TotalSearchFreq']].reset_index(drop=True)

# Write out UnmatchedAfterMetathesaurus
writer = pd.ExcelWriter(dataInterim + 'UnmatchedAfterMetathesaurus.xlsx')
UnmatchedAfterMetathesaurus.to_excel(writer,'UnmatchedAfterMetathesaurus', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


# -------------
# How we doin?
# -------------

# Total queries in log
SearchesRepresentedTot = LogAfterMetathesaurus['TotalSearchFreq'].sum().astype(int)
SearchesAssignedTot = LogAfterMetathesaurus.loc[LogAfterMetathesaurus['SemanticType'] != '']
SearchesAssignedTot = SearchesAssignedTot['TotalSearchFreq'].sum().astype(int)
SearchesAssignedPercent = (SearchesAssignedTot / SearchesRepresentedTot * 100).astype(int)
# PercentOfSearchesUnAssigned = 100 - PercentOfSearchesAssigned
RowsTot = len(LogAfterMetathesaurus)
RowsAssignedCnt = (LogAfterMetathesaurus['SemanticType'].values != '').sum() # .isnull().sum()
# RowsUnassignedCnt = TotRows - RowsAssigned
RowsAssignedPercent = (RowsAssignedCnt / RowsTot * 100).astype(int)

# print("\nTop Semantic Types\n{}".format(LogAfterMetathesaurus['SemanticType'].value_counts().head(10)))
print("\n================================================================\n ** LogAfterMetathesaurus: {}% of total search volume tagged **\n================================================================\n{:,} of {:,} searches ({}%) assigned;\n{:,} of {:,} rows ({}%) assigned".format(SearchesAssignedPercent, SearchesAssignedTot, SearchesRepresentedTot, SearchesAssignedPercent, RowsAssignedCnt, RowsTot, RowsAssignedPercent))


# Free up some memory
del [[LogAfterJournals, UnmatchedAfterJournals, listToCheck1]]


#%%
# ==========================================
# 4. Append new API results to PastMatches
# ==========================================
'''
Improve future local matching and fuzzy matching.

Re-start?
newApiAssignments = pd.read_excel('02_API-Normalized_string_files/newApiAssignments.xlsx')
'''

'''
UmlsResult = newAssignments1.append([apiGetNormalizedString]) # , sort=False

Or if you only had one df from the API:
'''

ApiNormalizedString = pd.read_excel(dataInterim + 'ApiNormalizedString1.xlsx')
ApiNormalizedString.columns
'''
'Unnamed: 0', 'ui', 'AdjustedQueryTerm', 'preferredTerm',
       'SemanticType'
'''

ApiNormalizedString.drop(['Unnamed: 0'], axis=1, inplace=True)

ApiNormalizedString.rename(columns={'preferredTerm': 'PreferredTerm'}, inplace=True)


# Bring in file containing this site's historical matches
PastMatches = pd.read_excel(dataMatchFiles + 'PastMatches.xlsx')

# Append to PastMatches
PastMatches = PastMatches.append(ApiNormalizedString, sort=True)

# Sort, reset index
PastMatches = PastMatches.sort_values(by=['PreferredTerm', 'AdjustedQueryTerm'], ascending=[True, True])

'''
Eyeball top and bottom of cols, remove rows by Index, if needed
PastMatches.drop(58027, inplace=True)
'''

# Write out the updated PastMatches
writer = pd.ExcelWriter(dataMatchFiles + 'PastMatches.xlsx')
PastMatches.to_excel(writer,'PastMatches', index=False)
writer.save()


#%%

'''
Until you put this into a function, you need to change listToCheck#
and apiGetNormalizedString# counts every run!
Stay below 30 API requests per second. With 4 API requests per item
(2 .get and 2 .post requests)...
time.sleep commented out: 6,000 / 35 min = 171 per minute = 2.9 items per second / 11.4 requests per second
Computing differently, 6,000 items @ 4 Req per item = 24,000 Req, divided by 35 min+
686 Req/min = 11.4 Req/sec
time.sleep(.07):  ~38 minutes to do 6,000; 158 per minute / 2.6 items per second

Example entry that has multiple preferredTerm suggestions:
    
{
    "pageSize": 25,
    "pageNumber": 1,
    "result": {
        "classType": "searchResults",
        "results": [
            {
                "ui": "S42.45",
                "rootSource": "ICD10CM",
                "uri": "https://uts-ws.nlm.nih.gov/rest/content/2018AA/source/ICD10CM/S42.45",
                "name": "Fracture of lateral condyle of humerus"
            },
            {
                "ui": "208272001",
                "rootSource": "SNOMEDCT_US",
                "uri": "https://uts-ws.nlm.nih.gov/rest/content/2018AA/source/SNOMEDCT_US/208272001",
                "name": "Closed fracture distal humerus, capitellum"
            },
            {
                "ui": "208284004",
                "rootSource": "SNOMEDCT_US",
                "uri": "https://uts-ws.nlm.nih.gov/rest/content/2018AA/source/SNOMEDCT_US/208284004",
                "name": "Open fracture distal humerus, capitellum"
            },
            {
                "ui": "213243",
                "rootSource": "MEDCIN",
                "uri": "https://uts-ws.nlm.nih.gov/rest/content/2018AA/source/MEDCIN/213243",
                "name": "open capitellar fracture of right humerus involving subchondral bone and trochlea"
            }
        ]
    }
}
'''

"""
# FUTURE VERSION...

def getStuffFromAPI(currLogTerm): #Fetch from API
# === Get 'preferred term' and its concept identifier (CUI/UI) =========
    stTicket = requests.post(todaysTgt, data = {'service':'http://umlsks.nlm.nih.gov'}) # Get single-use Service Ticket (ST)
    tQuery = {'string':currLogTerm, 'searchType':'normalizedString', 'ticket':stTicket.text} # removed 'sabs':'MSH',
    getPrefTerm = requests.get(uiUri, params=tQuery)
    getPrefTerm.encoding = 'utf-8'
    tItems  = json.loads(getPrefTerm.text)
    tJson = tItems["result"]
    return tJson

def getSemanticType(currUi): #Send Stuff to the API
# === Get 'semantic type' =========
    stTicket = requests.post(todaysTgt, data = {'service':'http://umlsks.nlm.nih.gov'}) # Get single-use Service Ticket (ST)
    semQuery = {'ticket':stTicket.text}
    getPrefTerm = requests.get(semUri+currUi, params=semQuery)
    getPrefTerm.encoding = 'utf-8'
    semItems  = json.loads(getPrefTerm.text)
    semJson = semItems["result"]
    currSemTypes = []
    for name in semJson["semanticTypes"]:
        currSemTypes.append(name["name"]) #  + " ; "
    return currSemTypes

def postToDataFrame(currSemTypes, currPrefTerm, currLogTerm,apiGetNormalizedString):
 # === Post to dataframe =========
    apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'AdjustedQueryTerm': currLogTerm,
                                               'preferredTerm': currPrefTerm,
                                               'SemanticType': currSemTypes}), ignore_index=True)
    return apiGetNormalizedString

#initialize spellchecker
bj = hunspell.HunSpell('/home/ubuntu/umls/sortedvocab.txt.dic', '/home/ubuntu/umls/sortedvocab.txt.aff')
for index, row in listToCheck1.iterrows():
    currLogTerm = row['AdjustedQueryTerm']
    tJson = getStuffFromAPI(currLogTerm)
    if tJson["results"][0]["ui"] != "NONE": # Sub-loop to resolve "NONE"
        currUi = tJson["results"][0]["ui"]
        currPrefTerm = tJson["results"][0]["name"]
          
        currSemTypes = getSemanticType(currUi)
        # === Post to dataframe =========
        apiGetNormalizedString = postToDataFrame(currSemTypes, currPrefTerm, currLogTerm,apiGetNormalizedString)
        print('{} --> {}'.format(currLogTerm, currSemTypes)) # Write progress to console
        # time.sleep(.06)
    else:
        original = currLogTerm
        suggestion = bj.suggest(currLogTerm)
        if len(suggestion) > 0 and  (suggestion[0] != "["+original):
            currLogTerm = suggestion[0]
            tJson = getStuffFromAPI(currLogTerm)
            currUi = tJson["results"][0]["ui"]
            currPrefTerm = tJson["results"][0]["name"]

            currSemTypes = getSemanticType(currUi)
            # === Post to dataframe =========
            apiGetNormalizedString = postToDataFrame(currSemTypes, currPrefTerm, currLogTerm, apiGetNormalizedString)
            print('{}: {} --> {}'.format(original, currLogTerm, currSemTypes)) # Write progress to console
        else:
	    # Post "NONE" to database and restart loop
            apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'AdjustedQueryTerm': currLogTerm, 'preferredTerm': "NONE"}, index=[0]), ignore_index=True)
            print('{} --> NONE'.format(currLogTerm, )) # Write progress to console
            # time.sleep(.06)
print ("* Done *")
"""



'''
writer = pd.ExcelWriter(dataInterim + 'apiGetNormalizedString1.xlsx')
apiGetNormalizedString.to_excel(writer,'apiGetNormalizedString')
# df2.to_excel(writer,'Sheet2')
writer.save()

# Free up memory: Remove listToCheck, listToCheck1, listToCheck2, listToCheck3,
# listToCheck4, nonForeign, searchLog, UnmatchedAfterJournals
'''


"""

#%%
# ==================================================================
# 3. Combine multiple files if needed
'''
If you ran multiple runs and need to combine parts.

Re-starting? If using old version, the 'for' loop, use digit such asapiGetNormalizedString1
apiGetNormalizedString = pd.read_excel('02_API-Normalized_string_files/apiGetNormalizedString.xlsx')

apiGetNormalizedString = apiGetNormalizedString1
'''

# Bring in stored info
newAssignments1 = pd.read_excel('02_API-Normalized_string_files/ApiNormalizedString1.xlsx')
newAssignments2 = pd.read_excel('02_API-Normalized_string_files/ApiNormalizedString2.xlsx')
newAssignments3 = pd.read_excel('02_API-Normalized_string_files/ApiNormalizedString3.xlsx')
newAssignments4 = pd.read_excel('02_API-Normalized_string_files/ApiNormalizedString4.xlsx')
newAssignments5 = pd.read_excel('02_API-Normalized_string_files/ApiNormalizedString5.xlsx')

# Append
UmlsResult = newAssignments1.append([newAssignments2, newAssignments3, newAssignments4]) # , sort=False
# afterUmlsApi = newAssignments1.append([newAssignments2, newAssignments3, newAssignments4, newAssignments5])
# Last run's data should be in a df already.


"""

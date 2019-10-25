#!/usr/bin/env python3
#-*- coding: utf-8 -*-
"""
Created on Thu Jun 28 15:33:33 2018

@authors: dan.wendling@nih.gov, 

Last modified: 2019-10-16

** Site-search log file analyzer, Part 2 **

Purpose: Run unmatched search queries against UMLS API.

The first UMLS API run uses normalized string matching, which is conservative
enough to assume that almost all the matches are correct. Some clean-up will 
be needed, later.


----------------
SCRIPT CONTENTS
----------------

1. Start-up
2. Umls Api 1 - Normalized string matching
3. Isolate entries updated by API, complete tagging, and match to the
   new version of the search log - logAfterUmlsApi1
4. Append new API results to PastMatches
5. Create logAfterUmlsApi1 by updating logAfterPastMatches - append newApiAssignments
6. Create new 'uniques' dataframe/file for fuzzy matching
7. Start new 'uniques' dataframe
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
# Re-starting?
uniqueUnassignedAfterStep1 = pd.read_excel('01_Import-transform_files/uniqueUnassignedAfterStep1.xlsx')
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
os.chdir('/Users/name/Projects/semanticsearch')
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
reports = 'reports/search/' # Where to write images, etc., to

# Specific files you'll need. NOTE - Removes df if your first session is still active
uniqueUnassignedAfterStep1 = dataInterim + 'uniqueUnassignedAfterStep1.xlsx' # newest log
PastMatches = dataMatchFiles + 'PastMatches.xlsx' # historical file of vetted successful matches
logAfterStep1 = dataInterim + 'logAfterStep1-07.xlsx'

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
# ===========================================
# 2. Umls Api 1 - Normalized string matching
# ===========================================
'''
In this run the API calls use the Normalized String setting. Example:
for the input string Yellow leaves, normalizedString would return two strings,
leaf yellow and leave yellow. Each string would be matched exactly to the
strings in the normalized string index to return a result.
Re-start:
# listOfUniqueuniqueUnassignedAfterStep1 = pd.read_excel('listOfUniqueuniqueUnassignedAfterStep1.xlsx')
listToCheck6 = pd.read_excel(dataInterim + 'listToCheck6.xlsx')
listToCheck7 = pd.read_excel(dataInterim + 'listToCheck7.xlsx')

listToCheck1 = pd.read_excel(dataInterim + 'listToCheck1.xlsx')
listToCheck1 = uniqueUnassignedAfterStep1[0:30]
listToCheck1 = listOfUniqueUnassignedAfterFindReplace[0:20]

writer = pd.ExcelWriter(dataInterim + 'listToCheck1.xlsx')
listToCheck1.to_excel(writer,'listToCheck1')
# df2.to_excel(writer,'Sheet2')
writer.save()

# uniqueSearchTerms = search['adjustedQueryTerm'].unique()

# Reduce entry length, to focus on single concepts that UTS API can match

'''

uniqueUnassignedAfterStep1 = pd.read_excel(uniqueUnassignedAfterStep1)



# -------------------------------------------
# Batch rows if you want to do separate runs
# Arbitrary max of 5,000 rows per run...
# -------------------------------------------

# listToCheck1 = uniqueUnassignedAfterStep1[uniqueUnassignedAfterStep1.timesSearched >= 3]

listToCheck1 = uniqueUnassignedAfterStep1

listToCheck1 = uniqueUnassignedAfterStep1.iloc[0:1000]

'''
listToCheck1 = uniqueUnassignedAfterStep1.iloc[0:10000]
listToCheck2 = uniqueUnassignedAfterStep1.iloc[10001:20000]
listToCheck3 = uniqueUnassignedAfterStep1.iloc[20001:30000]
listToCheck4 = uniqueUnassignedAfterStep1.iloc[30001:40000]
listToCheck5 = uniqueUnassignedAfterStep1.iloc[40001:55000]
listToCheck6 = uniqueUnassignedAfterStep1.iloc[55001:65264]
# listToCheck7 = uniqueUnassignedAfterStep1.iloc[60001:65264]

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
apiGetNormalizedString['adjustedQueryTerm'] = ""
apiGetNormalizedString['ui'] = ""
apiGetNormalizedString['preferredTerm'] = ""
apiGetNormalizedString['SemanticType'] = list()

# OLD VERSION PLUS SUCCESSFUL CAPTURE OF MULTIPLE SemanticType ENTRIES


for index, row in listToCheck1.iterrows():
    currLogTerm = row['adjustedQueryTerm']
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
        apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'adjustedQueryTerm': currLogTerm, 
                                                       'ui': currUi,
                                                       'preferredTerm': currPrefTerm, 
                                                       'SemanticType': currSemTypes}), ignore_index=True)
        print('{} --> {}'.format(currLogTerm, currSemTypes)) # Write progress to console
        # time.sleep(.06)
    else:
       # Post "NONE" to database and restart loop
        apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'adjustedQueryTerm': currLogTerm, 'preferredTerm': "NONE"}, index=[0]), ignore_index=True)
        print('{} --> NONE'.format(currLogTerm, )) # Write progress to console
        # time.sleep(.06)
print ("* Done *")

# Experiment - Convert to one concept per row, with multiple SemanticType separated with pipe
# This makes joins easier, but adds step to later counting. What works best?
apiGetNormalizedString = apiGetNormalizedString.groupby(['ui','adjustedQueryTerm', 'preferredTerm'])['SemanticType'].apply('|'.join).reset_index()

# Save
writer = pd.ExcelWriter(dataInterim + 'apiNormalizedString1.xlsx')
apiGetNormalizedString.to_excel(writer,'apiNormalizedString')
# df2.to_excel(writer,'Sheet2')
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
    apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'adjustedQueryTerm': currLogTerm,
                                               'preferredTerm': currPrefTerm,
                                               'SemanticType': currSemTypes}), ignore_index=True)
    return apiGetNormalizedString

#initialize spellchecker
bj = hunspell.HunSpell('/home/ubuntu/umls/sortedvocab.txt.dic', '/home/ubuntu/umls/sortedvocab.txt.aff')
for index, row in listToCheck1.iterrows():
    currLogTerm = row['adjustedQueryTerm']
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
            apiGetNormalizedString = apiGetNormalizedString.append(pd.DataFrame({'adjustedQueryTerm': currLogTerm, 'preferredTerm': "NONE"}, index=[0]), ignore_index=True)
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
# listToCheck4, nonForeign, searchLog, uniqueUnassignedAfterStep1
'''


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
newAssignments1 = pd.read_excel('02_API-Normalized_string_files/apiNormalizedString1.xlsx')
newAssignments2 = pd.read_excel('02_API-Normalized_string_files/apiNormalizedString2.xlsx')
newAssignments3 = pd.read_excel('02_API-Normalized_string_files/apiNormalizedString3.xlsx')
newAssignments4 = pd.read_excel('02_API-Normalized_string_files/apiNormalizedString4.xlsx')
newAssignments5 = pd.read_excel('02_API-Normalized_string_files/apiNormalizedString5.xlsx')

# Append
UmlsResult = newAssignments1.append([newAssignments2, newAssignments3, newAssignments4]) # , sort=False
# afterUmlsApi = newAssignments1.append([newAssignments2, newAssignments3, newAssignments4, newAssignments5])
# Last run's data should be in a df already.



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
UmlsResult = apiGetNormalizedString


# Bring in file containing this site's historical matches
PastMatches = pd.read_excel(PastMatches)

# Depending on the steps you took above... This is for one API run
# UmlsResult = apiGetNormalizedString

# Reduce to a list of successful assignments
newApiAssignments = UmlsResult.loc[(UmlsResult['preferredTerm'] != "NONE")]
newApiAssignments = newApiAssignments[~pd.isnull(newApiAssignments['preferredTerm'])]
newApiAssignments = newApiAssignments.loc[(newApiAssignments['preferredTerm'] != "Null Value")]
newApiAssignments = newApiAssignments[~pd.isnull(newApiAssignments['adjustedQueryTerm'])]

# Eyeball the df. If you need to remove rows...
# logAfterPastMatches = logAfterPastMatches.iloc[760:] # remove before index...

# Reduce cols
newApiAssignments = newApiAssignments[['ui', 'adjustedQueryTerm', 'preferredTerm', 'SemanticType']]

'''
# If you want to send to Excel (Good for presentations, good quantity of 'stumpers'; 
convincing reason to NOT try to label them yourself in Excel)
writer = pd.ExcelWriter(dataInterim + 'newApiAssignments.xlsx')
newApiAssignments.to_excel(writer,'newApiAssignments')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

# newApiAssignments = pd.read_excel('02_API-Normalized_string_files/newApiAssignments.xlsx')


# Append fully tagged UMLS API adds to PastMatches
PastMatches = PastMatches.append(newApiAssignments, sort=True)

# Sort, reset index
PastMatches = PastMatches.sort_values(by='adjustedQueryTerm', ascending=True)
PastMatches = PastMatches.reset_index()
PastMatches.drop(['index'], axis=1, inplace=True)

'''
Eyeball top and bottom of cols, remove rows by Index, if needed
PastMatches.drop(58027, inplace=True)
'''

# Write out the updated PastMatches
writer = pd.ExcelWriter(dataMatchFiles + 'PastMatches.xlsx')
PastMatches.to_excel(writer,'PastMatches')
writer.save()


#%%
# ============================================================================
# 5. Create S2LogAfterUmlsApi1 by updating logAfterPastMatches - append
# newApiAssignments
# ============================================================================
'''
# Restart?
logAfterQuirkyMatches = pd.read_excel('01_Import-transform_files/logAfterQuirkyMatches.xlsx')
newApiAssignments = pd.read_excel('02_API-Normalized_string_files/newApiAssignments.xlsx')

# If you combined several logs
logAfterUmlsApi1 = combinedLogs
'''

# bring in the data to match against
# logAfterStep1 = pd.read_excel(logAfterStep1)

logAfterStep1 = pd.read_excel(dataInterim + 'S1Logs-Combined.xlsx')

newApiAssignments = pd.read_excel(dataInterim + 'NewFromApi1.xlsx')


# Join new UMLS API adds to the current search log master
logAfterUmlsApi1 = pd.merge(logAfterStep1, newApiAssignments, how='left', on='adjustedQueryTerm')

logAfterUmlsApi1.columns
'''
'Unnamed: 0_x', 'CountForPgDate', 'Date', 'ProbablyMeantGSTerm',
       'Query', 'Referrer', 'SemanticType_x', 'SessionID', 'Unnamed: 0.1',
       'Unnamed: 0.1.1.1.1.1.1_x', 'Unnamed: 0.1.1.1.1.1.1_y',
       'Unnamed: 0.1.1.1.1.1_x', 'Unnamed: 0.1.1.1.1.1_y',
       'Unnamed: 0.1.1.1.1_x', 'Unnamed: 0.1.1.1.1_y', 'Unnamed: 0.1.1.1_x',
       'Unnamed: 0.1.1.1_y', 'Unnamed: 0.1.1_x', 'Unnamed: 0.1.1_y',
       'Unnamed: 0.1_x', 'Unnamed: 0.1_y', 'Unnamed: 0_x', 'Unnamed: 0_y',
       'adjustedQueryTerm', 'preferredTerm_x', 'ui_x', 'Unnamed: 0_y', 'ui_y',
       'preferredTerm_y', 'SemanticType_y'
'''

logAfterUmlsApi1.drop(['Unnamed: 0_x', 'Unnamed: 0.1',
       'Unnamed: 0.1.1.1.1.1.1_x', 'Unnamed: 0.1.1.1.1.1.1_y',
       'Unnamed: 0.1.1.1.1.1_x', 'Unnamed: 0.1.1.1.1.1_y',
       'Unnamed: 0.1.1.1.1_x', 'Unnamed: 0.1.1.1.1_y', 'Unnamed: 0.1.1.1_x',
       'Unnamed: 0.1.1.1_y', 'Unnamed: 0.1.1_x', 'Unnamed: 0.1.1_y',
       'Unnamed: 0.1_x', 'Unnamed: 0.1_y', 'Unnamed: 0_x', 'Unnamed: 0_y',
       'Unnamed: 0_y'], axis=1, inplace=True)
            
logAfterUmlsApi1.columns
'''
'CountForPgDate', 'Date', 'ProbablyMeantGSTerm', 'Query', 'Referrer',
       'SemanticType_x', 'SessionID', 'adjustedQueryTerm', 'preferredTerm_x',
       'ui_x', 'ui_y', 'preferredTerm_y', 'SemanticType_y'
'''
         

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterUmlsApi1['ui2'] = logAfterUmlsApi1['ui_x'].where(logAfterUmlsApi1['ui_x'].notnull(), logAfterUmlsApi1['ui_y'])
logAfterUmlsApi1['ui2'] = logAfterUmlsApi1['ui_y'].where(logAfterUmlsApi1['ui_y'].notnull(), logAfterUmlsApi1['ui_x'])
logAfterUmlsApi1['preferredTerm2'] = logAfterUmlsApi1['preferredTerm_x'].where(logAfterUmlsApi1['preferredTerm_x'].notnull(), logAfterUmlsApi1['preferredTerm_y'])
logAfterUmlsApi1['preferredTerm2'] = logAfterUmlsApi1['preferredTerm_y'].where(logAfterUmlsApi1['preferredTerm_y'].notnull(), logAfterUmlsApi1['preferredTerm_x'])
logAfterUmlsApi1['SemanticType2'] = logAfterUmlsApi1['SemanticType_x'].where(logAfterUmlsApi1['SemanticType_x'].notnull(), logAfterUmlsApi1['SemanticType_y'])
logAfterUmlsApi1['SemanticType2'] = logAfterUmlsApi1['SemanticType_y'].where(logAfterUmlsApi1['SemanticType_y'].notnull(), logAfterUmlsApi1['SemanticType_x'])

logAfterUmlsApi1.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterUmlsApi1.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)
logAfterUmlsApi1.columns
'''
'CountForPgDate', 'Date', 'ProbablyMeantGSTerm', 'Query', 'Referrer',
       'SessionID', 'adjustedQueryTerm', 'ui', 'preferredTerm',
       'SemanticType'
'''

'''
# Tidy
logAfterUmlsApi1.drop(['Unnamed: 0', 'Unnamed: 0_x', 'Unnamed: 0_y', 'Unnamed: 0.1'], axis=1, inplace=True)
logAfterUmlsApi1['SemanticType2'] = logAfterUmlsApi1['SemanticType'].where(logAfterUmlsApi1['SemanticType'].notnull(), logAfterUmlsApi1['NewSemanticTypeName'])
logAfterUmlsApi1.drop(['NewSemanticTypeName', 'SemanticType'], axis=1, inplace=True)
logAfterUmlsApi1.rename(columns={'SemanticType2': 'SemanticType'}, inplace=True)
logAfterUmlsApi1.columns
'''


# Error in sorting sometimes if a single adjustedQueryTerm is int
logAfterUmlsApi1['adjustedQueryTerm'] = logAfterUmlsApi1['adjustedQueryTerm'].astype(str)
# Re-sort full file
logAfterUmlsApi1 = logAfterUmlsApi1.sort_values(by='adjustedQueryTerm', ascending=True)
logAfterUmlsApi1 = logAfterUmlsApi1.reset_index()
logAfterUmlsApi1.drop(['index'], axis=1, inplace=True)

# Save to file so you can open in future sessions, if needed
writer = pd.ExcelWriter(dataInterim + 'S2LogAfterApi1.xlsx')
logAfterUmlsApi1.to_excel(writer,'logAfterUmlsApi1')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -------------
# How we doin?
# -------------
rowCount = len(logAfterUmlsApi1)
TotUniqueEntries = logAfterUmlsApi1['adjustedQueryTerm'].nunique()

Assigned = logAfterUmlsApi1['SemanticType'].count()
# Assigned = (logAfterUmlsApi1['SemanticType'].values != '').sum() 
# Assigned = (logAfterUmlsApi1['SemanticType'].notnull().sum())
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterUmlsApi1['SemanticType'].value_counts().head(10)))
print("\n\n===============================================\n ** logAfterUmlsApi1 stats **\n===============================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))

'''
# -------------------------------
# How we doin? Visualize results
# -------------------------------

# Pie for percentage of rows assigned; https://pythonspot.com/matplotlib-pie-chart/

TotLogEntries = logAfterUmlsApi1['CountForPgDate'].sum()

newAssigned = logAfterUmlsApi1[['SemanticType', 'CountForPgDate']]
newAssigned = newAssigned[newAssigned['SemanticType'].notnull() == True]
newAssigned = newAssigned['CountForPgDate'].sum()
newUnassigned = TotLogEntries - newAssigned

labels = ['Assigned', 'Unassigned']
sizes = [newAssigned, newUnassigned]
colors = ['steelblue', '#fc8d59']
explode = (0.1, 0)  # explode 1st slice

# viz --------------
# Pie of status
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'Step 2' processing - \n{:,} queries with {:,} queries assigned".format(TotLogEntries, newAssigned))
plt.show()

plt.savefig(reports + 'Search-StatusAfterStep2.png')


# viz --------------
# Bar of SemanticType categories, horizontal
ax = logAfterUmlsApi1['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(10,6), color="steelblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'Step 2' processing \nwith {:,} of {:,} unassigned".format(newUnassigned, TotLogEntries), fontsize=14)
ax.set_xlabel("Number of searches", fontsize=9);
ax.set_ylabel("Semantic Type", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.31, i.get_y()+.31, "{:,}".format(i.get_width()), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.4)
plt.show()

plt.savefig(reports + 'Search-SemTypesAfterStep2.png')

# Remove listOfUniqueuniqueUnassignedAfterStep1, listToCheck1, etc., logAfterPastMatches, logAfterUmlsApi11,
# newAssignments1 etc.
'''


#%%
# ============================================================================
# 6. Start new 'uniques' dataframe that gets new column for each of the below
# listOfUniqueUnassignedAfterUmls1
# ============================================================================

# Unique queries with no assignments
uniqueUnassignedAfterStep2 = logAfterUmlsApi1[pd.isnull(logAfterUmlsApi1['SemanticType'])] # preferredTerm, don't use anymore because Quirky, etc. doesn't have preferredTerm
uniqueUnassignedAfterStep2 = uniqueUnassignedAfterStep2.groupby('adjustedQueryTerm').size()
uniqueUnassignedAfterStep2 = pd.DataFrame({'timesSearched':uniqueUnassignedAfterStep2})
uniqueUnassignedAfterStep2 = uniqueUnassignedAfterStep2.sort_values(by='timesSearched', ascending=False)
uniqueUnassignedAfterStep2 = uniqueUnassignedAfterStep2.reset_index()

# If combo file and it's huge, limit by search frequency
uniqueUnassignedAfterStep2 = uniqueUnassignedAfterStep2[uniqueUnassignedAfterStep2.timesSearched >= 4]


# Send to file to preserve
writer = pd.ExcelWriter(dataInterim + 'S2UniquesAfterApi1.xlsx')
uniqueUnassignedAfterStep2.to_excel(writer,'unassignedToCheck')
writer.save()


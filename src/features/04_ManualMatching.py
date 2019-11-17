#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 31 12:56:43 2018

@authors: dan.wendling@nih.gov, 

Last modified: 2019-10-16

** Site-search log file analyzer, Step 4 **

This script: Use UI to select among fuzzy matching and machine learning
candidates for remaining unmatched queries. All manual matches go to 
QuirkyMatches.xlsx

SWITCH TO HighConfidenceGuesses?

, a holding area, where terms can used for awhile 
without vetting. However, it's best to eyeball them and move the ones 
that are CORRECTLY SPELLED and otherwise correct, to PastMatches.xlsx. 
(Incorrect spellings should not be the basis of fuzzy matching.)


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Add term prediction file to SQLite
3. Process results in browser using http://localhost:5000/MakeAssignments/
4. Update QuirkyMatches and log, from manual_assignments table - logAfterStep4.xlsx
5. Create new 'uniques' - uniqueUnassignedAfterStep4.xlsx

"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import pie, axis, show
import numpy as np
import requests
import json
import lxml.html as lh
from lxml.html import fromstring
import time
import os
from fuzzywuzzy import fuzz, process

import sqlite3
from pandas.io import sql
from sqlite3 import Error
from sqlalchemy import create_engine
# import mysql.connector

# Set working directory, read/write locations
# CHANGE AS NEEDED
os.chdir('/Users/wendlingd/Projects/semanticsearch')
dbDir = '_django/loganalysis/'
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/search/' # Save to disk as desired, to re-start easily
reports = 'reports/search/' # Where to write images, etc., to

# Specific files you'll need. NOTE - Removes df if your first session is still active
dbIngestFile = dbDir + '04-TermPredictions.xlsx'
QuirkyMatches = dataMatchFiles + 'QuirkyMatches.xlsx' # Human-chosen terms that might be misspelled, foreign, etc.

logAfterStep4 = dataInterim + 'logAfterStep4.xlsx'

# Open file of term predictions
dbIngestFile = pd.read_excel(dbIngestFile)

# Add additional cols or SQLite will change the schema
dbIngestFile['NewSemanticType'] = ""
dbIngestFile['SemanticGroup'] = ""
dbIngestFile['Modified'] = 0


#%%
# =================================================================
# 2. Add term prediction file to SQLite
# =================================================================
'''
In DB Browser for SQLite:
    
DROP TABLE IF EXISTS manual_assignments;
VACUUM;
CREATE TABLE `manual_assignments` (`id` integer NOT NULL PRIMARY KEY AUTOINCREMENT, `adjustedQueryTerm` TEXT, `preferredTerm` TEXT, `FuzzyToken` TEXT, `SemanticType` TEXT, `timesSearched` INTEGER, `FuzzyScore` INTEGER, `NewSemanticType` TEXT, `SemanticGroup` TEXT, `Modified` INTEGER);


# FIXME - Arranged to solve problems with Django UI; update this when possible.

Assumes this path and name on disk; update accordingly
/Users/wendlingd/Projects/webDS/_django/loganalysis/db.sqlite3
'''

# Set new working directory
# os.chdir('/Users/wendlingd/Projects/webDS/_django/loganalysis')



# Open or re-open the database connection
conn = sqlite3.connect("db.sqlite3") # opens sqlite and a database file
myCursor = conn.cursor() # provides a connection to the database

# Replace old data with new
dbIngestFile.to_sql("manual_assignments", conn, if_exists="replace", index_label='id')

# Did it work?
myCursor.execute("SELECT adjustedQueryTerm, timesSearched FROM `manual_assignments` limit 10;")
top10 = myCursor.fetchall()
print("\n\nTop 10 by timesSearched:\n {}".format(top10))

# Close the connection. I open and close this when switching between Python
# and DB Browser for SQLite.
conn.close()


#%%
# ========================================================================
# 3. Taxonomy discovery UI: Create a logProcessed table for 
#    http://localhost:5000/taxonomy/ (Use browser to update SQLite table)
# ========================================================================
'''
Not sure how to handle this; re-factor later as needed; need an editor UI 
that improves assignments and makes assigning easier, here, then at the 
end of the processing, we need a taxonomy for 6 or 12 months that allows 
exploration for all analysts. Could have a time drop-down here that allows
user to limit using same table as final...

First creation? db model revisions? - This will determine what you need to 
do here. Early in the project you can use this to make sense of the custom
adds you will need to make.
'''


os.chdir('/Users/wendlingd/Projects/webDS')

logAfterStep4 = pd.read_excel(logAfterStep4)
logAfterStep4.columns
'''
'Referrer', 'Query', 'Date', 'CountForPgDate', 'adjustedQueryTerm',
       'ProbablyMeantGSTerm', 'preferredTerm', 'SemanticType', 'ui'
'''

# Might want to cut down the cols; it will add whatever is in the df.
logAfterStep4 = logAfterStep4[['Query', 'adjustedQueryTerm', 'preferredTerm', 
                                 'SemanticType', 'Referrer', 'Date', 
                                 'CountForPgDate', 'ui']]

'''
If you need to modify the table:

DROP TABLE IF EXISTS logs_processed;
VACUUM;
CREATE TABLE `logs_processed` (`id` integer NOT NULL PRIMARY KEY AUTOINCREMENT, 
`Query` TEXT, `adjustedQueryTerm` TEXT, `preferredTerm` TEXT, `SemanticType` TEXT, 
`Referrer` TEXT, `Date` TEXT, `CountForPgDate` INTEGER, `ui` TEXT);


Add data to table:
'''

# Set working directory for SQLite
os.chdir('/Users/wendlingd/Projects/webDS/_django/loganalysis')

# Open or re-open the database connection
conn = sqlite3.connect("db.sqlite3") # opens sqlite and a database file
myCursor = conn.cursor() # provides a connection to the database

# Replace old data with new
logAfterStep4.to_sql("logs_processed", conn, if_exists="replace", index_label='id')

# Did it work?
myCursor.execute("SELECT SemanticType, adjustedQueryTerm FROM `logs_processed` limit 10;")
top10 = myCursor.fetchall()
print("\n\nExample records:\n {}".format(top10))

# Close the connection. I open and close this when switching between Python
# and DB Browser for SQLite.
conn.close()


'''
Terminal

cd /Users/wendlingd/Projects/webDS/_django/loganalysis

from assignment.models import Processed
python3 manage.py showmigrations
python3 manage.py makemigrations
python3 manage.py migrate


'''


#%%
# ========================================================================
# 3. Process results in browser using http://localhost:5000/MakeAssignments/
#    (Use browser to update SQLite table)
# ========================================================================
'''
To start Django server, from terminal:


    
cd /Users/wendlingd/Projects/webDS/_django/loganalysis
python manage.py runserver

Then open http://localhost:8000/MakeAssignments/ in browser.

Solve top searches as best you can.

Do what you have time for, but don't waste too much time on low-frequency
occurrences. This is primarily to get frequently used terms that aren't in
UMLS.

Then review in http://localhost:8000/MakeAssignments/assignmentVetter. 

This will assign Modifed = 1 on the entries you approve, so you can pull
them in with the below.
'''


#%%
# =====================================================================================
# 4. Update QuirkyMatches and log, from manual_assignments table - logAfterStep4.xlsx
# =====================================================================================
'''
Assign SemanticGroup from PastMatches or other.

FYI, the columns in the database:
    'id', 'adjustedQueryTerm', 'preferredTerm', 'ProbablyMeantGSTerm',
       'SemanticType', 'timesSearched', 'FuzzyScore',
       'NewSemanticType', 'SemanticGroup', 'Modified'
'''

# Set working directory for SQLite
os.chdir('/Users/wendlingd/Projects/webDS/_django/loganalysis')

# Open or re-open the database connection
conn = sqlite3.connect("db.sqlite3") # opens sqlite and a database file
myCursor = conn.cursor() # provides a connection to the database

newManualMatches = pd.read_sql_query("SELECT adjustedQueryTerm, preferredTerm, NewSemanticType FROM manual_assignments WHERE Modified = 1;", conn)

'''
Below closes the connection; I open and close this when switching between Python
and DB Browser for SQLite. You can choose where to do eyeballing and 
editing, if any - df's, DB Browser, Django Admin.
'''
conn.close()

# Good idea to read this table while you're in "building" step, remove null cols, content problems
# newManualMatches.drop(2, inplace=True)

'''
# -- If you need to eyeball for problems and fix, in the df ------------------
newManualMatches.drop(45, inplace=True)
newManualMatches.loc[newManualMatches['adjustedQueryTerm'].str.contains('item', na=False), 'preferredTerm'] = 'item'
'''

# --------------------------
# To move to other instance
# --------------------------

dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily


# Write out for future matching
writer = pd.ExcelWriter(dataInterim + 'newManualMatches.xlsx')
newManualMatches.to_excel(writer,'newManualMatches')
# df2.to_excel(writer,'Sheet2')
writer.save()






# --------------------------
# Update QuirkyMatches.xlsx
# --------------------------

# Reset working directory now that we're done with Django
os.chdir('/Users/wendlingd/Projects/webDS')

# Open QuirkyMatches from step 1
QuirkyMatches = pd.read_excel(QuirkyMatches)

# Append new data
QuirkyMatches = QuirkyMatches.append(newManualMatches, sort=True)

# Write out for future matching
writer = pd.ExcelWriter(dataMatchFiles + 'QuirkyMatches.xlsx')
QuirkyMatches.to_excel(writer,'QuirkyMatches')
# df2.to_excel(writer,'Sheet2')
writer.save()


# ------------------
# Update search log
# ------------------

# Bring in if not already open
logAfterStep4 = pd.read_excel(logAfterStep4)
logAfterStep4.columns
'''
'Referrer', 'Query', 'Date', 'CountForPgDate', 'adjustedQueryTerm',
       'ProbablyMeantGSTerm', 'preferredTerm', 'SemanticType', 'ui'
'''

newManualMatches.columns
'''
'adjustedQueryTerm', 'preferredTerm', 'NewSemanticType'
'''

# Align cols
newManualMatches.rename(columns={'NewSemanticType': 'SemanticType'}, inplace=True)

# Join new adds to the current search log master
logAfterStep4 = pd.merge(logAfterStep4, newManualMatches, how='left', left_on='adjustedQueryTerm', right_on='adjustedQueryTerm')
logAfterStep4.columns
'''
'Referrer', 'Query', 'Date', 'CountForPgDate', 'adjustedQueryTerm',
       'ProbablyMeantGSTerm', 'preferredTerm_x', 'SemanticType_x', 'ui',
       'preferredTerm_y', 'SemanticType_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterStep4['preferredTerm2'] = logAfterStep4['preferredTerm_x'].where(logAfterStep4['preferredTerm_x'].notnull(), logAfterStep4['preferredTerm_y'])
logAfterStep4['preferredTerm2'] = logAfterStep4['preferredTerm_y'].where(logAfterStep4['preferredTerm_y'].notnull(), logAfterStep4['preferredTerm_x'])
logAfterStep4['SemanticType2'] = logAfterStep4['SemanticType_x'].where(logAfterStep4['SemanticType_x'].notnull(), logAfterStep4['SemanticType_y'])
logAfterStep4['SemanticType2'] = logAfterStep4['SemanticType_y'].where(logAfterStep4['SemanticType_y'].notnull(), logAfterStep4['SemanticType_x'])
logAfterStep4.drop(['preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterStep4.rename(columns={'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)

# Re-sort full file
logAfterStep4['adjustedQueryTerm'] = logAfterStep4['adjustedQueryTerm'].astype(str)
logAfterStep4 = logAfterStep4.sort_values(by='adjustedQueryTerm', ascending=True)
logAfterStep4 = logAfterStep4.reset_index()
logAfterStep4.drop(['index'], axis=1, inplace=True)


# Save to file so you can open in future sessions, if needed
writer = pd.ExcelWriter(dataInterim + 'logAfterStep4.xlsx')
logAfterStep4.to_excel(writer,'logAfterStep4')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -------------------------------
# How we doin? Visualize results
# -------------------------------

TotLogEntries = logAfterStep4['CountForPgDate'].sum()

newAssigned = logAfterStep4[['SemanticType', 'CountForPgDate']]
newAssigned = newAssigned[newAssigned['SemanticType'].notnull() == True]
newAssigned = newAssigned['CountForPgDate'].sum()
newUnassigned = TotLogEntries - newAssigned

PercentAssigned = (newAssigned / TotLogEntries) * 100

quickCounts = logAfterStep4['SemanticType'].value_counts()

print("\n\n======================================================\n ** logAfterStep4 stats **\n======================================================\n\n{:,}% of search traffic classified\n{:,} queries in searchLog;\n{:,} assigned / {:,} unassigned".format(round(PercentAssigned), TotLogEntries, newAssigned, newUnassigned))
print("\nTop Semantic Types\n{}".format(logAfterStep4['SemanticType'].value_counts().head(10)))


# viz --------------
# Pie of status
labels = ['Assigned', 'Unassigned']
sizes = [newAssigned, newUnassigned]
colors = ['steelblue', '#fc8d59']
explode = (0.1, 0)  # explode 1st slice
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'Step 4' processing - \n{:,} queries with {:,} unassigned".format(TotLogEntries, newUnassigned))
plt.show()

plt.savefig(reports + 'Search-StatusAfterStep4.png')


# viz --------------
# Bar of SemanticType categories, horizontal
ax = logAfterStep4['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(10,6), color="steelblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'Step 4' processing \nwith {:,} of {:,} unassigned".format(newUnassigned, TotLogEntries), fontsize=14)
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

plt.savefig(reports + 'Search-SemTypesAfterStep4.png')


#%%
# ===========================================================
# 5. Create new 'uniques' - uniqueUnassignedAfterStep4.xlsx
# ===========================================================

# Unique queries with no assignments
uniqueUnassignedAfterStep4 = logAfterStep4[pd.isnull(logAfterStep4['SemanticType'])]
uniqueUnassignedAfterStep4 = uniqueUnassignedAfterStep4.groupby('adjustedQueryTerm').size()
uniqueUnassignedAfterStep4 = pd.DataFrame({'timesSearched':uniqueUnassignedAfterStep4})
uniqueUnassignedAfterStep4 = uniqueUnassignedAfterStep4.sort_values(by='timesSearched', ascending=False)
uniqueUnassignedAfterStep4 = uniqueUnassignedAfterStep4.reset_index()

# Send to file to preserve
writer = pd.ExcelWriter(dataInterim + 'uniqueUnassignedAfterStep4.xlsx')
uniqueUnassignedAfterStep4.to_excel(writer,'unassignedToCheck')
writer.save()


#%%

# OBSOLETED?


'''
# Unique unassigned terms and frequency of occurrence
listOfUniqueUnassignedAfterFuzzy1 = combinedLogs[pd.isnull(combinedLogs['preferredTerm'])] # was SemanticGroup
listOfUniqueUnassignedAfterFuzzy1 = listOfUniqueUnassignedAfterFuzzy1.groupby('adjustedQueryTerm').size()
listOfUniqueUnassignedAfterFuzzy1 = pd.DataFrame({'timesSearched':listOfUniqueUnassignedAfterFuzzy1})
listOfUniqueUnassignedAfterFuzzy1 = listOfUniqueUnassignedAfterFuzzy1.sort_values(by='timesSearched', ascending=False)
listOfUniqueUnassignedAfterFuzzy1 = listOfUniqueUnassignedAfterFuzzy1.reset_index()



# FIXME - Problem with Django; fix there and remove this workaround
# FIXME - Reset index and name column assignment_id.;

# FuzzyWuzzyProcResult4 = FuzzyWuzzyProcResult4.reset_index()
# FuzzyWuzzyProcResult4.rename(columns={'index': 'id'}, inplace=True)

# Assigned = (logAfterStep4['preferredTerm'].values != '').sum()
# Unassigned = (logAfterStep4['preferredTerm'].values == '').sum()
'''


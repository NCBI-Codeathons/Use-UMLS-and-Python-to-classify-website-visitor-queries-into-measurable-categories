#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 09:20:01 2018

@authors: dan.wendling@nih.gov, 

Last modified: 2019-10-16

** Site-search log file analyzer, Part 1 **

This script: Import search log from Google Analytics custom report, clean up, 
match query entries against historical files. This is the only script of the 
set that can be run automatically, with no human intervention, if desired.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Create dataframe from search log; globally update columns and rows
3. Show baseline stats for this dataset
4. Clean up content to improve matching
5. Assign non-Roman characters to Foreign unresolved, match to umlsTermListForeign
6. Make special-case assignments with F&R, RegEx: Bibliographic, Numeric, Named entities
7. Do an exact match to umlsTermListEnglish
8. Match to "gold standard," successful and vetted past matches
9. Apply matches from HighConfidenceGuesses.xlsx
10. Create new high-confidence guesses with FuzzyWuzzy
11. Apply matches from QuirkyMatches.xlsx
12. Create 'uniques' dataframe/file for APIs

12. If working with multiple processed logs at once


---------------
LOG APPEARANCE
---------------

This script processes logs that looks similar to the below, that is exported
from a Google Analytics custom report (https://support.google.com/analytics/answer/1151300?hl=en):

| Start Page      | Search Term       | Date     | Total Unique Searches
| www.mysite.gov/ | sequence analysis | 20181213 | 6


Column descriptions; these should never be empty.
    
Start Page - The page the web visitor was on when she/he used site search. 
    Not required for this tool, but my homepage is a HUGE search outlier that I 
    like to analyze separately. And if you end up drilling down from the 
    visualizations, this could be informative.
Search Term - What was searched; can be any length.
Date - Date GA assigned to the search as year month date; used for time 
    series charts.
Total Unique Searches - Number of times that term was seearched from that
    page on that date.

You can create something similar if you are not using GA; if you follow the 
above, the code in this package should work. GA lacks the ability to put 
consecutive searches back into sessions, 

Other search log analyzers do things like this, some of which you can add as 
custom dimensions in GA (https://support.google.com/analytics/answer/2709829?hl=en#set_up_custom_dimensions),
or there are GA custom reports for
- Visits that a page got with, and without, a search being requested from the page
- Percent of sessions that include a search (would be nice to have this on page level)
- Pages with high ratio of searches for the pageviews
- Searches per session; how many visitors searched from this page
- Look at search refinements; how many, look at what content people are doing variations on
Look where people exit - in search results, after one jump from search results, etc.
Time of day FOR THE VISITOR's search. When during their day are they searching your site?
- https://www.optimizesmart.com/correctly-evaluating-google-analytics-traffic-hour-day-conversion-optimization/
- https://www.optimizesmart.com/how-to-correctly-measure-conversion-date-time-in-google-analytics/

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
import string
import requests
import json
import lxml.html as lh
from lxml.html import fromstring
import time
from fuzzywuzzy import fuzz, process

'''
Before running script, copy the following new files to /data/raw/search/; 
adjust names below, if needed.
'''

# Set working directory and directories for read/write
os.chdir('/Users/name/Projects/semanticsearch')

dataRaw = 'data/raw/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
dataInterim = 'data/interim/' # Save to disk as desired, to re-start easily
reports = 'reports/'

# Specific files you'll need
logFileName = 'SiteSearch2019-05' # newest log - without .csv (added below)
PastMatches = dataMatchFiles + 'PastMatches.xlsx' # historical file of vetted successful matches
HighConfidenceGuesses = dataMatchFiles + 'HighConfidenceGuesses.xlsx' # Automatically matched even though a few characters off
QuirkyMatches = dataMatchFiles + 'QuirkyMatches.xlsx' # Human-chosen terms that might be misspelled, foreign, etc.
umlsTermListForeign = dataMatchFiles + 'umlsTermListForeign.csv'
umlsTermListEnglish = dataMatchFiles + 'umlsTermListEnglish.csv'


#%%
# ======================================================================
# 2. Create dataframe from search log; globally update columns and rows
# ======================================================================
'''
If you need to concat multiple files, one option is
searchLog = pd.concat([x1, x2, x3], ignore_index=True)
'''

# Open; I export with GA headers in case I need to ID the data later
searchLog = pd.read_csv(dataRaw + logFileName + '.csv', sep=',', skiprows=7, index_col=False,
                        names=['Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate'])


# Dupe off Query column into lower-cased 'adjustedQueryTerm', which will
# be the column to clean up and match against
searchLog['adjustedQueryTerm'] = searchLog['Query'].str.lower()

# Remove incomplete rows, if any, which can cause errors later
searchLog = searchLog[~pd.isnull(searchLog['Referrer'])]
searchLog = searchLog[~pd.isnull(searchLog['Query'])]

# Add cols
searchLog['SemanticType'] = ""
searchLog['preferredTerm'] = ""

# Make Date recognizable to Python
searchLog['Date'] = pd.to_datetime(searchLog['Date'].astype(str), format='%Y%m%d')

# Eyeball beginning and end of log and remove partial weeks if needed.
# One week is Sunday through Saturday.



#%%
# ================================================================
# 3. Show baseline stats for this dataset
# ================================================================
'''
Before we start altering content, what are we dealing with?
Partly parallel to a section in the "Chart the trends" script.
'''

# Total queries in log
TotQueries = searchLog['CountForPgDate'].sum()

# Row count / Number of days you have data for
TotDaysCovered = searchLog['Date'].nunique()

# Avg searches per day
AvgSearchesPerDay = round(TotQueries / TotDaysCovered, 0)

# Searches by day for bar chart
searchesByDay = searchLog.groupby('Date').agg(['sum']).reset_index()

# How to shorten dates?
# https://stackoverflow.com/questions/30133280/pandas-bar-plot-changes-date-format

'''
# viz -------------- (not displaying correctly, I want counts on bars)
# FIXME - Multi-index problem?
ax = searchesByDay.plot(x='Date', y='CountForPgDate', kind='bar', figsize=(11,6))
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Search Count by Day", fontsize=18)
ticklabels = searchesByDay['Date'].dt.strftime('%Y-%m-%d')
ax.xaxis.set_major_formatter(mtick.FixedFormatter(ticklabels))
ax.autofmt_xdate()
ax.set_xlabel("Day", fontsize=7)
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.1, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
plt.gcf().subplots_adjust(bottom=0.5)
plt.show()

plt.savefig(reports + 'Search-ByDay-WholeNewDS.png')
'''


# Top x directory folders (often content group) searched from and % share
searchesByReferrerDir = searchLog[['Referrer', 'CountForPgDate']]
# Derive the path (lop off the file name)
# rsplit generates SettingwithCopyWarning msg, says use .loc. Suppressing the msg.
pd.options.mode.chained_assignment = None
searchesByReferrerDir['path'] = [u.rsplit("/", 1)[0] for u in searchesByReferrerDir["Referrer"]]
# Drop Referrer col
searchesByReferrerDir.drop('Referrer', axis=1, inplace=True)
searchesByReferrerDir = searchesByReferrerDir.groupby('path').agg(['sum']).reset_index()
searchesByReferrerDir.columns = searchesByReferrerDir.columns.droplevel() # remove multi-index
searchesByReferrerDir.columns = ['path', 'Count']
searchesByReferrerDir = searchesByReferrerDir.sort_values(by='Count', ascending=False).reset_index(drop=True)
searchesByReferrerDir['PercentShare'] = round(searchesByReferrerDir.Count / TotQueries * 100, 1)
searchesByReferrerDir['path'] = searchesByReferrerDir['path'].str.replace('^www.nlm.nih.gov$', '(site root)') # shorten
searchesByReferrerDir['path'] = searchesByReferrerDir['path'].str.replace('www.nlm.nih.gov', '') # shorten
searchesByReferrerDir = searchesByReferrerDir.head(n=10)


# Top x pages searched from, and their % search share
searchesByReferrerPg = searchLog[['Referrer', 'CountForPgDate']]
searchesByReferrerPg = searchesByReferrerPg.groupby('Referrer').agg(['sum']).reset_index()
searchesByReferrerPg.columns = searchesByReferrerPg.columns.droplevel() # remove multi-index
searchesByReferrerPg.columns = ['Referrer', 'Count']
searchesByReferrerPg = searchesByReferrerPg.sort_values(by='Count', ascending=False).reset_index(drop=True)
searchesByReferrerPg['PercentShare'] = round(searchesByReferrerPg.Count / TotQueries * 100, 1)
searchesByReferrerPg['Referrer'] = searchesByReferrerPg['Referrer'].str.replace('^www.nlm.nih.gov/$', '(home page)') # shorten
searchesByReferrerPg['Referrer'] = searchesByReferrerPg['Referrer'].str.replace('www.nlm.nih.gov', '') # shorten
searchesByReferrerPg = searchesByReferrerPg.head(n=10)


# Top x items searched, percent share
TermReport = searchLog.groupby(['adjustedQueryTerm'])['CountForPgDate'].sum().sort_values(ascending=False).reset_index()
TermReport['PercentShare'] = round(TermReport.CountForPgDate / TotQueries * 100, 1)
TermReport.rename(columns={'CountForPgDate': 'Count'}, inplace=True)
TermReport = TermReport.head(n=25)

# Might aid the display
# pd.options.display.max_columns = None


# Show
print("\n\n=====================================================\n ** Baseline stats - {} **\n=====================================================\n\n{:,} search queries from {} days; ~ {:,} searches/day".format(logFileName, TotQueries, TotDaysCovered, AvgSearchesPerDay))
print("\nPage report: Top 10 FOLDERS where searches are occurring, by percent share of total searches\n\n{}".format(searchesByReferrerDir))
print("\nPage report: Top 10 PAGES where searches are occurring, by percent share of total searches\n\n{}".format(searchesByReferrerPg))
print("\nTerm report: Top 25 TERMS searched with percent share, by literal string\n\n{}".format(TermReport))


#%%
# ========================================
# 4. Clean up content to improve matching
# ========================================
'''
NOTE: Be careful what you remove, because the data you're matching to, DOES
CONTAIN non-alpha-numeric characters such as %.

Future: Later there is discussion of the UMLS file, MRCONSO.RRF; get a list 
of non-alpha-numeric characters used, then decide which ones in visitor 
queries cause more trouble than they're worth. Faster but 
may damage your ability to match:
    searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.extract('(\w+)', expand = False)
'''


"""
TODO - Easier to edit:
    stuffToUpdate = [ 
        ('<AUTHORS>', '<AUTHORS><AUTHOR>'),
        ('</AUTHORS>', '</AUTHOR></AUTHORS>'),
        ('<KEYWORDS>', '<KEYWORDS><KEYWORD>'),
        ('</KEYWORDS>', '</KEYWORD></KEYWORDS>'),
        (' & ', ' and ')
        ]

for txtIn, txtOut in stuffToUpdate:
    nowAString = nowAString.replace(txtIn, txtOut)
    
But, could separate into removals and replaces...
"""



# Remove selected punctuation...
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('"', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("'", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("`", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('(', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace(')', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('.', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace(',', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('!', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('*', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('$', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('+', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('?', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('~', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('!', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('#', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace(':', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace(';', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('{', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('}', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('|', '')
# Remove control characters
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\^', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\[', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\]', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\<', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\>', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('\\', '')
# Remove high ascii etc.
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('•', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("“", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("”", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("‘", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("«", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("»", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("»", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("¿", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("®", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("™", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("¨", "")
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace("（", "(")

# searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('-', '')
# searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('%', '')

# First-character issues
# searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^[0-9]{4}") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^-") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^/") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^@") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^;") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^<") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^>") == False] # char entities

# If removing punct caused a preceding space, remove the space.
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^  ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^ ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^ ', '')

# Drop junk rows with entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.startswith("&#") == False] # char entities
searchLog = searchLog[searchLog.adjustedQueryTerm.str.contains("^&[0-9]{4}") == False] # char entities
# Alternatively, could use searchLog = searchLog[(searchLog.adjustedQueryTerm != '&#')

# Remove modified entries that are now dupes or blank entries
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('  ', ' ') # two spaces to one
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.strip() # remove leading and trailing spaces
searchLog = searchLog.loc[(searchLog['adjustedQueryTerm'] != "")]


# Test - Does the following do anything, good or bad? Can't tell. Remove non-ASCII; https://www.quora.com/How-do-I-remove-non-ASCII-characters-e-g-%C3%90%C2%B1%C2%A7%E2%80%A2-%C2%B5%C2%B4%E2%80%A1%C5%BD%C2%AE%C2%BA%C3%8F%C6%92%C2%B6%C2%B9-from-texts-in-Panda%E2%80%99s-DataFrame-columns
# I think a previous operation converted these already, for example, &#1583;&#1608;&#1588;&#1606;
# def remove_non_ascii(Query):
#    return ''.join(i for i in Query if ord(i)<128)
# testingOnly = uniqueSearchTerms['Query'] = uniqueSearchTerms['Query'].apply(remove_non_ascii)
# Also https://stackoverflow.com/questions/20078816/replace-non-ascii-characters-with-a-single-space?rq=1

# Remove starting text that can complicate matching
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^benefits of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^cause of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^cause for ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^causes of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^causes for ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^definition for ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^definition of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^effect of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^etiology of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^symptoms of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^treating ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^treatment for ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^treatments for ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^treatment of ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^what are ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^what causes ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^what is a ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^what is ', '')

# Should investigate how this happens? Does one browser not remove "search" from input?
# Examples: search ketamine, searchmedline, searchcareers, searchtuberculosis
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^search ', '')
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^search', '')

# Is this one different than the above? Such as, pathology of the lung
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('^pathology of ', '')

# Space clean-up as needed
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.replace('  ', ' ') # two spaces to one
searchLog['adjustedQueryTerm'] = searchLog['adjustedQueryTerm'].str.strip() # remove leading and trailing spaces
searchLog = searchLog.loc[(searchLog['adjustedQueryTerm'] != "")]

# searchLog.head()
searchLog.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'SemanticType', 'preferredTerm'
'''


#%%
# ====================================================================================
# 5. Assign non-Roman characters to Foreign unresolved, match to umlsTermListForeign
# ====================================================================================
'''
The local UMLS files can process non-Roman languages (Chinese, Cyrillic, etc.),
but the API cannot. Flag these so later you can remove them from the API 
request lists; no point trying to match something unmatchable.

Don't change placement; this will wipe both preferredTerm and SemanticType.
Future procedures can replace this content, which is fine.

FIXME - Some of these are not foreign; R&D how to avoid assigning as foreign;
start by seeing whether orig term had non-ascii characters. 

Mistaken assignments that are 1-4-word single-concept searches will be overwritten with 
the correct data. And a smaller number of other types will be reclaimed as well.
- valuation of fluorescence in situ hybridization as an ancillary tool to urine cytology in diagnosing urothelial carcinoma
- comparison of a light‐emitting diode with conventional light sources for providing phototherapy to jaundiced newborn infants
- crystal structure of ovalbumin
- diet exercise or diet with exercise 18–65 years old

2019-08: Matched UMLS to log at 141 unique terms of 2749, ~5% of foreign uniques.
'''

def checkForeign(row):
    # print(row)
    foreignYes = {'adjustedQueryTerm':row.adjustedQueryTerm, 'preferredTerm':'Foreign unresolved', 'SemanticType':'Foreign unresolved'}
    foreignNo = {'adjustedQueryTerm':row.adjustedQueryTerm, 'preferredTerm':'','SemanticType':''}
    try:
       row.adjustedQueryTerm.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
       return pd.Series(foreignYes)
    else:
       # return row
       return pd.Series(foreignNo)
   
searchLog[['adjustedQueryTerm', 'preferredTerm','SemanticType']] = searchLog.apply(checkForeign, axis=1)

# ForeignCounts = searchLog['SemanticType'].value_counts()

# Attempt an exact match to UMLS foreign terms. Intentionally overwrites SemanticType == 'Foreign unresolved'

# Create list of log uniques where SemanticType = 'Foreign unresolved'
foreignAgainstUmls = searchLog.loc[searchLog['SemanticType'] == 'Foreign unresolved']
foreignAgainstUmls = foreignAgainstUmls.groupby('adjustedQueryTerm').size()
foreignAgainstUmls = pd.DataFrame({'timesSearched':foreignAgainstUmls})
foreignAgainstUmls = foreignAgainstUmls.sort_values(by='timesSearched', ascending=False)
foreignAgainstUmls = foreignAgainstUmls.reset_index()

# Open ~1.7 million row file
umlsTermListForeign = pd.read_csv(umlsTermListForeign, sep='|')
umlsTermListForeign.columns
'''
'preferredTerm', 'ui', 'SemanticType', 'wordCount'
'''

# Reduce to matches
foreignUmlsMatches = pd.merge(foreignAgainstUmls, umlsTermListForeign, how='inner', left_on=['adjustedQueryTerm'], right_on=['preferredTerm'])
foreignUmlsMatches.columns
'''
'adjustedQueryTerm', 'timesSearched', 'preferredTerm', 'ui',
       'SemanticType', 'wordCount'
'''

# Reduce cols
foreignUmlsMatches = foreignUmlsMatches[['adjustedQueryTerm', 'preferredTerm', 'ui', 'SemanticType']]

# Combine with searchLog
logAfterForeign = pd.merge(searchLog, foreignUmlsMatches, how='left', left_on=['adjustedQueryTerm', 'preferredTerm', 'SemanticType'], right_on=['adjustedQueryTerm', 'preferredTerm', 'SemanticType'])
logAfterForeign.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'SemanticType', 'preferredTerm', 'ui'
'''

# searchLog
del [[searchLog, umlsTermListForeign, foreignAgainstUmls]]


#%%
# =========================================================================================
# 6. Make special-case assignments with F&R, RegEx: Bibliographic, Numeric, Named entities
# =========================================================================================
'''
Later procedures can't match the below very well, so match them here.
'''

'''
If you think one page is skewing results - an outlier, maybe you'll want special handling.

outlierCheck = logAfterForeign[logAfterForeign.Referrer.str.contains("/bsd/pmresources.html") == True]
outlierCheck = logAfterForeign['Query'].value_counts()
outlierCheck = pd.DataFrame({'Count':outlierCheck})
outlierCheck = outlierCheck.reset_index()
outlierCheck = outlierCheck.head(n=25)
outlierCheck['PercentShare'] = outlierCheck.Count / TotQueries * 100
print("\nTop searches with percent share\n{}".format(outlierCheck))

# You can make these a separate category with something like,
logAfterForeign.loc[logAfterForeign['Referrer'].str.contains('/bsd/pmresources.html'), 'preferredTerm'] = 'pmresources.html'
'''


# --- Bibliographic Entity ---
# Assign ALL queries over x char to 'Bibliographic Entity' (often citations, search strategies, publication titles...)
logAfterForeign.loc[(logAfterForeign['adjustedQueryTerm'].str.len() > 30), 'preferredTerm'] = 'Bibliographic Entity'

# logAfterForeign.loc[(logAfterForeign['adjustedQueryTerm'].str.len() > 25) & (~logAfterForeign['preferredTerm'].str.contains('pmresources.html', na=False)), 'preferredTerm'] = 'Bibliographic Entity'

# Search strategies might also be in the form "clinical trial" and "step 0"
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('[a-z]{3,}" and "[a-z]{3,}', na=False), 'preferredTerm'] = 'Bibliographic Entity'

# Search strategies might also be in the form "clinical trial" and "step 0"
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('[a-z]{3,}" and "[a-z]{3,}', na=False), 'preferredTerm'] = 'Bibliographic Entity'

# Queries about specific journal titles
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('^journal of', na=False), 'preferredTerm'] = 'Bibliographic Entity'
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('^international journal of', na=False), 'preferredTerm'] = 'Bibliographic Entity'

# Add SemanticType
logAfterForeign.loc[logAfterForeign['preferredTerm'].str.contains('Bibliographic Entity', na=False), 'SemanticType'] = 'Bibliographic Entity' # 'Intellectual Product'


# --- Numeric ID ---
# Assign entries starting with 3 digits
# FIXME - Clarify and grab the below, PMID, ISSN, ISBN 0-8016-5253-7), etc.
# logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('^[0-9]{3,}', na=False), 'preferredTerm'] = 'Numeric ID'
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('[0-9]{5,}', na=False), 'preferredTerm'] = 'Numeric ID'
logAfterForeign.loc[logAfterForeign['adjustedQueryTerm'].str.contains('[0-9]{4,}-[0-9]{4,}', na=False), 'preferredTerm'] = 'Numeric ID'

# Add SemanticType
logAfterForeign.loc[logAfterForeign['preferredTerm'].str.contains('Numeric ID', na=False), 'SemanticType'] = 'Numeric ID'


'''
# When experimenting it's useful to write out a cleaned up version; if you 
# do re-processing, you can skip a bunch of work.
writer = pd.ExcelWriter(dataInterim + 'logAfterForeign.xlsx')
logAfterForeign.to_excel(writer,'logAfterForeign')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

# -------------
# How we doin?
# -------------

rowCount = len(logAfterForeign)
TotUniqueEntries = logAfterForeign['adjustedQueryTerm'].nunique()

Assigned = (logAfterForeign['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = (logAfterForeign['SemanticType'].values == '').sum() # .isnull().sum()
PercentAssigned = round(Assigned / TotUniqueEntries * 100)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterForeign['SemanticType'].value_counts().head(10)))
print("\n\n=================================================\n ** logAfterForeign stats - {} **\n=================================================\n\n{}% of rows unclassified / {}% classified\n{:,} unique queries in logAfterForeign;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), TotQueries, Unassigned, Assigned))


#%%
# ====================================================================
# 7. Do an exact match to umlsTermListEnglish
# ====================================================================
'''
Optional. Attempt local exact matching against 3.7-million-term UMLS file. 
Because of the license agreement this file will not be shared, but it is a 
combination of MRCONSO.RFF and MRSTY.RRF that is reduced to only the 
preferred "atom" for each concept (CUI) in the vocabulary, and each concept 
includes its semantic type assignment(s). Saves a lot of time with the API, 
but not necessary for the project.

Restart?
logAfterForeign = pd.read_excel('01_Import-transform_files/logAfterForeign.xlsx')
'''

# Reviewing from above
logAfterForeign.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'SemanticType', 'preferredTerm', 'ui'
'''

# ~3.2 million rows. To see what this HUGE df contains
# ViewSomeUmlsTerms = umlsTermListEnglish[10000:10500]
umlsTermListEnglish = pd.read_csv(umlsTermListEnglish, sep='|') # , index_col=False
umlsTermListEnglish.drop('wordCount', axis=1, inplace=True)
umlsTermListEnglish.columns
'''
'preferredTerm', 'ui', 'SemanticType'
'''

# Combine
logAfterUmlsTerms = pd.merge(logAfterForeign, umlsTermListEnglish, how='left', left_on=['adjustedQueryTerm'], right_on=['preferredTerm'])
logAfterUmlsTerms.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'SemanticType_x', 'preferredTerm_x', 'ui_x',
       'preferredTerm_y', 'ui_y', 'SemanticType_y'
'''

# numpy.where(condition[, x, y])
# logAfterUmlsTerms['SemanticType2'] = np.where(logAfterUmlsTerms.SemanticType_x.isna(), logAfterUmlsTerms.SemanticType_y, logAfterUmlsTerms.SemanticType_x)


# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterUmlsTerms['ui2'] = logAfterUmlsTerms['ui_x'].where(logAfterUmlsTerms['ui_x'].notnull(), logAfterUmlsTerms['ui_y'])
logAfterUmlsTerms['ui2'] = logAfterUmlsTerms['ui_y'].where(logAfterUmlsTerms['ui_y'].notnull(), logAfterUmlsTerms['ui_x'])
logAfterUmlsTerms['preferredTerm2'] = logAfterUmlsTerms['preferredTerm_x'].where(logAfterUmlsTerms['preferredTerm_x'].notnull(), logAfterUmlsTerms['preferredTerm_y'])
logAfterUmlsTerms['preferredTerm2'] = logAfterUmlsTerms['preferredTerm_y'].where(logAfterUmlsTerms['preferredTerm_y'].notnull(), logAfterUmlsTerms['preferredTerm_x'])
logAfterUmlsTerms['SemanticType2'] = logAfterUmlsTerms['SemanticType_x'].where(logAfterUmlsTerms['SemanticType_x'].notnull(), logAfterUmlsTerms['SemanticType_y'])
logAfterUmlsTerms['SemanticType2'] = logAfterUmlsTerms['SemanticType_y'].where(logAfterUmlsTerms['SemanticType_y'].notnull(), logAfterUmlsTerms['SemanticType_x'])
logAfterUmlsTerms.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y', 'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterUmlsTerms.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)
    
    
'''
# Adjust cols
logAfterUmlsTerms.drop(['ui_x', 'preferredTerm_y'], axis=1, inplace=True)
logAfterUmlsTerms.rename(columns={'preferredTerm_x':'preferredTerm'}, inplace=True)

# Attempting to remove all traces of 3.6-million-row df from memory, and logAfterForeign
# is no longer needed. Assuming this is correct:
# https://stackoverflow.com/questions/32247643/how-to-delete-multiple-pandas-python-dataframes-from-memory-to-save-ram
'''

del [[foreignUmlsMatches, logAfterForeign, umlsTermListEnglish, TermReport]]

'''
# Write out the work so far
writer = pd.ExcelWriter(dataInterim + 'logAfterUmlsTerms.xlsx')
logAfterUmlsTerms.to_excel(writer,'logAfterUmlsTerms')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

# -------------
# How we doin?
# -------------
rowCount = len(logAfterUmlsTerms)
TotUniqueEntries = logAfterUmlsTerms['adjustedQueryTerm'].nunique()

Assigned = (logAfterUmlsTerms['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterUmlsTerms['SemanticType'].value_counts().head(10)))
print("\n\n=====================================================\n ** umlsTermListEnglish stats - {} **\n=====================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


# -----------------
# Visualize results
# -----------------
'''
# Interesting to run but may disrupt auto-run

# Pie for percentage of rows assigned
Assigned = (logAfterUmlsTerms['preferredTerm'].values != '').sum()
Unassigned = (logAfterUmlsTerms['preferredTerm'].values == '').sum()
labels = ['Assigned', 'Unassigned']
sizes = [Assigned, Unassigned]
colors = ['steelblue', '#fc8d59'] # more intense-#FF7F0E; lightcoral #FF9966
explode = (0.1, 0)  # explode 1st slice
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'UmlsTerms' processing - \n{:,} queries with {:,} unassigned".format(TotUniqueEntries, Unassigned))
plt.show()


# Bar of SemanticType categories, horizontal
# 
ax = logAfterUmlsTerms['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(8,6),
                                                 color="steelblue", fontsize=10); # slateblue
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'UmlsTerms' \nprocessing with {:,} of {:,} unassigned".format(Unassigned, TotUniqueEntries), fontsize=14)
ax.set_xlabel("Number of searches", fontsize=9);
ax.set_ylabel("Number of searches", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.31, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.5)
'''

#%%
# ================================================================
# 8. Match to "gold standard," successful and vetted past matches
# ================================================================
'''
Attempt exact matches to previously successful matches that are commonly 
searched or specific to this site. Over time this will lighten the manual 
work in later steps. You should add to, and occasionally edit, this "Gold 
Standard" to improve future matching (more work at beginning). This file can 
be supplemented with entity extraction of web page content, lists of 
product/service names, organization department names, etc. But do use 
correct spellings, because later we fuzzy match off of this. QuirkyMatches 
will have common misspellings.

Restart:
logAfterUmlsTerms = pd.read_excel(dataInterim + 'logAfterUmlsTerms.xlsx')
'''

# Review
logAfterUmlsTerms.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'ui', 'preferredTerm', 'SemanticType'
'''

# Bring in file containing this site's historical matches
PastMatches = dataMatchFiles + 'PastMatches.xlsx' # historical file of vetted successful matches
PastMatches = pd.read_excel(PastMatches)
PastMatches.columns
'''
'SemanticType', 'adjustedQueryTerm', 'preferredTerm', 'ui'
'''

# Not getting expected matches; is the col type mixed? Looks like from checking df
# logAfterUmlsTerms['adjustedQueryTerm'] = logAfterUmlsTerms['adjustedQueryTerm'].astype(str)



# Combine based on PastMatches.adjustedQueryTerm
logAfterPastMatches = pd.merge(logAfterUmlsTerms, PastMatches, left_on=['adjustedQueryTerm'], right_on=['preferredTerm'], how='left')
logAfterPastMatches.columns

# adjustedQueryTerm_y will not be needed; otherwise same update as above
logAfterPastMatches.drop(['adjustedQueryTerm_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'adjustedQueryTerm_x':'adjustedQueryTerm'}, inplace=True)

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:  If _x is empty, move _y into it
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_x'].where(logAfterPastMatches['ui_x'].notnull(), logAfterPastMatches['ui_y'])
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_y'].where(logAfterPastMatches['ui_y'].notnull(), logAfterPastMatches['ui_x'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_x'].where(logAfterPastMatches['preferredTerm_x'].notnull(), logAfterPastMatches['preferredTerm_y'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_y'].where(logAfterPastMatches['preferredTerm_y'].notnull(), logAfterPastMatches['preferredTerm_x'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_x'].where(logAfterPastMatches['SemanticType_x'].notnull(), logAfterPastMatches['SemanticType_y'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_y'].where(logAfterPastMatches['SemanticType_y'].notnull(), logAfterPastMatches['SemanticType_x'])
logAfterPastMatches.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)

# Reclaim text cols as strings
# logAfterPastMatches = logAfterPastMatches.astype({'adjustedQueryTerm': str, 'ui': str, 'preferredTerm': str, 'SemanticType': str})


# Combine based on PastMatches.adjustedQueryTerm
logAfterPastMatches = pd.merge(logAfterUmlsTerms, PastMatches, how='left', left_on=['adjustedQueryTerm'], right_on=['adjustedQueryTerm'])
logAfterPastMatches.columns
'''
'Unnamed: 0', 'Referrer', 'Query', 'Date', 'SessionID',
       'CountForPgDate', 'adjustedQueryTerm', 'ui_x', 'preferredTerm_x',
       'SemanticType_x', 'SemanticType_y', 'preferredTerm_y', 'ui_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. 
# Temporary fix: Move _y into _x if _x is empty; or here: where _x has content, use _x, otherwise use _y
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_x'].where(logAfterPastMatches['ui_x'].notnull(), logAfterPastMatches['ui_y'])
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_y'].where(logAfterPastMatches['ui_y'].notnull(), logAfterPastMatches['ui_x'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_x'].where(logAfterPastMatches['preferredTerm_x'].notnull(), logAfterPastMatches['preferredTerm_y'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_y'].where(logAfterPastMatches['preferredTerm_y'].notnull(), logAfterPastMatches['preferredTerm_x'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_x'].where(logAfterPastMatches['SemanticType_x'].notnull(), logAfterPastMatches['SemanticType_y'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_y'].where(logAfterPastMatches['SemanticType_y'].notnull(), logAfterPastMatches['SemanticType_x'])

logAfterPastMatches.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)


# -------------
# How we doin?
# -------------
rowCount = len(logAfterPastMatches)
TotUniqueEntries = logAfterPastMatches['adjustedQueryTerm'].nunique()

# Assigned = logAfterPastMatches['SemanticType'].count()
Assigned = (logAfterPastMatches['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterPastMatches['SemanticType'].value_counts().head(15)))
print("\n\n=====================================================\n ** logAfterPastMatches stats - {} **\n=====================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))

    
# Remove from memory. But PastMatches is used below, so leave that.
# del [[]]


#%%
# =================================================
# 8. Apply matches from HighConfidenceGuesses.xlsx
# =================================================
'''
This data comes from fuzzy matching later on; some of these can be sketchy,
so they are separated from "gold standard" matches. Entries here can be 
proper names, misspellings, foreign terms, that Python FuzzyWuzzy scored at 
90% or higher - just a few characters off from what the UMLS is able to 
match to, or what can be read from the web site spidering that made it into 
the PastMatches. You should edit this file a bit more frequently than you 
edit the PastMatches file; these are automatically assigned.
'''

# Bring in historical file of lightly edited matches
HighConfidenceGuesses = dataMatchFiles + 'HighConfidenceGuesses.xlsx' # Automatically matched even though a few characters off
HighConfidenceGuesses = pd.read_excel(HighConfidenceGuesses)

# FIXME - Update in file
HighConfidenceGuesses.rename(columns={'SemanticTypeName': 'SemanticType'}, inplace=True)
    

logAfterHCGuesses = pd.merge(logAfterPastMatches, HighConfidenceGuesses, left_on='adjustedQueryTerm', right_on='adjustedQueryTerm', how='left')
logAfterHCGuesses.columns
'''
'Unnamed: 0_x', 'Referrer', 'Query', 'Date', 'SessionID',
       'CountForPgDate', 'adjustedQueryTerm', 'Unnamed: 0_y', 'ui_x',
       'preferredTerm_x', 'SemanticType_x', 'Unnamed: 0',
       'ProbablyMeantGSTerm', 'SemanticType_y', 'preferredTerm_y', 'ui_y'
'''

# FIXME - Set Excel to stop exporting and import index col
# logAfterHCGuesses.drop(['Unnamed: 0_x', 'Unnamed: 0_y', 'Unnamed: 0'], axis=1, inplace=True)

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterHCGuesses['ui2'] = logAfterHCGuesses['ui_x'].where(logAfterHCGuesses['ui_x'].notnull(), logAfterHCGuesses['ui_y'])
logAfterHCGuesses['ui2'] = logAfterHCGuesses['ui_y'].where(logAfterHCGuesses['ui_y'].notnull(), logAfterHCGuesses['ui_x'])
logAfterHCGuesses['preferredTerm2'] = logAfterHCGuesses['preferredTerm_x'].where(logAfterHCGuesses['preferredTerm_x'].notnull(), logAfterHCGuesses['preferredTerm_y'])
logAfterHCGuesses['preferredTerm2'] = logAfterHCGuesses['preferredTerm_y'].where(logAfterHCGuesses['preferredTerm_y'].notnull(), logAfterHCGuesses['preferredTerm_x'])
logAfterHCGuesses['SemanticType2'] = logAfterHCGuesses['SemanticType_x'].where(logAfterHCGuesses['SemanticType_x'].notnull(), logAfterHCGuesses['SemanticType_y'])
logAfterHCGuesses['SemanticType2'] = logAfterHCGuesses['SemanticType_y'].where(logAfterHCGuesses['SemanticType_y'].notnull(), logAfterHCGuesses['SemanticType_x'])
logAfterHCGuesses.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterHCGuesses.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)


# -------------
# How we doin?
# -------------
rowCount = len(logAfterHCGuesses)
TotUniqueEntries = logAfterHCGuesses['adjustedQueryTerm'].nunique()

# Assigned = logAfterHCGuesses['SemanticType'].count()
Assigned = (logAfterHCGuesses['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterHCGuesses['SemanticType'].value_counts().head(10)))
print("\n\n===================================================\n ** logAfterHCGuesses stats - {} **\n===================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


# Remove from memory. HighConfidenceGuesses will be used below so don't remove here
del [[logAfterUmlsTerms, logAfterPastMatches]]



#%%
# ======================================================
# 9. Create new high-confidence guesses with FuzzyWuzzy
# ======================================================
'''
FuzzyAutoAdd - When phrase-match score is 90 or higher, assign without 
manual checking. By using past successful matches as the basis, we pull in
the vocabulary used by our audiences, product/service names, organizational
names, etc., with slight variations, AND as a tiny subset of the UMLS corpus,
this can be run quickly.

Isolate terms that might be a minor misspelling or might be a foreign version 
of the term. Some of these matches will be wrong, but overall, it's a good use 
of time to assign to what they look very similar to. Here we set the scorer to 
match whole terms/phrases, and the fuzzy matching score must be 90 or higher.

# Quick test, if you want - punctuation difference
fuzz.ratio('Testing FuzzyWuzzy', 'Testing FuzzyWuzzy!!')

FuzzyWuzzyResults - What the results of this function mean:
('hippocratic oath', 100, 2987)
('Best match string from dataset_2' (PastMatches), 'Score of best match', 'Index of best match string in PastMatches')

Re-start:
listOfUniqueUnassignedAfterUmls11 = pd.read_excel('02_Run_APIs_files/listOfUniqueUnassignedAfterUmls11.xlsx')
PastMatches = pd.read_excel('01_Import-transform_files/PastMatches.xlsx')
'''


# FIXME - Need to solve the issue around NaN vs '', which keeps coming up. Solve it the same way everywhere.
# Make the code fit what's easiest for Python so you don't have to keep changing
# listOfUniqueUnassignedAfterHC = logAfterHCGuesses.replace(np.nan, '', regex=True)


# Create list of unique entries that were searched more than x times.
listOfUniqueUnassignedAfterHC = logAfterHCGuesses.loc[logAfterHCGuesses['SemanticType'] == '']
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.groupby('adjustedQueryTerm').size()
listOfUniqueUnassignedAfterHC = pd.DataFrame({'timesSearched':listOfUniqueUnassignedAfterHC})
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.sort_values(by='timesSearched', ascending=False)
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.reset_index()

# This sets minimum appearances in log; helps assure we are starting with a "real" thing.
# There are many queries that are not discipherable, which appear only once.
listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC[listOfUniqueUnassignedAfterHC.timesSearched >= 2]
# Or you can eyeball and use a row range, # listOfUniqueUnassignedAfterHC = listOfUniqueUnassignedAfterHC.iloc[0:200]


def fuzzy_match(x, choices, scorer, cutoff):
    return process.extractOne(
        x, choices=choices, scorer=scorer, score_cutoff=cutoff
    )

# Create series FuzzyWuzzyResults
FuzzyAutoAdd1 = listOfUniqueUnassignedAfterHC.loc[:, 'adjustedQueryTerm'].apply(
        fuzzy_match,
    args=( PastMatches.loc[:, 'adjustedQueryTerm'], # Consider also running on PastMatches.preferredTerm
            fuzz.ratio, # also fuzz.token_set_ratio
            90
        )
)

# Convert FuzzyWuzzyResults Series to df
FuzzyAutoAdd2 = pd.DataFrame(FuzzyAutoAdd1)
FuzzyAutoAdd2 = FuzzyAutoAdd2.dropna() # drop the nulls


# The below procedures will fail if the df has zero rows
if FuzzyAutoAdd2.empty:
    logAfterFuzzyAuto = logAfterHCGuesses
    print('\n=================================\n FuzzyAutoAdd dataframe is empty\n=================================\n')
else:
    # Move Index (IDs) into 'FuzzyIndex' col because Index values will be discarded
    FuzzyAutoAdd2 = FuzzyAutoAdd2.reset_index()
    FuzzyAutoAdd2 = FuzzyAutoAdd2.rename(columns={'index': 'FuzzyIndex'})
    FuzzyAutoAdd2 = FuzzyAutoAdd2[FuzzyAutoAdd2.adjustedQueryTerm.notnull() == True] # remove nulls
    # Move tuple output into 3 cols
    FuzzyAutoAdd2[['ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex']] = FuzzyAutoAdd2['adjustedQueryTerm'].apply(pd.Series)
    FuzzyAutoAdd2.drop(['adjustedQueryTerm'], axis=1, inplace=True) # drop tuples
    # Merge result to the orig source list cols
    FuzzyAutoAdd3 = pd.merge(FuzzyAutoAdd2, listOfUniqueUnassignedAfterHC, how='left', left_index=True, right_index=True)
    FuzzyAutoAdd3.columns
    # 'FuzzyIndex', 'ProbablyMeantGSTerm', 'FuzzyScore', 'PastMatchesIndex', 'adjustedQueryTerm', 'timesSearched'
    # Change col order for browsability if you want to analyze this by itself
    FuzzyAutoAdd3 = FuzzyAutoAdd3[['adjustedQueryTerm', 'ProbablyMeantGSTerm', 'FuzzyScore', 'timesSearched', 'FuzzyIndex', 'PastMatchesIndex']]
    # Join to PastMatches "probably meant" to acquire columns from the source of the match
    resultOfFuzzyMatch = pd.merge(FuzzyAutoAdd3, PastMatches, how='left', left_on='ProbablyMeantGSTerm', right_on='adjustedQueryTerm')
    resultOfFuzzyMatch.columns
    '''
    'adjustedQueryTerm_x', 'ProbablyMeantGSTerm', 'FuzzyScore',
           'timesSearched', 'FuzzyIndex', 'PastMatchesIndex', 'ui',
           'adjustedQueryTerm_y', 'preferredTerm', 'SemanticType'
    '''   
    # adjustedQueryTerm_x is the term that was previously unmatchable; rename as adjustedQueryTerm
    # adjustedQueryTerm_y, adjustedQueryTerm from PastMatches, can be dropped
    # ProbablyMeantGSTerm is the PastMatches adjustedQueryTerm; keep so future editors understand the entry
    resultOfFuzzyMatch.rename(columns={'adjustedQueryTerm_x': 'adjustedQueryTerm'}, inplace=True)
    resultOfFuzzyMatch = resultOfFuzzyMatch[['ui', 'adjustedQueryTerm', 'ProbablyMeantGSTerm', 'preferredTerm', 'SemanticType']]
    # The below append breaks if data type is not str
    resultOfFuzzyMatch['adjustedQueryTerm'] = resultOfFuzzyMatch['adjustedQueryTerm'].astype(str)
    # Append new entries to HighConfidenceGuesses
    newHighConfidenceGuesses = HighConfidenceGuesses.append(resultOfFuzzyMatch, sort=True)
    # Write out for future runs
    writer = pd.ExcelWriter(dataMatchFiles + 'HighConfidenceGuesses.xlsx')
    newHighConfidenceGuesses.to_excel(writer,'HighConfidenceGuesses')
    # df2.to_excel(writer,'Sheet2')
    writer.save()
    # Join new entries to search log
    logAfterFuzzyAuto = pd.merge(logAfterHCGuesses, newHighConfidenceGuesses, how='left', left_on='adjustedQueryTerm', right_on='adjustedQueryTerm')
    logAfterFuzzyAuto.columns
    '''
    'SearchID', 'SessionID', 'StaffYN', 'Referrer', 'Query', 'Timestamp',
           'adjustedQueryTerm', 'ui_x', 'ProbablyMeantGSTerm_x', 'ui_x',
           'preferredTerm_x', 'SemanticType_x', 'ProbablyMeantGSTerm_y',
           'SemanticType_y', 'preferredTerm_y', 'ui_y'
    '''
    # Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
    logAfterFuzzyAuto['ui2'] = logAfterFuzzyAuto['ui_x'].where(logAfterFuzzyAuto['ui_x'].notnull(), logAfterFuzzyAuto['ui_y'])
    logAfterFuzzyAuto['ui2'] = logAfterFuzzyAuto['ui_y'].where(logAfterFuzzyAuto['ui_y'].notnull(), logAfterFuzzyAuto['ui_x'])
    logAfterFuzzyAuto['ProbablyMeantGSTerm2'] = logAfterFuzzyAuto['ProbablyMeantGSTerm_x'].where(logAfterFuzzyAuto['ProbablyMeantGSTerm_x'].notnull(), logAfterFuzzyAuto['ProbablyMeantGSTerm_y'])
    logAfterFuzzyAuto['ProbablyMeantGSTerm2'] = logAfterFuzzyAuto['ProbablyMeantGSTerm_y'].where(logAfterFuzzyAuto['ProbablyMeantGSTerm_y'].notnull(), logAfterFuzzyAuto['ProbablyMeantGSTerm_x'])
    logAfterFuzzyAuto['preferredTerm2'] = logAfterFuzzyAuto['preferredTerm_y'].where(logAfterFuzzyAuto['preferredTerm_y'].notnull(), logAfterFuzzyAuto['preferredTerm_x'])
    logAfterFuzzyAuto['SemanticType2'] = logAfterFuzzyAuto['SemanticType_x'].where(logAfterFuzzyAuto['SemanticType_x'].notnull(), logAfterFuzzyAuto['SemanticType_y'])
    logAfterFuzzyAuto['SemanticType2'] = logAfterFuzzyAuto['SemanticType_y'].where(logAfterFuzzyAuto['SemanticType_y'].notnull(), logAfterFuzzyAuto['SemanticType_x'])
    logAfterFuzzyAuto.drop(['ui_x', 'ui_y', 'ProbablyMeantGSTerm_x', 'ProbablyMeantGSTerm_y',
                            'preferredTerm_x', 'preferredTerm_y',
                            'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
    logAfterFuzzyAuto.rename(columns={'ui2': 'ui', 'ProbablyMeantGSTerm2': 'ProbablyMeantGSTerm', 
                                      'preferredTerm2': 'preferredTerm',
                                      'SemanticType2': 'SemanticType'}, inplace=True)
    # Re-sort full file
    logAfterFuzzyAuto = logAfterFuzzyAuto.sort_values(by='adjustedQueryTerm', ascending=True)
    logAfterFuzzyAuto = logAfterFuzzyAuto.reset_index()
    logAfterFuzzyAuto.drop(['index'], axis=1, inplace=True)


del [[logAfterHCGuesses, FuzzyAutoAdd3, resultOfFuzzyMatch]]


# -------------
# How we doin?
# -------------
rowCount = len(logAfterFuzzyAuto)
TotUniqueEntries = logAfterFuzzyAuto['adjustedQueryTerm'].nunique()

# Assigned = logAfterFuzzyAuto['SemanticType'].count()
Assigned = (logAfterFuzzyAuto['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterFuzzyAuto['SemanticType'].value_counts().head(10)))
print("\n\n===================================================\n ** logAfterFuzzyAuto stats - {} **\n===================================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned\n".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


del [[FuzzyAutoAdd1, FuzzyAutoAdd2, HighConfidenceGuesses, listOfUniqueUnassignedAfterHC]]


#%%
# ==========================================
# 10. Apply matches from QuirkyMatches.xlsx
# ==========================================
'''
The QuirkyMatches data comes from step 03, where a human selects entries 
from a matching / vetting interface. 

THESE ARE FREE-FORM ASSIGNMENTS WHERE SEMANTIC TYPE INFORMATION IS GUESSED AT.

While the PastMatches and HighConfidenceGuesses
entries could be incorporated into follow-on fuzzy matching, clustering, and
classification procedures, QuirkyMatches should be used more carefully, 
because these are misspelled, in a foreign language, are PARTIAL product/
service names, etc.

Periodically you can clean entries here and move them into PastMatches, if 
you decide they pass muster.
'''

# Open QuirkyMatches
QuirkyMatches = dataMatchFiles + 'QuirkyMatches.xlsx' # Human-chosen terms that might be misspelled, foreign, etc.
QuirkyMatches = pd.read_excel(QuirkyMatches)

# FIXME - Update in file
# QuirkyMatches.rename(columns={'SemanticTypeName': 'SemanticType'}, inplace=True)

# FIXME - R&D why it's not stored in the file this way...
QuirkyMatches['SemanticType2'] = QuirkyMatches['SemanticTypeName'].where(QuirkyMatches['SemanticTypeName'].notnull(), QuirkyMatches['NewSemanticTypeName'])
QuirkyMatches.drop(['Unnamed: 0', 'NewSemanticTypeName','SemanticTypeName'], axis=1, inplace=True)
QuirkyMatches.rename(columns={'SemanticType2': 'SemanticType'}, inplace=True)


# Join new UMLS API adds to the current search log master
logAfterStep1 = pd.merge(logAfterFuzzyAuto, QuirkyMatches, left_on='adjustedQueryTerm', right_on='adjustedQueryTerm', how='left')
logAfterStep1.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
       'adjustedQueryTerm', 'Unnamed: 0_x', 'Unnamed: 0_y',
       'ProbablyMeantGSTerm', 'ui', 'preferredTerm_x', 'SemanticType',
       'Unnamed: 0', 'NewSemanticTypeName', 'SemanticTypeName',
       'preferredTerm_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterStep1['preferredTerm2'] = logAfterStep1['preferredTerm_x'].where(logAfterStep1['preferredTerm_x'].notnull(), logAfterStep1['preferredTerm_y'])
logAfterStep1['preferredTerm2'] = logAfterStep1['preferredTerm_y'].where(logAfterStep1['preferredTerm_y'].notnull(), logAfterStep1['preferredTerm_x'])
logAfterStep1['SemanticType2'] = logAfterStep1['SemanticType_x'].where(logAfterStep1['SemanticType_x'].notnull(), logAfterStep1['SemanticType_y'])
logAfterStep1['SemanticType2'] = logAfterStep1['SemanticType_y'].where(logAfterStep1['SemanticType_y'].notnull(), logAfterStep1['SemanticType_x'])

logAfterStep1.drop(['preferredTerm_x', 'preferredTerm_y',
                          'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterStep1.rename(columns={'preferredTerm2': 'preferredTerm',
                                    'SemanticType2': 'SemanticType'}, inplace=True)

# Re-sort full file
logAfterStep1 = logAfterStep1.sort_values(by='adjustedQueryTerm', ascending=True)
logAfterStep1 = logAfterStep1.reset_index()
logAfterStep1.drop(['index'], axis=1, inplace=True)


# Save to file so you can open in future sessions, if needed
writer = pd.ExcelWriter(dataInterim + logFileName + '-logAfterStep1.xlsx')
logAfterStep1.to_excel(writer,'logAfterStep1')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -------------
# How we doin?
# -------------
rowCount = len(logAfterStep1)
TotUniqueEntries = logAfterStep1['adjustedQueryTerm'].nunique()

# Assigned = logAfterStep1['SemanticType'].count()
Assigned = (logAfterStep1['SemanticType'].values != '').sum() # .notnull().sum()
Unassigned = rowCount - Assigned

# Assigned = logAfterUmlsTerms['SemanticType'].count()
# Unassigned = rowCount - Assigned
PercentAssigned = round(Assigned / TotUniqueEntries * 100, 1)
PercentUnAssigned = 100 - PercentAssigned

# print("\nTop Semantic Types\n{}".format(logAfterStep1['SemanticType'].value_counts().head(10)))
print("\n\n===============================================\n ** logAfterStep1 stats - {} **\n===============================================\n\n{}% of rows unclassified / {}% classified\n{:,} queries in searchLog, {:,} unique;\n{:,} unassigned / {:,} assigned".format(logFileName, round(PercentUnAssigned), round(PercentAssigned), rowCount, TotUniqueEntries, Unassigned, Assigned))


del [[PastMatches, logAfterFuzzyAuto, QuirkyMatches, newHighConfidenceGuesses]]



#%%
# =============================================
# 11. Create 'uniques' dataframe/file for API
# =============================================
'''
Prepare a list of unique terms to process with API.

Re-starting?
listOfUniqueUnassignedAfterStep1 = pd.read_excel(dataInterim + 'listOfUniqueUnassignedAfterStep1.xlsx')
'''

# Unique unassigned terms and frequency of occurrence
uniquesForApiNormalized = logAfterStep1.loc[logAfterStep1['SemanticType'] == '']
uniquesForApiNormalized = uniquesForApiNormalized.groupby('adjustedQueryTerm').size()
uniquesForApiNormalized = pd.DataFrame({'timesSearched':uniquesForApiNormalized})
uniquesForApiNormalized = uniquesForApiNormalized.sort_values(by='timesSearched', ascending=False)
uniquesForApiNormalized = uniquesForApiNormalized.reset_index()


# ---------------------------------------------------------------
# Eyeball for fixes - Don't give the API things it can't resolve
# ---------------------------------------------------------------
'''
Act based on what the dataframes say; drop, modify, etc.
'''

# Save to file so you can open in future sessions
writer = pd.ExcelWriter(dataInterim + logFileName + '-uniquesForStep2.xlsx')
uniquesForApiNormalized.to_excel(writer,'uniquesForApiNormalized')
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%


# =====================================================
# 12. If working with multiple processed logs at once
# =====================================================
'''
For start-up / multiple runs, I run whole script on each of several log files, 
renaming output files after each run, then open and combine, for the API work
that is next.
'''

# ----------------
# Combine uniques
# ----------------

# Open step 1 files for uniques (the API)
uniques01 = pd.read_excel(dataInterim + 'SiteSearch2018-12-uniquesForStep2.xlsx')
uniques02 = pd.read_excel(dataInterim + 'SiteSearch2019-01-uniquesForStep2.xlsx')
uniques03 = pd.read_excel(dataInterim + 'SiteSearch2019-02-uniquesForStep2.xlsx')
uniques04 = pd.read_excel(dataInterim + 'SiteSearch2019-03-uniquesForStep2.xlsx')
uniques05 = pd.read_excel(dataInterim + 'SiteSearch2019-04-uniquesForStep2.xlsx')
uniques06 = pd.read_excel(dataInterim + 'SiteSearch2019-05-uniquesForStep2.xlsx')


# Append new data
combinedLogs = uniques01.append([uniques02, uniques03, uniques04, uniques05,
                                            uniques06])

del [[uniques01, uniques02, uniques03, uniques04, uniques05, uniques06]]

# Summarize across logs, 1 row per term
deDupedUniques = combinedLogs.groupby(['adjustedQueryTerm'])['timesSearched'].sum().sort_values(ascending=False).reset_index()
   
deDupedUniques = deDupedUniques.iloc[0:10000]

combinedLogs.head(50)

# Write out
writer = pd.ExcelWriter(dataInterim + 'S1Uniques-Combined.xlsx')
deDupedUniques.to_excel(writer,'deDupedUniques')
# df2.to_excel(writer,'Sheet2')
writer.save()


# -----------------------
# Combine processed logs
# -----------------------

# Open step 1 files for log
logAfterStep101 = pd.read_excel(dataInterim + 'SiteSearch2018-12-logAfterStep1.xlsx')
logAfterStep102 = pd.read_excel(dataInterim + 'SiteSearch2019-01-logAfterStep1.xlsx')
logAfterStep103 = pd.read_excel(dataInterim + 'SiteSearch2019-02-logAfterStep1.xlsx')
logAfterStep104 = pd.read_excel(dataInterim + 'SiteSearch2019-03-logAfterStep1.xlsx')
logAfterStep105 = pd.read_excel(dataInterim + 'SiteSearch2019-04-logAfterStep1.xlsx')
logAfterStep106 = pd.read_excel(dataInterim + 'SiteSearch2019-05-logAfterStep1.xlsx')


# Append new data
combinedLogs = logAfterStep101.append([logAfterStep102, logAfterStep103, logAfterStep104, 
                                           logAfterStep105, logAfterStep106], sort=True)

# Write out
writer = pd.ExcelWriter(dataInterim + 'S1Logs-Combined.xlsx')
combinedLogs.to_excel(writer,'combinedLogs')
# df2.to_excel(writer,'Sheet2')
writer.save() 
    
    
del [[logAfterStep101, logAfterStep102, logAfterStep103, logAfterStep104, logAfterStep105, logAfterStep106]]






del [[combinedLogs]]


#%%

"""
# -------------------------------
# How we doin? Visualize results
# -------------------------------


'''
FIXME - Add: x% of the terms searched 3 times or more, have been classified

# Full dataset, which terms were searched 3+ times?
cntThreeOrMore = logAfterStep1.groupby('adjustedQueryTerm').size()
cntThreeOrMore = pd.DataFrame({'timesSearched':cntThreeOrMore})
cntThreeOrMore = cntThreeOrMore.sort_values(by='timesSearched', ascending=False)
cntThreeOrMore = cntThreeOrMore.reset_index()
threeOrMoreSearches = cntThreeOrMore.loc[cntThreeOrMore['timesSearched'] >= 3]

# 5454

# Count of these terms where SemanticType notnull

cutDownFull = logAfterStep1[['adjustedQueryTerm', 'SemanticType']]

cutDownFull.loc[cutDownFull['SemanticType'].str.contains(''), 'SemanticType'] = 'Yes'
'''

print("\n\n====================================================================\n ** Import and Trasformation Completed for {}! **\n    When running multiple files, re-name each new file\n====================================================================".format(logFileName))


# -----------------
# Visualize results
# -----------------
# These break in Spyder autorun

'''
# Pie for percentage of rows assigned; https://pythonspot.com/matplotlib-pie-chart/
totCount = len(logAfterStep1)
Assigned = (logAfterStep1['preferredTerm'].values != '').sum()
Unassigned = (logAfterStep1['preferredTerm'].values == '').sum()
labels = ['Assigned', 'Unassigned']
sizes = [Assigned, Unassigned]
colors = ['steelblue', '#fc8d59']
explode = (0.1, 0)  # explode 1st slice
plt.pie(sizes, explode=explode, labels=labels, colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.title("Status after 'Step 1' processing - \n{} queries with {} unassigned".format(totCount, Unassigned))
plt.show()


# Bar of SemanticType categories, horizontal
# Source: http://robertmitchellv.com/blog-bar-chart-annotations-pandas-mpl.html
ax = logAfterStep1['SemanticType'].value_counts()[:20].plot(kind='barh', figsize=(10,6),
                                                 color="steelblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Top 20 semantic types assigned after 'Step 1' processing \nwith {:,} of {:,} unassigned".format(Unassigned, totCount), fontsize=14)
ax.set_xlabel("Number of searches", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.31, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
# invert for largest on top 
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.3)
'''


#%%


# =====================================================
# If working with multiple processed 'uniques' at once
# =====================================================
'''
For start-up / multiple runs, I run whole script on each of several log files, 
renaming output files after each run, then open and combine, for the API work
that is next.
'''

# Open step 1 files for uniques (the API)
uniques01 = pd.read_excel(dataInterim + 'SiteSearch2018-12-uniquesForStep2.xlsx')
uniques02 = pd.read_excel(dataInterim + 'SiteSearch2019-01-uniquesForStep2.xlsx')
uniques03 = pd.read_excel(dataInterim + 'SiteSearch2019-02-uniquesForStep2.xlsx')
uniques04 = pd.read_excel(dataInterim + 'SiteSearch2019-03-uniquesForStep2.xlsx')
uniques05 = pd.read_excel(dataInterim + 'SiteSearch2019-04-uniquesForStep2.xlsx')
uniques06 = pd.read_excel(dataInterim + 'SiteSearch2019-05-uniquesForStep2.xlsx')


# Append new data
combinedLogs = uniques01.append([uniques02, uniques03, uniques04, uniques05,
                                            uniques06])

    
# If combinedLogs is huge, you could have a look at a subset
viewRows = combinedLogs[260000:260800]

# Free memory
del [[uniques05, uniques06, uniques07, uniques08, uniques09, uniques10]]

# Running API requires time; try focusing on terms searched 3+ times, 
# i.e., it's probably a real thing. May-Oct 18, mine was 13,426 terms, nice
listToCheck1 = combinedLogs[combinedLogs.timesSearched >= 3]

# Or limit by rows
# listToCheck1 = combinedLogs[0:15000]


# ----------------------------------------------------



viewRows = combinedLogs[10000:11000]



'''
# Open step 1 files for log
logAfterStep1201805 = pd.read_excel(dataInterim + 'logAfterStep1-2018-05.xlsx')
logAfterStep1201806 = pd.read_excel(dataInterim + 'logAfterStep1-2018-06.xlsx')
logAfterStep1201807 = pd.read_excel(dataInterim + 'logAfterStep1-2018-07.xlsx')
logAfterStep1201808 = pd.read_excel(dataInterim + 'logAfterStep1-2018-08.xlsx')
logAfterStep1201809 = pd.read_excel(dataInterim + 'logAfterStep1-2018-09.xlsx')
logAfterStep1201810 = pd.read_excel(dataInterim + 'logAfterStep1-2018-10.xlsx')

# Append new data
combinedLogs = logAfterStep1201805.append([logAfterStep1201806, logAfterStep1201807, 
                                            logAfterStep1201808, logAfterStep1201809,
                                            logAfterStep1201810], sort=True)

# del [[logAfterStep1201805, logAfterStep1201806, logAfterStep1201807, logAfterStep1201808, logAfterStep1201809, logAfterStep1201810]]


combinedLogs.columns
'''
'ProbablyMeantGSTerm', 'Query', 'Referrer', 'SearchID',
'SemanticType', 'SessionID', 'StaffYN', 'Timestamp',
'adjustedQueryTerm', 'preferredTerm', 'ui'
'''

combinedLogs = combinedLogs[['SearchID', 'SessionID', 'Referrer', 
                             'adjustedQueryTerm','preferredTerm', 'ui', 
                             'ProbablyMeantGSTerm', 'SemanticType', 'StaffYN',
                             'Timestamp']]

viewRows = combinedLogs[10000:11000]

# Save to file so you can open in future sessions
writer = pd.ExcelWriter(dataInterim + 'combinedLogs.xlsx')
combinedLogs.to_excel(writer,'combinedLogs')
# df2.to_excel(writer,'Sheet2')
writer.save()
'''

'''
# I think the below can be obsoleted; I was not understanding. Replaced 9/19


# FIXME - see notes below, problem here
logAfterPastMatches = pd.merge(logAfterUmlsTerms, PastMatches, left_on=['adjustedQueryTerm', 'ui', 'preferredTerm', 'SemanticType'], right_on=['adjustedQueryTerm', 'ui', 'preferredTerm', 'SemanticType'], how='left')

logAfterPastMatches.columns
'''
'Referrer', 'Query', 'Date', 'SessionID', 'CountForPgDate',
'adjustedQueryTerm', 'wordCount', 'ui_x', 'preferredTerm_x',
'SemanticType_x', 'Unnamed: 0', 'Unnamed: 0.1', 'SemanticType_y',
'preferredTerm_y', 'ui_y'
'''

# Future: Look for a better way to do the above - MERGE WITH CONDITIONAL OVERWRITE. Temporary fix:
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_x'].where(logAfterPastMatches['ui_x'].notnull(), logAfterPastMatches['ui_y'])
logAfterPastMatches['ui2'] = logAfterPastMatches['ui_y'].where(logAfterPastMatches['ui_y'].notnull(), logAfterPastMatches['ui_x'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_x'].where(logAfterPastMatches['preferredTerm_x'].notnull(), logAfterPastMatches['preferredTerm_y'])
logAfterPastMatches['preferredTerm2'] = logAfterPastMatches['preferredTerm_y'].where(logAfterPastMatches['preferredTerm_y'].notnull(), logAfterPastMatches['preferredTerm_x'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_x'].where(logAfterPastMatches['SemanticType_x'].notnull(), logAfterPastMatches['SemanticType_y'])
logAfterPastMatches['SemanticType2'] = logAfterPastMatches['SemanticType_y'].where(logAfterPastMatches['SemanticType_y'].notnull(), logAfterPastMatches['SemanticType_x'])
logAfterPastMatches.drop(['ui_x', 'ui_y', 'preferredTerm_x', 'preferredTerm_y', 'SemanticType_x', 'SemanticType_y'], axis=1, inplace=True)
logAfterPastMatches.rename(columns={'ui2': 'ui', 'preferredTerm2': 'preferredTerm',
                                     'SemanticType2': 'SemanticType'}, inplace=True)


"""

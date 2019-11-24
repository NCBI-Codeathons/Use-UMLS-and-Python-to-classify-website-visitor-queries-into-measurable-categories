#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 27 09:20:01 2018

@authors: dan.wendling@nih.gov

Last modified: 2019-11-24

------------------------------------------
 ** Semantic Search Analysis: Start-up **
------------------------------------------

This script: A tool for collecting the type of "training data" that 
machine learning requires to make this process more automated. This is the
best way (so far) to classify the many ways your customers search for your 
products and product-related terminology.

The script puts your highest frequency terms into buckets/clusters, so
you can use Excel to add 2 levels of aggregation, to match what the UMLS 
terminologies are assigning: Preferred Term (preferred version of the term) and
Semantic Type (MID-LEVEL description).

Build a list of terms SPECIFIC TO YOUR SITE, which would be handled poorly by 
the processes in Phase 2:
    
    1. Your product and service names, in the forms that people search for them
    2. Person names, whether staff, authors, etc.
    3. Organizational names specific to pieces of your organization
    4. Anything you don't want the Phase 2 tools to tag. For example, if
       your organization is using a generic word as an acronym, you probably 
       want these occurrences tagged as your product, rather than the generic 
       term.

You can re-run the fuzzy-match process until you believe you have categorized 
what you need. Over time this will lighten the manual work in later steps with 
more accurate assignments and machine learning.

INPUTS:
- data/raw/SearchConsole.csv
- data/raw/SiteSearch.csv

OUTPUTS:
- data/matchFiles/ClusterResults.xlsx


--------------------------------
HOW TO EXPORT SEARCH QUERY DATA
--------------------------------
Script assumes Google Analytics where search logging has been configured. Can
be adapted for other tools.

    1. Go to Acquisition > Search Console > Queries
    2. Set date parameters (Consider 12 months)
    3. Select Export > Unsampled Report as SearchConsole.csv
    4. Copy the result to data/raw folder
    5. Do the same from Behavior > Site Search > Search Terms with file name
        SiteSearch.csv
        
(You could also use the separate Google Search Console interface, but this
requires more configuration than is covered here.)


----------------
SCRIPT CONTENTS
----------------
1. Start-up / What to put into place, where
2. Create match list, update columns and rows
3. Create buckets of similar character strings
4. Build your custom terminology in Excel
5. Go on to Phase 1; re-run this script later as needed

"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
File locations, etc.
'''

import pandas as pd
import numpy as np
import os
import re
import string
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import collections
import copy

# Set home, input, and output directories; files
home_folder = os.path.expanduser('~')
os.chdir(home_folder + '/Projects/classifysearches')

SearchConsoleRaw = 'data/raw/SearchConsole.csv' # Put log here before running script
SiteSearchRaw = 'data/raw/SiteSearch.csv' # Put log here before running script


#%%
# ==============================================
# 2. Create match list, update columns and rows
# ==============================================
'''
Default for pilot site, after eyeballing the data, was:
    - SearchConsole: Let's process the top 80% of search terms used
    - SiteSearch: Let's process 
    
Reset the number of terms you want to process based on:
    - Quality of the buckets you're getting below
    - Your available time
    - Percentage of your search traffic you you think is important to cover

Incorporating too many low-frequency searches too soon can waste your time
by reducing the quality of your bucket content.

You could process the terms separately or together. 

The pilot site has relatively few organization-specific terms, and the top 40% 
of terms by search frequency = 70,000 terms. We decided it would be easier to 
only match to our SearchConsole terms, and catch the rest after the generic 
terms have been matched by the UMLS vocabularies. This may not be true for 
other sites.
'''

# --------------
# SearchConsole 
# --------------
'''
Script is expecting:
    
| Search Query     | Clicks | Impressions | CTR  | Average Position |
| hippocratic oath | 1037   | 19603       | 0.05 | 4.1              |
'''

SearchConsole = pd.read_csv(SearchConsoleRaw, sep=',', index_col=False) # skiprows=7, 
SearchConsole.columns
'''
'Search Query', 'Clicks', 'Impressions', 'CTR', 'Average Position'
'''

# Reduce and rename
SearchConsole = SearchConsole[['Search Query', 'Clicks']]
SearchConsole.rename(columns={'Search Query': 'Query'}, inplace=True)

# Total queries represented in file
SearchConsoleTotCnt = SearchConsole['Clicks'].sum()

# Derive cumulative percentage by row; drop terms of lower search frequency
# Pilot site favors looking at the top 80 percent of terms used in the past year,
# Which is around 1100 terms
SearchConsole['CumulativeTotal'] = SearchConsole['Clicks'].cumsum()
SearchConsole['CumulativePercent'] = 100*SearchConsole['CumulativeTotal'] / SearchConsoleTotCnt
# Drop rows of lower frequency
SearchConsole = SearchConsole.loc[(SearchConsole['CumulativePercent'] < 81)]

# Only need 1 col
SearchConsoleResult = SearchConsole[['Query']]


# -----------
# SiteSearch
# -----------
'''
Not used as described at top of this section.
'''

SiteSearch = pd.read_csv(SiteSearchRaw, sep=',', index_col=False) # skiprows=7, 
SiteSearch.columns
'''
'Search Term', 'Total Unique Searches', 'Results Pageviews / Search',
       '% Search Exits', '% Search Refinements', 'Time after Search',
       'Avg. Search Depth'
'''

# listToCheck = SiteSearch.iloc[0:1000]

# Reduce and rename
SiteSearch = SiteSearch[['Search Term', 'Total Unique Searches']]
SiteSearch.rename(columns={'Search Term': 'Query', 'Total Unique Searches': 'SearchCnt'}, inplace=True)

# Total queries represented in file
SiteSearchTotCnt = SiteSearch['SearchCnt'].sum()

# Derive cumulative percentage by row; drop terms of lower search frequency
# Pilot site favors looking at the top 80 percent of terms used in the past year,
# Which is around 1100 terms
SiteSearch['CumulativeTotal'] = SiteSearch['SearchCnt'].cumsum()
SiteSearch['CumulativePercent'] = 100*SiteSearch['CumulativeTotal'] / SiteSearchTotCnt
# Drop rows of lower frequency
SiteSearch = SiteSearch.loc[(SiteSearch['CumulativePercent'] < 41)]

# Only need 1 col
SiteSearchResult = SiteSearch[['Query']]


# Concat if needed / rename
# query_df = SearchConsoleResult.append(SiteSearchResult, sort=False)
query_df = SearchConsoleResult


#%%

# Remove unneeded before intensive processing
del [[SiteSearch, SearchConsole, SiteSearchResult, SearchConsoleResult]] # listToCheck


#%%
# ===============================================
# 3. Create buckets of similar character strings
# ===============================================
'''
FuzzyWuzzy aggregates frequently occurring terms and puts them into buckets.
Change the commented numbers based on the quality of the response you are getting.
Depends on how people are searching your site, how many products you have, etc.
For the pilot site we started with 10 buckets; later with 5 buckets, one bucket
would be great and the others not useful at all.

Most of this is adjustable; see:
- https://github.com/seatgeek/fuzzywuzzy (creator site)
- https://www.neudesic.com/blog/fuzzywuzzy-using-python/
- https://www.datacamp.com/community/tutorials/fuzzy-string-python

This script uses "fuzz.ratio."

NOTE: The dataframe index must be sequential from zero or the code will break.

query_df = query_df.iloc[0:1000]
query_df = query_df.loc[(query_df['TotalSearchFreq'] > 5)]

Score of ~70, for pilot site, allows ~1 word to be the same in ~3-word phrases;
this is good for "grants" but bad regarding "medicine."
'''

# Iterations after initial build: query_df = UnmatchedAfterJournals # UnmatchedAfterUmlsMesh UnassignedAfterSS
query_df = query_df.loc[(query_df['TotalSearchFreq'] > 15)] # Pilot site: started at 15 and moved down
query_df.rename(columns={'AdjustedQueryTerm': 'Query'}, inplace=True)

rowCnt = len(query_df)
queryColName = 'Query'
n_freq = 200 # Max rows by frequency of occurrence (?) Was 200
n_bucket = 10 # 10 works fine but requires many cycles
pair = []
whole_list = []
bucket_init = [[]  for i in range(n_bucket)]
bucket = bucket_init
#bucket = [[],[], [], [], []]#[[]]*n_bucket
print("bucket = ", bucket)

for i_comp1 in range(rowCnt): 
    comp1 = query_df[queryColName][i_comp1]
    for i_comp2 in range(i_comp1+1, rowCnt):
        comp2 = query_df[queryColName][i_comp2]
        score = fuzz.ratio(comp1, comp2)
        if (score > 75):       # Similarity score you want; lower is looser matching. Was 75
            whole_list.extend((i_comp1, i_comp2))
            pair.append((i_comp1,i_comp2))
print("whole pair = ", pair)
whole_counter =  collections.Counter(whole_list)
whole_key = whole_counter.most_common(n_freq)
print(whole_key)
i_end = 0
i_cur = 0
i = 0
range_check = 0
for key, value in (whole_key):
    key_in_pre = False
# check whether key in previous bucket
    for j_check in range(max(range_check, i_end)):
        if key in bucket[j_check]:
            key_in_pre = key in bucket[j_check]
            i_cur = j_check
    if (i_end == 0 and (bucket[0] == [])):
        i = 0
        range_check = 1
    elif ((key_in_pre)):
        i = i_cur
    elif (key_in_pre and i_end != 0):
        i = i_cur
    elif ((~key_in_pre) and (i_end < n_bucket)) :
        i_end = i_end + 1
        i = i_end
    else:
        i = 100
# end check whether key in previous bucket        

#    print("i = " , i)   
    pair_copy = pair.copy()
    if (i < n_bucket):
      for i_pair in pair_copy:
        if(key == i_pair[0]):
            bucket[i].extend(i_pair)
            index = pair.index((key, i_pair[1]))
            pair.pop(index)
        elif(key == i_pair[1]):
            bucket[i].extend(i_pair)


print( "set ", set(bucket[0]), set(bucket[1]), set(bucket[2]))

# Results: Print to console
for ii in range(n_bucket):
    print("bucket ", ii, " = ", [query_df[queryColName][i_name] for i_name in set(bucket[ii])])

# Results: Append to dataframe
clusterResults = pd.DataFrame()
clusterResults['Bucket'] = ""
clusterResults['Query'] = ""

for ii in range(n_bucket):
    clusterResults = clusterResults.append(pd.DataFrame({'Bucket': ii, 
                                                       'Query': [query_df[queryColName][i_name] for i_name in set(bucket[ii])]}), ignore_index=True)

# Dupe off Query column so we can tinker with the dupe
clusterResults['AdjustedQueryTerm'] = clusterResults['Query'].str.lower()

# Replace hyphen with space because the below would replace with nothing
clusterResults['AdjustedQueryTerm'] = clusterResults['AdjustedQueryTerm'].str.replace('-', ' ')
# Remove https:// if used
clusterResults['AdjustedQueryTerm'] = clusterResults['AdjustedQueryTerm'].str.replace('https://', '')

# Remove all chars except a-zA-Z0-9 and leave foreign chars alone
clusterResults['AdjustedQueryTerm'] = clusterResults['AdjustedQueryTerm'].str.replace(r'[^\w\s]+', '')

# Mods look okay, dropping original term for now; check if problems emerge
clusterResults.drop('Query', axis=1, inplace=True)

# Add empty columns that user will type in
clusterResults['PreferredTerm'] = ''
clusterResults['SemanticType'] = ''

# Write out
writer = pd.ExcelWriter('data/matchFiles/ClusterResults.xlsx')
clusterResults.to_excel(writer,'clusterResults', index=False)
# df2.to_excel(writer,'Sheet2')
writer.save()


#%%
# ===============================================
# 4. Build your custom terminology in Excel
# ===============================================
'''
Open data/matchFiles/ClusterResults.xlsx. Sort through the results and for rows
that don't fit, move them to a bucket where it does fit, or delete it. Build a 
file matching the below. Delete the bucket column when you are done, and then
append the result to SiteSpecificTerms.xlsx.

|| AdjustedQueryTerm               || PreferredTerm                  || SemanticType     ||
|  yellow wallpaper	               |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow paper	               |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaper online pdf |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaper read       |  The Literature of Prescription | Product-LO-Exhibit |
|  yellow wallpaper gilman pdf	   |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaper text	       |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaper short story|  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaper book	       |  The Literature of Prescription | Product-LO-Exhibit |
|  the yellow wallpaer	           |  The Literature of Prescription | Product-LO-Exhibit |
|  medical subject headings (mesh) |  MeSH                           | Product-MeSH       |
|  medline                         |  PubMed/MEDLINE                 | Product-NCBI       |
|  medilne                         |  PubMed/MEDLINE                 | Product-NCBI       |
|  medlibe                         |  PubMed/MEDLINE                 | Product-NCBI       |
|  medlie                          |  PubMed/MEDLINE                 | Product-NCBI       |
|  medlime                         |  PubMed/MEDLINE                 | Product-NCBI       |
|  medlin                          |  PubMed/MEDLINE                 | Product-NCBI       |
|  medlina                         |  PubMed/MEDLINE                 | Product-NCBI       |
'''


#%%
# ========================================================
# 5. Go on to Phase 1; re-run this script later as needed
# ========================================================
'''
Phase 1 will match the logs to SiteSpecificTerms.xlsx and PastMatches.xlsx, 
and then you will be invited to re-cluster on the remaining untagged terms.
You can judge then how many cycles would be appropriate for you to build your 
SiteSpecificTerms.xlsx file.
'''



#%%
# ========================================================
# To update SiteSpecificMatches.xlsx, such as punctuation
# ========================================================

"""
SiteSpecificMatches = pd.read_excel('data/matchFiles/SiteSpecificMatches.xlsx')

# Replace hyphen with space because the below would replace with nothing
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('-', ' ')
# Remove https:// if used
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('http://', '')
SiteSpecificMatches['AdjustedQueryTerm'] = SiteSpecificMatches['AdjustedQueryTerm'].str.replace('https://', '')

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
"""


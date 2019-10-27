#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 17 14:20:00 2019


Last modified: 2019-10-25

** Search query analyzer **

This script: Cluster your uncategorized search queries using FuzzyWuzzy and use
them to build classifications outside the UMLS terminologies, that are
specific to your web site.


----------------------------------------------------------
CLUSTERING TO IMPOSE STRUCTURE ON NON-UMLS SEARCH QUERIES
----------------------------------------------------------

This can be used to build your PastMatches.csv file for things the UMLS resources
may not handle correctly, to be used in Phase 1:
    
    1. Your product and service names, as people search for them
    2. Person names, whether staff, authors, etc.
    3. Organizational names specific to your organization
    4. Any homonymns, etc., that you review after Phase 2 that you want to 
        control tagging for, to PREVENT the Phase 2 tools from tagging them.

One procedure:
    
1. In GA, download 12 months of queries, top 1000; Export > CSV, either
    GA > Acquisition > Search Console > Queries (probably best place to start) or
    GA > Behavior > Site Search > Search Terms (consider using Google Search Console)
2. Open the file in a text editor and remove the top and bottom rows that 
    surround the query data.
3. Run this script; copy the result to a text editor
4. Move clusters of query terms into the spreadsheet version of PastMatches.csv
5. In the spreadsheet, add categories such as the preferred product name, etc.
6. Save the spreadsheet and run/re-run the matching, then re-run this script
    and repeat the procedure, until you believe you have categorized what 
    you need.


--------------------------
INPUT FILES YOU WILL NEED
--------------------------
Google Analytics or Google Search Console file as described above.


--------------------------
OUTPUTS OF THIS PROCEDURE
-------------------------

1. Results written to console for you to check on; re-run with different parameters if needed
2. Results written to file data/matchFiles/clusterResult.csv - use to build PastMatches.csv
"""



#%%

import pandas as pd
import os
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import collections
import copy

# Set working directory and directories for read/write
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')

# Note difference in column names
queryColName = 'Search Query' # If you're using Acquisition > Search Console > Queries
# queryColName = 'Search Term' # If you're using Behavior > Site Search > Search Terms

query_df = pd.read_csv('data/raw/GA-console-12mo-1000.csv', sep=',', index_col=False) # skiprows=7, 
# query_df = pd.read_excel("data/raw/GA-console-12mo.xlsx")


n_freq = 200
n_bucket = 10
pair = []
whole_list = []
bucket_init = [[]  for i in range(n_bucket)]
bucket = bucket_init
#bucket = [[],[], [], [], []]#[[]]*n_bucket
print("bucket = ", bucket)

for i_comp1 in range(999): # Length of file (?)
    comp1 = query_df[queryColName][i_comp1]
    for i_comp2 in range(i_comp1+1, 999): # Length of file (?)
        comp2 = query_df[queryColName][i_comp2]
        score = fuzz.ratio(comp1, comp2)
        if (score > 75):
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
clusterResults['SearchQuery'] = ""

for ii in range(n_bucket):
    clusterResults = clusterResults.append(pd.DataFrame({'Bucket': ii, 
                                                       'SearchQuery': [query_df[queryColName][i_name] for i_name in set(bucket[ii])]}), ignore_index=True)
# Write out
clusterResults.to_csv('clusterResults.csv', sep=',', encoding='utf-8')

    
#%%


"""
Example output from GA-console-12mo.csv, the first bucket

bucket  0  =  ['the yellow wallpaper', 'the yellow wallpaper pdf', 'yellow wall paper', 'the yellow wallpaper online', 'pdf the yellow wallpaper', 'gilman yellow wallpaper', 'the yellow wallpaper by charlotte perkins gilman pdf', 'yellow wallpaper charlotte perkins gilman pdf', 'yellow wallpaper', 'yellow wallpaper pdf', 'yellow wall paper pdf', 'the yellow paper pdf', 'a yellow wallpaper pdf', 'why i wrote the yellow wallpaper pdf', 'the yellow wallpaper gilman', 'the yellow wallpaer', 'gilman the yellow wallpaper', 'yellow wallpaper by charlotte perkins gilman', 'the yellow wall-paper', 'the yellow wall paper pdf', 'the yellow paper', 'the yellow wallpaper short story pdf', 'the yellow wallpaper charlotte perkins gilman pdf', 'gilman the yellow wallpaper pdf', 'the yellow wallpaper short story', 'the yellow wallpaper text pdf', 'the yellow wallpaper book', 'why i wrote the yellow wallpaper', 'the yellow wallpaper text', 'the yellow.wallpaper', 'the yellow wallpaper by charlotte perkins gilman', 'the yellow wall paper', 'the yellow wallpaper read online', 'the yellow wallpaper summary pdf', 'the yellow wallpaper gilman pdf', 'yellow wallpaper story', 'yellow wallpaper short story', 'yellow wallpaper charlotte perkins gilman', 'the yellow wallpaper story', 'the yellow wallpaper full text pdf', 'the yellow wallpaper online pdf', 'the yellow wallpaper charlotte perkins gilman', 'the yellow wallpape', 'wallpaper pdf', 'yellow wallpaper short story pdf', 'yellow wallpaper gilman', 'charlotte perkins gilman the yellow wallpaper pdf', 'the yellow walpaper', 'the yellow wallpaper free pdf', 'the yellow wallpaper analysis pdf', 'the yellow wallpapaer', 'the yellow wallpaper full text']
"""


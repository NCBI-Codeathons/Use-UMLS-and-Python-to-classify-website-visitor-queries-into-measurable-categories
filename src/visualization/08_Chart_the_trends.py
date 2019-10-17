#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 12 08:59:19 2018

@authors: dan.wendling@nih.gov,

Last modified: 2019-10-16

This script: Statistical depictions for dashboard, in the order of 
our dashboard wireframe. Writes images.

Assumes that the basic unit of analysis is one week of logs.

Future: Wrangle tables for Tableau

----------------
SCRIPT CONTENTS
----------------
1. Start-up / What to put into place, where
2. New and Historical datasets - Pies for percentage of rows assigned
3. Totals for complete log and the newly added log
4. hbar of 6-Month Summary by Top-Level Categories
5. Trendlines by broad topic (Semantic Groups)
6. Biggest movers - Normalized term
7. Semantic type hierarchy with counts
8. Sem type time series subplots
9. Findings
10. Outlier / error checks

Code for quick testing: If date is Index, the below will automatically plot time series:
    df['ClosingPrice'].plot()
    plt.ylabel('Closing price in U.S. dollars')
    plt.show()
    
    df.loc['2018-07-01':'2018-12:31', ClosingPrice'].plot(style='k.-', title='S&P stuff')
    plt.ylabel('Closing price in U.S. dollars')
    plt.show()    
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
Various options for time periods, 
http://pandas.pydata.org/pandas-docs/stable/timeseries.html#dateoffset-objects
'''

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import os
from datetime import datetime, timedelta
# import random
from scipy.optimize import basinhopping, differential_evolution
import json

# Set working directory, read/write locations
# CHANGE AS NEEDED
os.chdir('/Users/name/Projects/webDS')
dataProcessed = 'data/processed/search/' # Ready to visualize
reports = 'reports/search/' # Where to write images, etc., to

# Specific files you'll need
sslh = dataProcessed + 'SemanticSearchLogHistorical.xlsx' # processed log

# Load the historical log (previously compiled logs that don't yet include this week)
sslh = pd.read_excel(sslh)
sslh.columns
'''
'Referrer', 'adjustedQueryTerm', 'CountForPgDate',
       'ProbablyMeantGSTerm', 'ui', 'preferredTerm', 'SemanticType',
       'SemanticGroupCode', 'SemanticGroup', 'CustomTreeNumber',
       'BranchPosition', 'CustomTag'
'''

# Re-confirm Date data type if needed
sslh['Date'] = pd.to_datetime(sslh['Date'].astype(str), format='%Y-%m-%d')

sslh.dtypes # Should have Date as datetime64[ns]

# Set multiple time periods for multiple dashboard charts
# now = datetime.now()
mostRecentDate = sslh['Date'].max()
mostRecentDate

# FIXME - MANUAL WORK!! THIS CODE WAS IN PHASE 5, ALSO COMMENTED OUT. CHART 
# FULL WEEKS ONLY, SUNDAY TO SATURDAY. IF TRENDLINES DROOP LATER, THIS IS 
# PROBABLY THE ISSUE. 
# sslh = sslh.loc[(sslh['Date'] != "2018-12-30")]
# or later perhaps d.drop(2018-12-30 00:00:00, inplace=True)


# Change date to be the index
sslh.set_index('Date', inplace=True)

# Sort by date
sslh = sslh.sort_index()

sslh.tail()


# Get df's to process using last x in the data frame; start from max and go 
# backward. (End on Sunday?) "Biggest Movers" section has more.
lastWeekOfLog = sslh.loc[mostRecentDate - pd.Timedelta(weeks=1):mostRecentDate]
lastTwoWeeksOfLog = sslh.loc[mostRecentDate - pd.Timedelta(weeks=2):mostRecentDate]
lastFourWeeksOfLog = sslh.loc[mostRecentDate - pd.Timedelta(weeks=4):mostRecentDate]
lastSixMonthsOfLog = sslh.loc[mostRecentDate - pd.Timedelta(weeks=26):mostRecentDate]


'''
Need 2 ranges for Biggest Movers
RangeOne
    Last 14 days of log
RangeTwo
    # StartDate = Today minus 26 weeks
    # EndDate = Today minus 14 days
    
Also need to prevent the right end of trendlines from drooping at the end
of months because it's not a full week. Set end of calc to the end of the
last full week.
'''


#%%
# ======================================================================
# 2. New and Historical datasets - Pies for percentage of rows assigned
# ======================================================================

# ------------
# New dataset
# ------------

# Total searches
newTotCount = lastWeekOfLog['CountForPgDate'].sum()

newAssigned = lastWeekOfLog[['SemanticType', 'CountForPgDate']]
newAssigned = newAssigned[newAssigned.SemanticType.str.contains("Unassigned") == False]
newAssigned = newAssigned['CountForPgDate'].sum()
newUnassigned = newTotCount - newAssigned
newPercentAssigned = round(newAssigned / newTotCount * 100)

colors = ['steelblue', '#fc8d59'] # more intense-#FF7F0E; lightcoral #FF9966
explode = (0.1, 0)  # explode 1st slice

# viz --------------
plt.pie([newAssigned, newUnassigned], explode=explode, labels=['Assigned', 'Unassigned'], colors=colors,
        autopct='%1.f%%', shadow=False, startangle=100)
plt.axis('equal')
plt.suptitle('Tagging Status for Site Search Log'.format(lastWeekOfLog), fontsize=14, fontweight='bold')
plt.title('{:,} ({}%) of {:,} queries successfully tagged for most recent week'.format(newAssigned, newPercentAssigned, newTotCount), fontsize=10)
plt.show()

plt.savefig(reports + 'Search01-SumPercentAssigned.png')


'''
From 01

# Total queries in log
TotQueries = searchLog['CountForPgDate'].sum()

# Row count / Number of days you have data for
TotDaysCovered = searchLog['Date'].nunique()

# Avg searches per day
AvgSearchesPerDay = round(TotQueries / TotDaysCovered, 0)

# Searches by day for bar chart
searchesByDay = searchLog.groupby('Date').agg(['sum']).reset_index()

# viz -------------- (not displaying correctly, I want counts on bars)
# FIXME - Multi-index problem?
ax = searchesByDay.plot(x='Date', y='CountForPgDate', kind='bar', figsize=(10,5))
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.set_title("Search Count by Day", fontsize=18)
ax.set_xlabel("Day", fontsize=9)
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.1, i.get_y()+.1, str(round((i.get_width()), 2)), fontsize=9, color='dimgrey')
plt.gcf().subplots_adjust(bottom=0.2)
plt.show()

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
pd.options.display.max_columns = None

# Show
print("\n\n==================================================================\n ** Baseline stats - {} **\n==================================================================\n\n{:,} search queries from {} days; ~ {:,} searches/day".format(logFileName, TotQueries, TotDaysCovered, AvgSearchesPerDay))
print("\nPage report: Top 10 FOLDERS where searches are occurring, by percent share of total searches\n\n{}".format(searchesByReferrerDir))
print("\nPage report: Top 10 PAGES where searches are occurring, by percent share of total searches\n\n{}".format(searchesByReferrerPg))
print("\nTerm report: Top 25 TERMS searched with percent share, by literal string\n\n{}".format(TermReport))
'''


#%%
# ===================================================
# 3. Totals for complete log and the newly added log
# ===================================================
'''
Stats for the newest dataset added. Add limit; set to the week just ended?
'''

print("\nSearches last week: {:,}".format(lastWeekOfLog['CountForPgDate'].sum()))

print("Total unique search terms: {:,}".format(lastWeekOfLog['adjustedQueryTerm'].nunique()))

print("Foreign language, not parsable: {:,}".format((lastWeekOfLog['SemanticType'].values == 'Foreign unresolved').sum()))

print("\nSearches last week for opiods/addiction: {:,}".format(lastWeekOfLog['CustomTag'].str.contains('Opioid').sum()))

# newDaysOfData = sslh['Date'].nunique() # pandas.Index.nunique
# print("Newest data set - days of data: {}".format(lastWeekOfLog.resample('D').count()))

# print("Average searches per day: {:,}".format(round(newTotCount / newDaysOfData)))

# print("Average searches per week: {:,}".format(round(newTotCount / newDaysOfData)))


#%%
# ===================================================
# 4. hbar of 6-Month Summary by Top-Level Categories
# ===================================================
'''
# Add time calcs
# AprMay = logAfterUmlsApi1[(logAfterUmlsApi1['Timestamp'] > '2018-04-01 01:00:00') & (logAfterUmlsApi1['Timestamp'] < '2018-06-01 00:00:00')]

'''

histTotCount = sslh['CountForPgDate'].sum()

histAssigned = sslh[['SemanticType', 'CountForPgDate']]
histAssigned = histAssigned[histAssigned.SemanticType.str.contains("Unassigned") == False]
histAssigned = histAssigned['CountForPgDate'].sum()
histUnassigned = histTotCount - histAssigned
histPercentAssigned = round(histAssigned / histTotCount * 100)

topSemGroupsSum = sslh.groupby(['SemanticGroup'])['CountForPgDate'].sum().sort_values(ascending=False)
topSemGroupsSum = topSemGroupsSum.astype({"CountForPgDate": int})

# viz --------------
ax = topSemGroupsSum.plot(kind='barh', figsize=(7,6), color="slateblue", fontsize=10);
ax.set_alpha(0.8)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.suptitle('6-Month Summary by Top-Level Categories', fontsize=14, fontweight='bold')
ax.set_title('With {:,} ({}%) of {:,} queries assigned'.format(histAssigned, histPercentAssigned, histTotCount), fontsize=10)
ax.set_xlabel("Number of searches", fontsize=9);
# set individual bar lables using above list
for i in ax.patches:
    # get_width pulls left or right; get_y pushes up or down
    ax.text(i.get_width()+.31, i.get_y()+.31, "{:,}".format(i.get_width()), fontsize=9, color='dimgrey')
# invert for largest on top
ax.invert_yaxis()
plt.gcf().subplots_adjust(left=0.4)
plt.show()

plt.savefig(reports + 'Search03-SumSemGroups6mo.png')


#%%
# ===================================================
# 5. Trendlines by broad topic (Semantic Groups)
# ===================================================
'''
cf surveyViz.py, plt.title('6 Months of "FoundInformation=Yes 
and survey-RoleYesOverTime.png

This is a version of https://matplotlib.org/gallery/showcase/bachelors_degrees_by_gender.html
that has adjusts some labels automatically.

Simplified source, see https://www.kdnuggets.com/2018/07/5-quick-easy-data-visualizations-python-code.html
See https://medium.com/python-pandemonium/data-visualization-in-python-line-graph-in-matplotlib-9dfd0016d180
'''

d = sslh.groupby('SemanticGroup').resample('1D').count()['SemanticGroup'].unstack().T
color_sequence = ['#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
                  '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
                  '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
                  '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5']


# viz --------------
fig, ax = plt.subplots(1,1, figsize=(8,10))
# Remove the plot frame lines. They are unnecessary here.
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
# ax.spines['bottom'].set_visible(False)
# ax.spines['left'].set_visible(False)
# Ensure that the axis ticks only show up on the bottom and left of the plot.
# Ticks on the right and top of the plot are generally unnecessary.
ax.get_xaxis().tick_bottom()
ax.get_yaxis().tick_left()
fig.subplots_adjust(left=.1, right=.75, bottom=.15, top=.94)
out = d.resample('1W').sum()
ax.grid(True, axis='y')
# To tinker manually
# ax.set_xlim(pd.Timestamp('2018-10-01'), pd.Timestamp('2018-11-29'))
ax.tick_params(axis='both', which='both', bottom=False, top=False,
                labelbottom=True, left=False, right=False, labelleft=True)
fig.autofmt_xdate()
# Optimizing label position to avoid overlap
p = list(out.iloc[-1].items())
p.sort(key=lambda x: x[1])
dist = 3
m = -15
step = 0.5
q = []
for k,v in p:
    if np.isnan(v):
        q.append(-1)
    else:
        q.append(v-1)

def conflicts(x):
    x = np.array(x)
    diff = np.diff(x)
    diff = diff[diff < dist].size
    return diff

def improve_placement(q, dist=3, m=-15, step=0.5):
    while conflicts(q) > 0:
        for i in range(len(q) // 2):
            if (q[i+1] - q[i]) < dist:
                if (q[i]-step) > m:
                    q[i] -= step
                q[i+1] += step / 2
            if (q[-i-1] - q[-i-2]) < dist:
                q[-i-1] += step
                q[-i-2] -= step / 2
    return q

q = improve_placement(q, dist=5)
new_positions = {l:v for (l,old_value),v in zip(p,q)}
x_position = out.index[-1] + (out.index[-1] - out.index[0])/50
for i, (label, value) in enumerate(out.iloc[-1].items()):
    ax.plot(out.index, out[label], c=color_sequence[i])
    ax.text(x_position, new_positions[label], label, 
                    fontsize=9, color=color_sequence[i])
ax.set_xlabel('Time', fontsize=11)
ax.set_ylabel('Search Frequency', fontsize=11)
plt.suptitle('Broad-Topic Trendline (~15 Semantic Groups)', fontsize=14, fontweight='bold')
ax.set_title('6 months of data, up to the end of the last full week. Avg searches/week: x', fontsize=11)
plt.show()

fig.savefig(reports + 'Search04-BroadTopicTrendlines6mo.png') # , dpi=300


#%%
# ===================================================
# 6. Biggest movers bar - Normalized term
# ===================================================
'''
How is the week just ended different than the 4 weeks before it?
'''

# ------------------------
# Prepare custom data set
# ------------------------

# Reduce and reorder
BiggestMovers = sslh[['preferredTerm', 'SemanticType', 'SemanticGroup']]

# Get nan count, out of curiousity
Unassigned = BiggestMovers['preferredTerm'].isnull().sum()
Unassigned

# Remove nan rows
BiggestMovers = BiggestMovers.loc[(BiggestMovers.preferredTerm.notnull())]
BiggestMovers = BiggestMovers.loc[(BiggestMovers.SemanticType.notnull())]
BiggestMovers = BiggestMovers.loc[(BiggestMovers.SemanticGroup.notnull())]

# Remove Bibliographic Entity? Quite an outlier.


# ---------------------------------------------
# Create time-period data for chart to consume
# ---------------------------------------------
'''
Currently: How is the week just ended different from the previous 4 weeks?

TODO - Build all automatically in the future
    How is the week just ended different from the previous 4 weeks?   
    How is the month just ended different from the previous month?
    How is the quarter just ended different from the quarter before?
    How is this December different from last December?

From above, we already have
    lastWeekOfLog
    lastTwoWeeksOfLog
    lastFourWeeksOfLog
    lastSixMonthsOfLog

TODO - Re-write as a (reusable!) function
'''

# Split rows between 'New' and 'Old'; get counts for unique preferredTerms
# Assign the percentage of that month's search share

# Newest rows
newMovers = BiggestMovers.loc['2018-12-23':'2018-12-29'].copy()
newMovers['TimePeriod'] = 'New'
newMovers = newMovers.groupby('preferredTerm').size()
newMovers = pd.DataFrame({'newMoversCount':newMovers})
# newMovers = newMovers[newMovers['newMoversCount'] >= 10] # throws off calc?
newMoversTotal = newMovers.newMoversCount.sum()
newMovers['newMoversPercent'] = newMovers.newMoversCount / newMoversTotal * 100
newMovers = newMovers.reset_index()

# Comparison rows
oldMovers = BiggestMovers.loc['2018-11-25':'2018-12-22'].copy()
oldMovers['TimePeriod'] = 'Old'
oldMovers = oldMovers.groupby('preferredTerm').size()
oldMovers = pd.DataFrame({'oldMoversCount':oldMovers})
# oldMovers = oldMovers[oldMovers['oldMoversCount'] >= 10]  # throws off calc?
oldMoversTotal = oldMovers.oldMoversCount.sum()
oldMovers['oldMoversPercent'] = oldMovers.oldMoversCount / oldMoversTotal * 100
oldMovers = oldMovers.reset_index()

# Join the two on the index, which is preferredTerm
# Put dupes on the same row
# Include rows that don't have a match in the other. 

# TODO - R&D what the logic should be here, whether to remove terms not 
# searched in BOTH months? This shows everything you can calculate on.
PercentChangeData = pd.merge(oldMovers, newMovers, how ='outer', on='preferredTerm')

# Replace nan with zero
PercentChangeData = PercentChangeData.fillna(0)

# Assign PercentChange, old minus new. If old is bigger, the result is 
# negative, which means searching for this went down.
PercentChangeData['PercentChange'] = PercentChangeData['oldMoversPercent'] - PercentChangeData['newMoversPercent']

# Sort so you can use top of df / bottom of df
PercentChangeData = PercentChangeData.sort_values(by='PercentChange', ascending=True)
PercentChangeData = PercentChangeData.reset_index()
PercentChangeData.drop(['index'], axis=1, inplace=True)          

# This will be the red bars, decline in searching
negative_values = PercentChangeData.head(20)

# This will be the blue bars, increase in searching
positive_values = PercentChangeData.tail(20)
# Change the order
positive_values = positive_values.sort_values(by='PercentChange', ascending=True)
positive_values = positive_values.reset_index()
positive_values.drop(['index'], axis=1, inplace=True) 

# df that the chart consumes
interesting_values =  negative_values.append([positive_values])


# Write out summary table file and file for chart accessibility compliance
writer = pd.ExcelWriter(reports + 'Search05-PercentChangeData.xlsx')
PercentChangeData.to_excel(writer,'PercentChangeData')
# df2.to_excel(writer,'Sheet2')
writer.save()

writer = pd.ExcelWriter(reports + 'Search05-interesting_values.xlsx')
interesting_values.to_excel(writer,'interesting_values')
# df2.to_excel(writer,'Sheet2')
writer.save()


# ----------------------------------------
# Generate Percent Change chart
# ----------------------------------------
'''
--------------------------
IN CASE YOU COMPLETE CYCLE AND THEN SEE THAT LABELS SHOULD BE SHORTENED

# Shorten names if needed
df2['preferredTerm'] = df2['preferredTerm'].str.replace('National Center for Biotechnology Information', 'NCBI')
df2['preferredTerm'] = df2['preferredTerm'].str.replace('Samples of Formatted Refs J Articles', 'Formatted Refs Authors J Articles')
df2['preferredTerm'] = df2['preferredTerm'].str.replace('Formatted References for Authors of Journal Articles', 'Formatted Refs J Articles')

# R&D specific issues
dobby = df2.loc[df2['preferredTerm'].str.contains('Formatted') == True]
dobby = df2.loc[df2['preferredTerm'].str.contains('Biotech') == True]
'''

# Percent change chart
cm = ListedColormap(['#0000aa', '#ff2020'])
colors = [cm(1) if c < 0 else cm(0)
          for c in interesting_values.PercentChange]

# viz --------------
ax = interesting_values.plot(x='preferredTerm', y='PercentChange',
                             figsize=(12,6), kind='bar', color=colors, 
                             fontsize=10)
ax.set_xlabel("preferredTerm")
ax.set_ylabel("Percent change for oldMovers")
ax.legend_.remove()
plt.axvline(x=19.4, linewidth=.5, color='gray')
plt.axvline(x=19.6, linewidth=.5, color='gray')
plt.subplots_adjust(bottom=0.4)
plt.ylabel("Percent change in search frequency")
plt.xlabel("Standardized topic name from UMLS, with additions")
plt.xticks(rotation=60, ha="right", fontsize=9)
plt.suptitle('Biggest movers - How the week just ended is different from the prior 4 weeks', fontsize=16, fontweight='bold')
plt.title('Classify-able search terms only. Last week use of the terms on the left dropped the most, and use of the terms on the right rose the most,\n compared to the previous time period.', fontsize=10)
plt.gcf().subplots_adjust(bottom=0.42)
plt.show()

plt.savefig(reports + 'Search05-BiggestMoversBars.png')


#%%
# =================================================
# 7. Semantic type hierarchy with counts
# =================================================
'''
Best time period? Should this be parallel with x chart...?
'''

selectedTimeframe = lastFourWeeksOfLog
selectedTimeframeText = '4'

lastFourWeeksOfLog.columns
'''
'Referrer', 'adjustedQueryTerm', 'CountForPgDate',
       'ProbablyMeantGSTerm', 'ui', 'preferredTerm', 'SemanticType',
       'SemanticGroupCode', 'SemanticGroup', 'CustomTreeNumber',
       'BranchPosition', 'CustomTag'
'''


# Reduce and reorder
listOfSemTypes = selectedTimeframe[['CustomTreeNumber', 'BranchPosition', 'SemanticType', 'UniqueID', 'CountForPgDate']]
listOfSemTypes = listOfSemTypes[pd.notnull(listOfSemTypes['BranchPosition'])]

# Group and count
listOfSemTypesGr = listOfSemTypes.groupby(['CustomTreeNumber', 'BranchPosition', 'SemanticType'], as_index=False).sum()

# Create HTML docTop
htmlHeaderPartOne = """
<head>
    <title>SemType Counts</title>
    <style>
        body {font-family: Arial, Helvetica, sans-serif; font-size:110%;}
        h1 {font-size: 160%;font-weight:bold;}
        ul {list-style-type: none; margin-left:0; padding-left:0;}
        .indent1 {padding-left:1.5em;}
        .indent2 {padding-left:3em;}
        .indent3 {padding-left:4.5em;}
        .indent4 {padding-left:6em;}
        .indent5 {padding-left:7.5em;}
        .indent6 {padding-left:9em;}
        .indent7 {padding-left:10.5em;}
        .indent8 {padding-left:12em;}
    </style>
</head>
<body>
"""

htmlHeaderPartTwo = """
<h1>Summary Counts by Semantic Type (past {} weeks)</h1>
<p>Based on the <a href="https://www.nlm.nih.gov/research/umls/META3_current_semantic_types.html">
UMLS Semantic Types Taxonomy</a>; queries have been assigned to the 
<strong>most specific level</strong> possible. Some queries have multiple 
assignments. Several categories were
added to accommodate web site queries. &quot;Bibliographic Entity&quot; means 
queries directly related to documents/publishing/PubMed search syntax/etc.
&quot;Numeric ID&quot; means document control numbers, usually from one of 
our databases.
</p>

<ul>
""".format(selectedTimeframeText)

# Create docBottom
htmlFooter = """
</ul>

</body>
</html>
"""


#%%
# ---------------------------------------------------
# Create docMiddle - the Sem Type listing and counts
# ---------------------------------------------------
# FIXME - Create function and reuse, pass in the integer that starts CustomTreeNumber
# Add percent and <mark> the rows (yellow background) when over 20%, or number TBD


# Change to lexicographic sort; treat numbers as string
listOfSemTypesGr['CustomTreeNumber'] = listOfSemTypesGr['CustomTreeNumber'].astype('str')
listOfSemTypesGr = listOfSemTypesGr.sort_values(by='CustomTreeNumber', ascending=True).reset_index(drop=True)

# Order no longer needed?
# listOfSemTypesGr.drop('CustomTreeNumber', axis=1, inplace=True)

# For HTML, best if this is int
listOfSemTypesGr['BranchPosition'] = listOfSemTypesGr['BranchPosition'].astype(int)


# Create strings of the taxonomy and write to file


# Turn df rows into key-value pairs in a dictionary
# https://stackoverflow.com/questions/26716616/convert-a-pandas-dataframe-to-a-dictionary
# TODO - Check whether this is necessary...
semTypesDict = listOfSemTypesGr.set_index('SemanticType').T.to_dict('dict')

'''
If, elif, contains the CustomTreeNumber...
Show first, <h2><a href="SemGroup{SemanticGroupCode}">Web-Specific</a></h2>, CustomTreeNumber = 0
Show second, <h2>Entity</h2>, CustomTreeNumber = 1
# Show third, <h2>Event</h2>, CustomTreeNumber = 2
# Show fourth, <h2>Multiple Groups</h2>, CustomTreeNumber = 3
'''


htmlList1 = []

for key, value in semTypesDict.items():
    htmlList1.append('<li class="indent{}">{} - <a href="semType{}">{:,}</a></li>'.format(value['BranchPosition'], key, value['UniqueID'], value['CountForPgDate']))
# Convert list object to string
htmlList1String = '\n'.join(htmlList1)


#%%
# -----------------------
# Create output file
# -----------------------

semTypesHtml = htmlHeaderPartOne + htmlHeaderPartTwo + htmlList1String + htmlFooter
htmlFile = open(reports + 'CountsBySemType.html', 'w')
htmlFile.write(semTypesHtml)
htmlFile.close()


#%%
# =================================================
# 8. Sem type time series subplots - 26 weeks
# =================================================
'''
FIXME - 
    - Needs to show the change in SEARCH SHARE, over time. Percent share, by week
    - Original purpose: to select the ~5 Sem Types where searches are 
    increasing the most. Add second chart, maintain both a 'top cat' line
    subplot and abiggest mover line chart.

item1 = 'SemType with biggest % change in the past 26 weeks'
item2 = 'SemType with second-biggest % change in the past 26 weeks'
etc.

https://campus.datacamp.com/courses/pandas-foundations/time-series-in-pandas?ex=15
'''

# List SemType names by column, with total count as row 1
st = sslh.groupby('SemanticType').resample('1W').count()['SemanticType'].unstack().T

# Total the sem types, sort cols by freq, reduce
semTypeSparklines = st.reindex(st.sum().sort_values(ascending=False, na_position='last').index, axis=1)
semTypeSparklines.columns
'''
'Unassigned-Long Tail', 'Bibliographic Entity', 'Disease or Syndrome',
       'Organic Chemical|Pharmacologic Substance', 'Foreign unresolved',
       'Numeric ID', 'Therapeutic or Preventive Procedure',
       'Intellectual Product', 'Neoplastic Process',
       'Mental or Behavioral Dysfunction',
       ...
       'Organic Chemical|Pharmacologic Substance|Organic Chemical|Pharmacologic Substance',
       'Laboratory Procedure|Research Activity',
       'Intellectual Product|Research Activity',
       'Intellectual Product|Intellectual Product',
       'Pharmacologic Substance|Biologically Active Substance',
       'Nucleic Acid, Nucleoside, or Nucleotide|Pharmacologic Substance|Biologically Active Substance',
       'Amino Acid, Peptide, or Protein|Pharmacologic Substance|Amino Acid, Peptide, or Protein|Pharmacologic Substance',
       'Amino Acid, Peptide, or Protein|Immunologic Factor|Indicator, Reagent, or Diagnostic Aid',
       'Health Care Related Organization|Health Care Related Organization',
       'Pharmacologic Substance|Biomedical or Dental Material'
'''

semTypeSparklines = semTypeSparklines[['Disease or Syndrome',
       'Organic Chemical|Pharmacologic Substance', 'Therapeutic or Preventive Procedure',
       'Intellectual Product', 'Neoplastic Process',
       'Mental or Behavioral Dysfunction']]

# viz --------------
ax = semTypeSparklines.loc['2018', ['Disease or Syndrome',
       'Organic Chemical|Pharmacologic Substance', 'Therapeutic or Preventive Procedure',
       'Intellectual Product', 'Neoplastic Process']].plot(subplots=True, fontsize=10)
plt.ylabel("Searches conducted")
plt.xlabel("Time")
plt.suptitle('Movement within top Semantic Type categories \n(~130 categories total)', fontsize=14, fontweight='bold')
# plt.title('Semantic types, of which there are ~130. Classified searches only.', fontsize=10)
# plt.legend.remove()
plt.gcf().subplots_adjust(bottom=0.42)
plt.show()

plt.savefig(reports + 'Search07-SemTypeMultiPlot.png')


#%%
# =================================================
# 9. Findings
# =================================================

# Terms to add to navigation, auto-suggest?
# New trends to explore more


#%%

# OBSOLETE?


# -------------------------
# https://stackoverflow.com/questions/37877708/how-to-turn-a-pandas-dataframe-row-into-a-comma-separated-string
# Make each row a separate string; add CSS for indents

html = listOfSemTypesGr.to_string(header=False,
                  index=False,
                  index_names=False).split('\n')
vals = [' '.join(ele.split()) for ele in html]

print(vals)



# https://stackoverflow.com/questions/18574108/how-do-convert-a-pandas-dataframe-to-xml

'''
input:
    
field_1 field_2 field_3 field_4
cat     15,263  2.52    00:03:00
dog     1,652   3.71    00:03:47
test     312    3.27    00:03:41
book     300    3.46    00:02:40

Desired result:
    
<item>
  <field name="field_1">cat</field>
  <field name="field_2">15,263</field>
  <field name="field_3">2.52</field>
  <field name="field_4">00:03:00</field>
</item>
<item>
  <field name="field_1">dog</field>
  <field name="field_2">1,652</field>
  <field name="field_3">3.71</field>
  <field name="field_4">00:03:47</field>
</item>

I want:
    
<ul class="topCat">
  <li class="CustomTreeNumber31.0 BranchPosition2.0">{{SemanticType}}<span style="text-align:right;">{{CountForPgDate}}"></li>
</ul>
'''


def func(row):
    html = ['<li class="']
    for r in row.index:
        html.append('{0}{1}">stop'.format(r, row[r]))
    html.append('</li>')
    return '\n'.join(html)

print('\n'.join(listOfSemTypesGr.apply(func, axis=1)))




'''
htmlWrapSum = ['<html><body>\n\n']
htmlWrapSum.append(treeMapFile.to_html(index=False))
htmlWrapSum.append('\n\n</body></html>')
htmlSum = ''.join(htmlWrapSum)
htmlFile = open(treeMapHtmlRpts + 'SummaryTableCode.html', 'w')
htmlFile.write(htmlSum)
htmlFile.close()
'''




# Create JSON version of df
j = (listOfSemTypesGr.groupby(['CustomTreeNumber', 'BranchPosition', 'SemanticType'], as_index=False)
             .apply(lambda x: x[['CustomTreeNumber', 'BranchPosition', 'SemanticType', 'CountForPgDate']].to_dict('r'))
             .reset_index() # puts in steward cols
             .rename(columns={0:'children'})
             .to_json(orient='records'))
             # .to_json(treeMapReport + 'bLinksMap.json', orient='records'))


# FIXME - Can't figure out how to move data from df into nested lists.
# test = listOfSemTypesGr.to_dict()


# https://stackoverflow.com/questions/43050683/outputting-html-unordered-list-python
def ulify(elements):
    string = "<ul>\n"
    for s in elements:
        string += "    <li>" + str(s) + "</li>\n"
    string += "</ul>"
    return string

print(ulify(['thing', 'other_thing']))








# https://stackoverflow.com/questions/37550928/python-optimal-way-to-write-dict-into-html-table
cars = {
    'car1': {'brand': 'skoda', 'model': 'fabia', 'color': 'blue'},
    'car2': {'brand': 'opel', 'model': 'corsa', 'color': 'red'},
    'car3': {'brand': 'Audi', 'model': 'a3', 'color': 'black'}
    }

def getProp(carValue, carList):

    for car, dic in carList.items():

        for value in dic.values():

            if carValue.lower() == value.lower():
                return dic

    # else return empty dict
    return {}.fromkeys(carList['car1'], '')



def printTable(dic):

    print(HTML.tag('html',
        HTML.tag('body',
            HTML.tag('table',
                HTML.tag('tr',
                    HTML.tag('th', 'CAR'), HTML.tag('th', 'PROPERTIES')
                    ),
                *[HTML.tag('tr',
                    HTML.tag('td', key), HTML.tag('td', value)
                    ) for key, value in dic.items()]
                )
            )
        )
    )

properties = getProp('Opel', cars)
print(properties)
printTable(properties)






# https://stackoverflow.com/questions/29297969/from-python-dictionary-to-html-list
taxonomy = {'Animalia': {'Chordata': {'Mammalia': {'Carnivora': {'Canidae': {'Canis': {'coyote': {},
                                                                        'dog': {}}},
                                                  'Felidae': {'Felis': {'cat': {}},
                                                              'Panthera': {'lion': {}}}}}}},
'Plantae': {'Solanales': {'Convolvulaceae': {'Ipomoea': {'sweet potato': {}}},
                       'Solanaceae': {'Solanum': {'potato': {},
                                                  'tomato': {}}}}}}
    
def printItems(dictObj):
    if len(dictObj):
        print('{}<ul>'.format('  ' * indent))
        for k,v in dictObj.iteritems():
            print('{}<li><input type="checkbox" id="{}-{}">{}</li>'.format(
                            '  ' * (indent+1), k, parent, k))
            printItems(v, k, indent+1)
        print('{}</ul>'.format('  ' * indent))

printItems(test)




# https://stackoverflow.com/questions/3930713/python-serialize-a-dictionary-into-a-simple-html-output
import pprint
z = {'data':{'id':1,'title':'home','address':{'street':'some road','city':'anycity','postal':'somepostal'}}}

def printItems(dictObj, BranchPosition):
    print('  ' * BranchPosition + '<ul>\n')
    for k,v in dictObj.iteritems():
        if isinstance(v, dict):
            print('  ' *BranchPosition + '<li>' + k + ':' + '</li>')
            printItems(v, BranchPosition+1)
        else:
            print(' ' * BranchPosition + '<li>' + k + ':' + v + '</li>')
    print('  ' * BranchPosition + '</ul>\n')

print('<pre>', pprint.pformat(z), '</pre>')





'''
# https://stackoverflow.com/questions/37877708/how-to-turn-a-pandas-dataframe-row-into-a-comma-separated-string
x = listOfSemTypesGr.to_string(header=False,
                  index=False,
                  index_names=False).split('</ul\n\n<ul>')
vals = [','.join(ele.split()) for ele in x]
print(vals)
'''

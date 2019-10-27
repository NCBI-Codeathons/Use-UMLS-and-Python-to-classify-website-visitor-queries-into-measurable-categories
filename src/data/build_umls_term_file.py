#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 25 09:35:31 2018

@author: dan.wendling@nih.gov

Last modified: 2019-10-16

** Search log analysis: (Re)build a local UMLS term list, ~2 times per year **

This script: Creates the files umlsTermListEnglish.csv and umlsTermListForeign.csv,
by downloading and combining information from MRCONSO.RFF and MRSTY.RRF.  
Limits the list to the preferred "atom" for each concept (CUI), sets a limit
on term length, and stacks all the semantic types when there is more than one.

You should check the release notes to see if they changed any columns or the 
column order.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. From MRCONSO.RFF, get string (term name, STR) and the unique identifier 
   for concept (CUI)
3. Create df from local SemanticNetworkReference and MRSTY.RRF
4. Join the two dfs into umlsTermList files: 'STR', 'CUI', 'SemanticType'
5. Write to file, show stats
"""


#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================
'''
HOW TO PREPARE THE SOURCE FILES 

1. Create or free up data/external/umls_distribution (save old version until new one works)
2. Check that you have 40 GB of free disk space.
3. Log in to https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html
4. Download the current MRCONSO.RRF, listed down the page. Move it to 
   data/external/umls_distribution
5. Download the full release
6. Unzip the main file
7. Add the zip extension to 20xxaa-1-meta.nlm and unzip
8. Go into 20xxAA folder > META. Uncompress MRSTY.RRF.gz
9. Move MRSTY.RRF to data/external/umls_distribution
10. Remove the distribution files if you want to recover space, now or after 
    successful script run.
'''

import pandas as pd
import os

# Set working directory and directories for read/write
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')

dataRaw = 'data/external/umls_distribution2019AA/' # Put log here before running script
dataMatchFiles = 'data/matchFiles/' # Permanent helper files; both reading and writing required
reports = 'reports/'


#%%
# ===========================================================================
# 2. From MRCONSO.RFF, get string (term name, STR) and the unique identifier 
# for concept (CUI)
# ===========================================================================
'''
CONcept Names and SOurces info: https://www.ncbi.nlm.nih.gov/books/NBK9685/#ch03.sec3.3.4
SAB is the abbreviated source name, such as MSH for MeSH...
'''

# Huge import, ~14 million rows. File has no col headers.
VariationsWithinConcept = pd.read_csv(dataRaw + "MRCONSO.RRF", sep='|', 
                                      low_memory=False, index_col=False, 
                                      names = ["CUI","LAT","TS","LUI","STT","SUI","ISPREF",
                                               "AUI","SAUI","SCUI","SDUI","SAB","TTY","CODE",
                                               "STR","SRL","SUPPRESS","CVF"])


#%%
# --------------------------------------------------------------------------
# Limit to MeSH so file can be posted to repo, and matching is easier
meshOnly = VariationsWithinConcept.loc[(VariationsWithinConcept['SAB'] == "MSH")]

# Reduce cols
atomForCui = meshOnly[["STR","CUI","LAT", "SAB"]] # ,"TTY","TS","ISPREF"

# Lower-case STR to match lowercased logs
atomForCui['STR'] = atomForCui['STR'].str.lower()


del [[VariationsWithinConcept]]


"""
#%%
# --------------------------------------------------------------------------
# This version does NOT limit to MeSH 

# Reduce to preferred atom for CUI
atomForCui = VariationsWithinConcept.loc[(VariationsWithinConcept['TS'] == "P")]
atomForCui = atomForCui.loc[(atomForCui['STT'] == "PF")]
atomForCui = atomForCui.loc[(atomForCui['ISPREF'] == "Y")]
# ~5.7 million rows remain
# quickLook = atomForCui[10000:10200]

# Reduce cols
atomForCui = atomForCui[["STR","CUI","LAT"]] # ,"TTY","TS",SAB","ISPREF"

# Lower-case STR to match lowercased logs
atomForCui['STR'] = atomForCui['STR'].str.lower()


'''
# If you want to write out
# 2018AA has 11,612,827 rows
headers = ["STR","CUI","LAT"]
VariationsWithinConcept.to_csv(dataMatchFiles + 'UMLSVariationsWithinConcept.csv', 
                               sep='|', encoding='utf-8', columns = headers)
'''


'''
Just FYI for special cases,
abrasionMaster = atomForCui[atomForCui.STR.str.contains("^abrasion$") == True] # char entities
diabetesMaster = atomForCui[atomForCui.STR.str.contains("^diabetes$") == True]
'''

del [[VariationsWithinConcept]]
"""


#%%
# ===============================================================
# 3. Create df from local SemanticNetworkReference and MRSTY.RRF
# ===============================================================
'''
One CUI can have several Semantic Types. This order of operations allows 
stacking the Semantic Types before matching them with the term file.
'''

# Open custom-created 'Semantic Network' key
'''
Semantic types and groups - see https://semanticnetwork.nlm.nih.gov/ file
SemGroups.txt, has additional info such as a col to build CSS indents in 
reporting, etc.
'''
SemanticNetwork = pd.read_excel(dataMatchFiles + 'SemanticNetworkReference.xlsx')

SemanticNetwork.columns

# Reduce cols. Don't need definitions, etc. here
SemanticNetwork = SemanticNetwork[["TUI", "Abbreviation", "SemanticGroupCode",
                                   "SemanticGroup","SemanticGroupAbr",
                                   "CustomTreeNumber", "SemanticType", 
                                   "BranchPosition", "UniqueID"]]

'''
The below, showing how concept IDs (CUIs) relate to semantic type 
IDs, allows you to join human-readable labels to each other.

MRSTY.RRF; info at https://www.ncbi.nlm.nih.gov/books/NBK9685/

Col.	Description
CUI	Unique identifier of concept
TUI	Unique identifier of Semantic Type
STN	Semantic Type tree number
STY	Semantic Type. The valid values are defined in the Semantic Network.
ATUI	 Unique identifier for attribute
CVF	Content View Flag. Bit field used to flag rows included in Content View. 
    This field is a varchar field to maximize the number of bits available for use.

Sample Record in documentation, HOWEVER 2018AA only has content in the first 2.
C0001175|T047|B2.2.1.2.1|Disease or Syndrome|AT17683839|3840|
'''

TuisByCui = pd.read_csv(dataRaw + "MRSTY.RRF", sep='|', index_col=False, 
                   names = ["CUI","TUI","STN","STY","ATUI","CVF"])
# ~4.1 million rows

ViewSomeTuis = TuisByCui[10000:10500]

# Reduce columns
TuisByCui = TuisByCui[["CUI","TUI"]]

SemanticJoinFile = pd.merge(TuisByCui, SemanticNetwork, left_on='TUI', right_on='TUI', how='left')

# Reduce columns
SemanticJoinFile = SemanticJoinFile[["CUI","SemanticType"]]

# Convert to one concept per row, with multiple SemanticType separated with pipe
SemanticJoinFile = SemanticJoinFile.groupby(['CUI'])['SemanticType'].apply('|'.join).reset_index()
# ~3.8 million rows

'''
ViewSomeSemTypes = SemanticJoinFile[10000:10500]
ViewSomeSemTypes.head()

            CUI                            SemanticType
10000  C0019609  Amino Acid, Peptide, or Protein|Enzyme
10001  C0019611  Amino Acid, Peptide, or Protein|Enzyme
10002  C0019612                                    Cell
10003  C0019613                      Neoplastic Process
10004  C0019618                      Neoplastic Process
'''

del [[SemanticNetwork, ViewSomeTuis, TuisByCui]]


#%%
# ==========================================================================
# 4. Join the two dfs into umlsTermList files: 'STR', 'CUI', 'SemanticType'
# ==========================================================================
'''
Desired result - Data you can match against:
    
    STR	                CUI	         SemanticType
histidine ammonia-lyase	C0019601	     Amino Acid, Peptide, or Protein|Enzyme
history of dentistry   	C0019666	     Occupation or Discipline
hiv	                    C0019682	     Virus
'''

umlsTermList = pd.merge(atomForCui, SemanticJoinFile, left_on='CUI', right_on='CUI', how='left')
# ~5.7 million rows

umlsTermList.rename(columns={'CUI': 'ui', 'STR': 'preferredTerm'}, inplace=True)

# Add wordCount so matching can try 'reproduction rights' before 'reproduction', etc.
umlsTermList['wordCount'] = umlsTermList['preferredTerm'].str.split().str.len()
umlsTermList = umlsTermList.sort_values(by='wordCount', ascending=False)

# Some UMLS terms are super long and I don't think people are using these in
# site search, so, cutting off at 7 words
umlsTermList = umlsTermList[umlsTermList['wordCount'] <= 5] #  == True
# ~4.9 million rows. I also doubt that searchers use the 7-word terms, but, leaving
# them in for now. Example: mechanical complication of biological heart valve graft

umlsTermList.columns
'''
'preferredTerm', 'ui', 'LAT', 'SemanticType', 'wordCount'
'''

# Separate into English and Foreign
umlsTermListEnglish = umlsTermList.loc[(umlsTermList['LAT'] == "ENG")] # ~3.2 million rows
umlsTermListForeign = umlsTermList.loc[(umlsTermList['LAT'] != "ENG")]  # ~1.7 million rows

# Correct result? Eyeball.
viewRowsEnglish = umlsTermListEnglish[10000:10500]
viewRowsEnglish.head()


#%%
# =============================
# 5. Write to file, show stats
# =============================

# Write out English terms
umlsTermListEnglish.to_csv(dataMatchFiles + 'umlsTermListEnglish.csv', 
                               sep='|', encoding='utf-8',
                               columns=['preferredTerm', 'ui', 'SemanticType', 'wordCount'],
                               index=False)

# Write out Foreign terms
umlsTermListForeign.to_csv(dataMatchFiles + 'umlsTermListForeign.csv', 
                               sep='|', encoding='utf-8',
                               columns=['preferredTerm', 'ui', 'SemanticType', 'wordCount'],
                               index=False)

# Counts
SemTypeCount = umlsTermListEnglish['SemanticType'].value_counts().reset_index()
SemTypeCount.rename(columns={'SemanticType': 'Count', 'index': 'SemanticType'}, inplace=True)

SemTypeCount.to_csv(reports + 'UMLS-SemTypeCount.csv', 
                               sep=',', encoding='utf-8',
                               columns=['SemanticType', 'Count'],
                               index=False)




#%%

del [[atomForCui, SemanticJoinFile, umlsTermList, umlsTermListEnglish, umlsTermListForeign]]


'''
How to open the result:
    
umlsTermListEnglish = pd.read_csv(dataMatchFiles + 'umlsTermListEnglish.csv', sep='|')
umlsTermListEnglish.columns

umlsTermList.rename(columns={'adjustedQueryTerm': 'preferredTerm'}, inplace=True)
'''


#%%



# EXTRA STUFF

'''
Use this table for ML, etc. matching to visitor query terms.

Includes concept variations across languages and variations in punctuation, 
acronyms vs spelled out, etc. Terms in non-Roman languages are here but 
are not available through the API.

https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/columns_data_elements.html
https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/abbreviations.html

https://www.ncbi.nlm.nih.gov/books/NBK9685/
    Top-level description: https://www.ncbi.nlm.nih.gov/books/NBK9684/#ch02.sec2.3
    col names link: https://www.ncbi.nlm.nih.gov/books/NBK9685/table/ch03.T.concept_names_and_sources_file_mr/?report=objectonly

CUI     Unique identifier for concept
LAT     Language of term
TS      Term status
LUI     Unique identifier for term
STT     String type
SUI     Unique identifier for string
ISPREF	Atom status - preferred (Y) or not (N) for this string within this concept
AUI     Unique identifier for atom - variable length field, 8 or 9 characters
SAUI	Source asserted atom identifier [optional]
SCUI	Source asserted concept identifier [optional]
SDUI	Source asserted descriptor identifier [optional]
SAB     Abbreviated source name (SAB). Maximum field length is 20 alphanumeric characters. Two source abbreviations are assigned:
        Root Source Abbreviation (RSAB) — short form, no version information, for example, AI/RHEUM, 1993, has an RSAB of "AIR"
        Versioned Source Abbreviation (VSAB) — includes version information, for example, AI/RHEUM, 1993, has an VSAB of "AIR93"
        Official source names, RSABs, and VSABs are included on the UMLS Source Vocabulary Documentation page.
TTY     Abbreviation for term type in source vocabulary, for example PN (Metathesaurus Preferred Name) or CD (Clinical Drug). Possible values are listed on the Abbreviations Used in Data Elements page.
CODE    Most useful source asserted identifier (if the source vocabulary has more than one identifier), or a Metathesaurus-generated source entry identifier (if the source vocabulary has none)
STR     String
SRL     Source restriction level
SUPPRESS	    Suppressible flag. Values = O, E, Y, or N
        O: All obsolete content, whether they are obsolesced by the source or by NLM. These will include all atoms having obsolete TTYs, and other atoms becoming obsolete that have not acquired an obsolete TTY (e.g. RxNorm SCDs no longer associated with current drugs, LNC atoms derived from obsolete LNC concepts). 
        E: Non-obsolete content marked suppressible by an editor. These do not have a suppressible SAB/TTY combination.
        Y: Non-obsolete content deemed suppressible during inversion. These can be determined by a specific SAB/TTY combination explicitly listed in MRRANK.
        N: None of the above
        Default suppressibility as determined by NLM (i.e., no changes at the Suppressibility tab in MetamorphoSys) should be used by most users, but may not be suitable in some specialized applications. See the MetamorphoSys Help page for information on how to change the SAB/TTY suppressibility to suit your requirements. NLM strongly recommends that users not alter editor-assigned suppressibility, and MetamorphoSys cannot be used for this purpose.
CVF	    Content View Flag. Bit field used to flag rows included in Content View. This field is a varchar field to maximize the number of bits available for use.


Sample Records (18 col)

C0001175|ENG|P|L0001175|VO|S0010340|Y|A0019182||M0000245|D000163|MSH|PM|D000163|Acquired Immunodeficiency Syndromes|0|N|1792|
C0001175|ENG|S|L0001842|PF|S0011877|N|A2878223|103840012|62479008||SNOMEDCT|PT|62479008|AIDS|9|N|3840|
C0001175|ENG|P|L0001175|VC|S0354232|Y|A2922342|103845019|62479008||SNOMEDCT|SY|62479008|Acquired immunodeficiency syndrome|9|N|3584|
C0001175|FRE|S|L0162173|PF|S0226654|Y|A7438879||M0000245|D000163|MSHFRE|EN|D000163|SIDA|3|N||
C0001175|RUS|S|L0904943|PF|S1108760|Y|A13488500||M0000245|D000163|MSHRUS|SY|D000163|SPID|3|N||
'''

"""

'''
I think the API is correct and this is incorrect. Need to add another table to
this, or something.
    Remove ISPREF = N???
    
   Get to correct CUI by  TS = P; Term status???
    
Second means lexical variant ID is the Preferred version. Works for abrasion; try others.
https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/abbreviations.html#TS

TS (Term Status)	TS Description

P	Preferred LUI of the CUI
S	Non-Preferred LUI of the CUI
p	Preferred LUI of the CUI, suppressible (only used in ORF MRCON)
s	Non-Preferred LUI of the CUI, suppressible (only used in ORF MRCON)


STT (String Type)	STT Description

PF	Preferred form of term
VCW	Case and word-order variant of the preferred form
VC	Case variant of the preferred form
VO	Variant of the preferred form
VW	Word-order variant of the preferred form


TTY (Term Type in Source)
(dozens)
PT	Designated preferred name
'''

# ========================================================
# 6. Run exact match against UMLS master file of 10m rows
# ========================================================
'''
Skip this if you haven't prepared files. While this procedure can save API 
usage, it requires exact matches with the UMLS data using customized source files, 
limiting the payoff, and it requires working knowledge of a local UMLS
file distribution. Building the capability for this is not included here.
'''

# List of unique unassigned terms and frequency of occurrence
listOfUniqueUnassignedAfterFindReplace = searchLog[pd.isnull(searchLog['preferredTerm'])] # was SemanticGroup
listOfUniqueUnassignedAfterFindReplace = listOfUniqueUnassignedAfterFindReplace.groupby('adjustedQueryTerm').size()
listOfUniqueUnassignedAfterFindReplace = pd.DataFrame({'timesSearched':listOfUniqueUnassignedAfterFindReplace})
listOfUniqueUnassignedAfterFindReplace = listOfUniqueUnassignedAfterFindReplace.sort_values(by='timesSearched', ascending=False)
listOfUniqueUnassignedAfterFindReplace = listOfUniqueUnassignedAfterFindReplace.reset_index()

# Open revised version of MRCONSO.RRF. Includes cols Variation, CUI
VariationsWithinConcept = pd.read_csv("umls_distribution/VariationsWithinConcept.csv", sep='|', 
                                      low_memory=False, index_col=False)

# Inner join, adjustedQueryTerm matching Variation
listAfterMaster = pd.merge(listOfUniqueUnassignedAfterFindReplace, VariationsWithinConcept, how='inner', left_on='adjustedQueryTerm', right_on='Variation')

listAfterMaster.head()
listAfterMaster.columns
'''
'adjustedQueryTerm', 'timesSearched', 'Unnamed: 0', 'Variation', 'CUI',
       'Language'
'''

# Reduce cols
listAfterMaster = listAfterMaster[['adjustedQueryTerm', 'CUI']]

# Reduce to exact matches (Next version of VariationsWithinConcept, remove case variations)
listAfterMaster.drop_duplicates(keep='first', inplace=True)

# Update log


# Problem with assigning CUIs
abrasionMaster = VariationsWithinConcept[VariationsWithinConcept.Variation.str.contains("abrasion") == True] # char entities



'''
Results for one-word term, abrasion; when term is one word I want to assign same thing, here C1302752
Metathesaurus considers these an "exact match":
    
Search Results (5)
C0043242	  Superficial abrasion
C0518443	  skin abrasion
C0580209	  Surgical abrasion
C1302752	  Abrasion
C1627366	  Abrasion Pharmacologic Substance


C1302752 has TS=P

'''

"""


'''
You'll see that one CUI can be assigned to many different variations on a term.

CuiEnglishPreferrred = VariationsWithinConcept[VariationsWithinConcept.LAT.str.contains("ENG") == True] # char entities
CuiEnglishPreferrred = CuiEnglishPreferrred[VariationsWithinConcept.ISPREF.str.contains("Y") == True] # char entities
# TTY=PEP sounded useful, but many entries don't seem to have a PEP (Preferred Entry Term)
viewSome = CuiEnglishPreferrred[0:500]
'''

# Use UMLS and Python to classify website visitor queries into measurable categories

Search log data for large web sites are often too verbose and inharmonious to analyze. The site www.nlm.nih.gov has around 100,000 visitor queries per month, with many variations on the same conceptual ideas. For this reason, many web managers are not looking for meaning in their search logs. This project uses Python with the UMLS MetaMap and other techniques to classify search terms to the Unified Medical Language System (UMLS). 

Use case: A web analytist could say to a product owner, "Did you know that last month, 30 percent of our home page searches were about drugs? Should we take action on this?

## Why is this project applicable to others in the community?

Site search represents the direct expression of our visitors’ intent. We could use this data to improve our staff’s awareness of what customers want from us. For example, we could (1) Cluster and analyze trends we know about. For multi-faceted topics that directly relate to our mission, we could create customized analyses using Python to collect the disparate keywords people might search for into a single “bucket.” Where can we create a better match between user interest and our content? Where might we improve our site structure and navigation? (2) Focus staff work onto new trends, as the trends emerge. When something new starts to happen that can be matched to our mission statement, we can start new content projects to address the emerging need in HTML pages, social media posts, etc. The eventual goal is to post a Python code package that other HHS web managers can use to classify their own search logs.

## Top objectives

- Implementing MetaMap matching in a lightweight web interface.
- Creating tabular and visual outputs using Pandas, matplotlib/Seaborn/etc. D3.js charts are also a possibility.

## Workflow
 
![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/searches_UMLS_workflow.JPG "Search Terms to UMLS")

## Dependencies
### Pre-Processing tools
  List of abbreviations for Journals cited in Pubmed (https://www.nlm.nih.gov/bsd/serfile_addedinfo.html). File in the github  repository: J_Medline.txt.
  - Medical language abbreviations -pending create de file. 
    Natural Language Processing Tool Kit through Python: delete punctuation, delete string that are numbers only, lower case,  limit to trigrams, English stopwords.
- Metamap JAVA API, https://metamap.nlm.nih.gov/JavaApi.shtml
- Python Machine Learning Packages
  Pandas
  K-Nearest Neighbor and FuzzyWuzzy to determine Machine Learning  
  Matplot Lib
  Flask
  Dyango
  
More implementation advice: (https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki)

## Mapping search terms to the UMLS

To take full advantage of the features offered by the UMLS it is important to base the search term to UMLS mappings on a knowledge engine that not only finds synonyms but also processes the text in a consistent manner to obtain the best relevant results.

Metamap is a program developed by Lister Hill Medical Center with the purpose of improving medical text retrieval. It is based on the use of linguistic techniques and built on a knowledge base engine that includes:  tokenization, sentence boundary determination, acronym/abbreviation identification, part of speach tagging, lexical lookup in the Specialist Lexicon, and syntactic analysis through shallow paring of phrases, and mapping of the terms to the UMLS. The output is enhanced with a ranking score that allows the user to select the best matching terms, the UMLS prefered term, the Concept Unique Identifier (CUI) and the UMLS semantic types. 

For the purposes of this codethon we used the top 100 user search terms for one week in October. The search strings are submitted to Metamap through -edits here later depending on what we end up using- requesting the output in MetaMap Indexing (MMI) output. The output includes string identifyer, ranking score, UMLS preferred term, UMLS Concept Unique Identifier (CUI), Semantic Type List, Trigger Information (string, code and location used to identify the UMLS concept), Location (text offsets), MeSH treecode(s) when available.

## Team/People

Dan Wendling NLM/LO/PSD

Victor Cid NLM/LHC/CgSB

Dmitry Revoe NLM/NCBI/MGB

Laritza Rodriguez NLM/LHC/CSB

Wenya Rowe NLM/NCBCI/CBB

Rachit Bhatia NLM/OCCS/STB

## Past work

https://github.com/NCBI-Hackathons/Semantic-search-log-analysis-pipeline

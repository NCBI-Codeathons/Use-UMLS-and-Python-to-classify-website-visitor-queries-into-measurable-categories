# Use UMLS and Python to classify website visitor queries into measurable categories

Analytics data for *search* for large web sites is often too verbose and inharmonious to analyze. One "portal" site studied receives around 150,000 "clicks" per month from search-engine results screens, and around 100,000 queries per month from site search. Reporting for each has many variations on the same conceptual ideas, making the content difficult to analyze. For this reason, many web managers are not looking for meaning in the search terms people are using. 

How might we put more-frequent queries into "buckets" of broader topics, so subject matter experts can determine how well our customers are finding what they are looking for, and to see if our web site should be updated to serve those information needs better?

This tool operates on default reports from Google Analytics, using Python and the [MetaMap knowledge engine](https://metamap.nlm.nih.gov) to tag queries to categories in the [Semantic Network](https://semanticnetwork.nlm.nih.gov). MetaMap and the Semantic Network are components of the [Unified Medical Language System (UMLS)](https://www.nlm.nih.gov/research/umls/index.html). The current start-up script was written for Linux.

**Use case:** A web analytist could say to a product owner, "Did you know that last month, 30 percent of your home page searches were about drugs? Should we take action on this?

## Screenshots

![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/screenshot-input.png "screen to upload file")


## Why is this project applicable to others in the community?

Search represents the direct expression of our visitors’ intent. We could use this data to improve our staff’s awareness of what customers want from us. For example, we could:

1. **Cluster and analyze trends we know about.** For multi-faceted topics that directly relate to our mission, we could create customized analyses using Python to collect the disparate keywords people might search for into a single “bucket.” Where can we create a better match between user interest and our content? Where might we improve our site structure and navigation? 
2. **Focus staff work onto new trends, as the trends emerge.** When something new starts to happen that can be matched to our mission statement, we can deploy social media posts on the new topic and start new content projects to address the emerging need. The eventual goal is to post a Python code package that other HHS web managers can use to classify their own search logs.

## Top objectives

- Implement MetaMap matching in a lightweight web interface.
- Create tabular and visual outputs using Pandas, matplotlib/Seaborn/etc. D3.js charts are also a possibility.

## Mapping search terms to the UMLS

To take full advantage of the features offered by the UMLS it will be important to tag search terms to UMLS mappings with a knowledge engine that not only finds synonyms, but also processes the text in a consistent manner to obtain the best relevant results.

Metamap is a program developed by Lister Hill Medical Center with the purpose of improving medical text retrieval. It is based on the use of linguistic techniques and built on a knowledge base engine that includes:  tokenization, sentence boundary determination, acronym/abbreviation identification, part of speach tagging, lexical lookup in the Specialist Lexicon, and syntactic analysis through shallow paring of phrases, and mapping of the terms to the UMLS. The output is enhanced with a ranking score that allows the user to select the best matching terms, the UMLS prefered term, the Concept Unique Identifier (CUI) and the UMLS semantic types.

For the purposes of this codethon we used the top 100 user search terms for one week in October. The search strings are submitted to Metamap through -edits here later depending on what we end up using- requesting the output in MetaMap Indexing (MMI) output. The output includes string identifyer, ranking score, UMLS preferred term, UMLS Concept Unique Identifier (CUI), Semantic Type List, Trigger Information (string, code and location used to identify the UMLS concept), Location (text offsets), MeSH treecode(s) when available.

The unmatched terms are processed with FuzzyWuzzy to create clusters, analyze trends and re-process to find additional matches.

## Workflow

![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/searches_UMLS_workflow.JPG "Search Terms to UMLS")

## Dependencies

### Pre-Processing tools

* [Metamap JAVA API](https://metamap.nlm.nih.gov/JavaApi.shtml)
* (Linux startup script)
* Python
** Pandas
** scikit-learn's K-Nearest Neighbors
** FuzzyWuzzy for fuzzy matching and clustering
** Matplotlib
** Flask
** Optional: Django if assistance in manual matching is needed.

Yet to be integrated; may be useful:

* List of abbreviations for *[Journals cited in Pubmed](https://www.nlm.nih.gov/bsd/serfile_addedinfo.html);* file in this github repository: J_Medline.txt
- Medical language abbreviations
- Natural Language Processing Tool Kit (NLTK) Python package: delete some punctuation, delete strings that appear to be numeric database IDs, limit to trigrams, English stopwords.

[More implementation advice](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/wiki)

## Processing and Output

Search Strings input used for MetaMap and FuzzyWuzzy
![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/wordcloud_search_strings.JPG "Search terms")

Webservice input screen:
![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/webserver%20interfase.jpg "File Upload for Processing")

Search strings processed into UMLS semantic types categories:
![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/metamap%20output.JPG "UMLS Semantic Types Categories")

## Future work

- Implement pre-processing procedures to tag numeric IDs, foreign languages, bibliographic entities (journal names, document titles, etc.)
- Implement post-processing procedures to surface untagged queries above a frequently threshold, and facilitate their manual tagging so they will be automatically tagged in the future

## References

[An overview of MetaMap](https://ii.nlm.nih.gov/Publications/Papers/JAMIA.2010.17.Aronson.pdf)

## Team/People

* Dan Wendling, NLM/LO/PSD
* Victor Cid, NLM/LHC/CgSB
* Damon Revoe, NLM/NCBI/MGV
* Laritza Rodriguez, NLM/LHC/CSB
* Wenya Rowe, NLM/NCBCI/CBB
* Rachit Bhatia, NLM/OCCS/STB

## Past work

https://github.com/NCBI-Hackathons/Semantic-search-log-analysis-pipeline

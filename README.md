# Classify website visitor queries into measurable categories

> **Chart and respond to trends in information seeking, by classifying your web visitor queries to a taxonomy and an ontology**

Analytics data for *search* for large web sites is often too verbose and inharmonious to analyze. One "portal" site studied receives around 150,000 "clicks" per month from search-engine results screens, and around 100,000 queries per month from site search. Reporting for each has many variations on the same conceptual ideas, making the content difficult to analyze and summarize. For this reason, many web managers are not looking for meaning in the search terms people are using. 

How might we put more-frequent queries into "buckets" of broader topics, so subject matter experts can focus on their own "buckets" and determine how well customers are finding what they are looking for? This in turn will help the SMEs envision ways to serve those information needs better.

Search represents the direct expression of our visitors’ intent. We could use this data to improve our staff’s awareness of what customers want from us. 

## Use cases

1. A web analytist could say to a product owner, "Did you know that last month, 30 percent of your home page searches were about drugs? Should we take action on this? How might we improve task completion and reduce time on task, for this type of information need?
2. We could cluster and analyze **trends we know about.** For multi-faceted topics that directly relate to our mission, we could create customized analyses using Python to collect the disparate keywords people might search for into a single “bucket.” Where can we create a better match between user interest and our content? Where might we improve our site structure and navigation? 
3. We could focus staff work onto **new trends,** as the trends emerge. When something new starts to happen that can be matched to our mission statement, we can deploy social media posts on the new topic and start new content projects to address the emerging information need.

## Top objectives

* Interact with the MetaMap knowledge engine to tag out-of-the-box GA reports, through an easy-to-use web interface. Focus first on the GA report Acquisition > Search Console > Queries.
* Create tabular and visual outputs using Pandas, matplotlib, C3.js, D3.js and/or Tableau.

More specifically, processing will use Python 3 and the National Library of Medicine's [MetaMap knowledge engine](https://metamap.nlm.nih.gov) to tag queries to categories in NLM's [Semantic Network](https://semanticnetwork.nlm.nih.gov). MetaMap and the Semantic Network are components of NLM's [Unified Medical Language System (UMLS)](https://www.nlm.nih.gov/research/umls/index.html). The current start-up script was written for Linux.

## Screenshots

<kbd><img src="https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/screenshot-input.png" alt="screen to upload file" /></kbd>

<kbd><img src="https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/metamap%20output.JPG" alt="UMLS Semantic Types Categories" /></kbd>

## Mapping search terms to the UMLS

The UMLS MetaMap knowledge engine maps to synonyms takes into account lexical variations, and processes text in a consistent manner to obtain the best relevant results.

Metamap is a program developed by Lister Hill Medical Center with the purpose of improving medical text retrieval. It is based on the use of linguistic techniques and built on a knowledge base engine that includes:  tokenization, sentence boundary determination, acronym/abbreviation identification, part of speach tagging, lexical lookup in the Specialist Lexicon, and syntactic analysis through shallow paring of phrases, and mapping of the terms to the UMLS. The output is enhanced with a ranking score that allows the user to select the best matching terms, the UMLS prefered term, the Concept Unique Identifier (CUI) and the UMLS semantic types.

For the purposes of this codethon we used the top 100 user search terms for one week in October. The search strings are submitted to Metamap through -edits here later depending on what we end up using- requesting the output in MetaMap Indexing (MMI) output. The output includes string identifyer, ranking score, UMLS preferred term, UMLS Concept Unique Identifier (CUI), Semantic Type List, Trigger Information (string, code and location used to identify the UMLS concept), Location (text offsets), MeSH treecode(s) when available.

The unmatched terms are processed with FuzzyWuzzy to create clusters, analyze trends and re-process to find additional matches.

## Workflow

Only partially implemented during this Codeathon.

<kbd><img src="https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/workflow.png" alt="Workflow" /></kbd>

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

## Additional output

Search Strings input used for MetaMap and FuzzyWuzzy
![alt text](https://github.com/NCBI-Codeathons/Use-UMLS-and-Python-to-classify-website-visitor-queries-into-measurable-categories/blob/master/wordcloud_search_strings.JPG "Search terms")

## Future work

- Implement pre-processing procedures to tag numeric IDs, foreign languages, bibliographic entities (journal names, document titles, etc.)
- Implement post-processing procedures to surface untagged queries above a frequently threshold, and facilitate their manual tagging so they will be automatically tagged in the future

## Influences and thanks

* [An overview of MetaMap](https://ii.nlm.nih.gov/Publications/Papers/JAMIA.2010.17.Aronson.pdf)
* McCray AT, Burgun A, Bodenreider O. (2001). Aggregating UMLS semantic types for reducing conceptual complexity. Stud Health Technol Inform. 84(Pt 1):216-20. PMID: 11604736. See also https://semanticnetwork.nlm.nih.gov/
* Lai KH, Topaz M, Goss FR, Zhou L. (2015). Automated misspelling detection and correction in clinical free-text records. J Biomed Inform. Jun;55:188-95. doi: 10.1016/j.jbi.2015.04.008. Epub 2015 Apr 24. PMID: 25917057.
* Thanks to NCBI Codeathon staff and participants; NLM-PSD-RWS Management; 2017 HHS Data Science CoLab Bootcamp (HHS-CTO and participants); UMLS staff; OCCS/AB Research & Development; OCCS Desktop Support; Data Society staff; many reviewers.

## Team/People

* Dan Wendling, team lead, NLM/LO/PSD
* Victor Cid, NLM/LHC/CgSB
* Damon Revoe, NLM/NCBI/MGV
* Laritza Rodriguez, NLM/LHC/CSB
* Wenya Rowe, NLM/NCBCI/CBB
* Rachit Bhatia, NLM/OCCS/STB

## Past work

https://github.com/NCBI-Hackathons/Semantic-search-log-analysis-pipeline

# Use UMLS and Python to classify website visitor queries into measurable categories

Activity logs for internal search (site search) of large web sites are often too verbose and inharmonious to analyze. The site www.nlm.nih.gov has around 100,000 visitor queries per month, with many variations on the same conceptual ideas. Combining log entries such as “ACA” and “Affordable Care Act” and “ObamaCare” across tens of thousands of rows, for example, is far too difficult for a human to do. An informal poll at the 2018 HHS Digital Community Day found that only two HHS web managers out of dozens, were looking for meaning in their search logs. This project uses an existing Python codebase and multiple techniques to classify search terms to the Unified Medical Language System (UMLS), with new work in tokenizing and vectorizing. We will explore how tools such as scikit-learn, TensorFlow, Keras, or PyTorch, might improve matching visitor input to the UMLS.

## Why is this project applicable to others in the community?

Site search represents the direct expression of our visitors’ intent. We could use this data to improve our staff’s awareness of what customers want from us. For example, we could (1) Cluster and analyze trends we know about. For multi-faceted topics that directly relate to our mission, we could create customized analyses using Python to collect the disparate keywords people might search for into a single “bucket.” Where can we create a better match between user interest and our content? Where might we improve our site structure and navigation? (2) Focus staff work onto new trends, as the trends emerge. When something new starts to happen that can be matched to our mission statement, we can start new content projects to address the emerging need in HTML pages, social media posts, etc. The eventual goal is to post a Python code package that other HHS web managers can use to classify their own search logs.

## Past work

This was a project for the HHS CoLab data science bootcamp, then was an NCBI Hackathon project. NOTE: this is an old version of the code; new code will be posted here. https://github.com/NCBI-Hackathons/Semantic-search-log-analysis-pipeline

Will be updated here, later: Project workflow / pipeline chart


## Top objectives

- Most important for future viability: Testing for the best category prediction using scikit-learn, TensorFlow, etc. tools., from existing sample data
- Team members with UMLS login (free) can work with that API and vocabularies other than MeSH. Can do this Wednesday if needed, if there is interest
- Creating tabular and visual outputs using Pandas, matplotlib/Seaborn/etc., Tableau: Search wiki for "Wireframing for the search log analysis project," for visual ideas. D3.js charts are also a possibility
- Team members with access to Google Analytics and Google Search Console APIs can bring in content from those systems
- The code for working with the noSQL/Django manual-coding interface (feeding the training set) could be improved, and perhaps term predictions could be added to it.
- We will have Excel files of fuzzy matched terms that are wrong. These can be edited using Excel.
- More to follow

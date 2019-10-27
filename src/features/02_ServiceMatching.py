#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 09:53:59 2019

@authors: dan.wendling@nih.gov

Last modified: 2019-10-25

** Search query analyzer, Part 2 **

This script: For items that were not matched, generate options to post to the
interface in 03.

THIS SCRIPT MUST BE RUN MANUALLY, ONE MODULE AT A TIME.


----------------
SCRIPT CONTENTS
----------------

1. Start-up / What to put into place, where
2. Generate spelling suggestion file using CSpell
(Consider a step that updates spellings before MetaMap)
3. Run MetaMapLite API

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


# Set working directory, read/write locations
# CHANGE AS NEEDED
envHome = (os.environ['HOME'])
os.chdir(envHome + '/Projects/classifysearches')


#%%
# ==================================================
# 2. Generate spelling suggestion file using CSpell
# ==================================================
'''
Install the Java application CSpell, "a distributable spell checker for consumer
language," from https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/index.html

Specifically, https://lsg3.nlm.nih.gov/LexSysGroup/Projects/cSpell/current/web/download.html
'''

# TODO - Write code to run the Java jar file from within this script - automate.

'''
** RUN MANUALLY FROM COMMAND LINE **

Currently I am running this manually, using the following command in Terminal.
CSpell -i:unmatchedUniquesFromStep1.txt -si -o:csplell-out.txt

File is written to /Projects/semanticsearch/.
'''

CSColNames = ['sourceID', 'Suggestion']

CSResultsRaw = pd.read_csv('csplell-out.txt', sep = '|', names=CSColNames) # , skiprows=2
CSResultsRaw.columns


#%%
# ============================================
# 2. Start-up / What to put into place, where
# ============================================

MMColNames = ['sourceID', 'OutputType', 'Score', 'PreferredName', 'CUI', 'SemanticType', 
            'TriggerInfo', 'PositionalInfo', 'MeSHTreeCode']

# Skip 2 lines
MMResultsRaw = pd.read_csv('test/MmOutput.txt', sep = '|', names=MMColNames) # , skiprows=2
MMResultsRaw.columns


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 09:53:59 2019

@author: wendlingd
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
os.chdir('/Users/wendlingd/Projects/classifysearches')





#%%
# ============================================
# 1. Start-up / What to put into place, where
# ============================================

colNames = ['sourceID', 'OutputType', 'Score', 'PreferredName', 'CUI', 'SemanticType', 
            'TriggerInfo', 'PositionalInfo', 'MeSHTreeCode']

# Skip 2 lines
MMResultsRaw = pd.read_csv('test/MmOutput.txt', sep = '|', names=colNames) # , skiprows=2
MMResultsRaw.columns


# -*- coding: utf-8 -*-
"""
Created on Mon Jul 18 15:57:13 2016

@author: natek
"""
from __future__ import division
import numpy as np
import pandas as pd

def fluxMain(to_file, area, bin_size):
    
    df = pd.read_csv(to_file, skiprows=[0,1,2], delim_whitespace=True, usecols=[0,1,2,3], names=['ID','JD','RE','FE'])
    print df.head()

fluxMain('C:\\Anaconda2\\Stuff\\6119.2016.0625.0.thresh',0,0)
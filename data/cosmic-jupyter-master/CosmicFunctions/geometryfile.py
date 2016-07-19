# -*- coding: utf-8 -*-
"""
Created on Mon Jul 11 14:46:50 2016

geometry.py
sorts out geometry in correct format, to be reworked later

@author: natek
"""

#Sample Geometry file
#
#	All the .geo files should be in this format for parsing
#
#	[timestamp]{float}	#the time that the following 8 lines were valid for this detector (a partial julian day)
#	[latitude]{hh.mm.pppp}		#pppp is for the 4 digit partial (decimal) minute in degrees (hh < 0 means North of the equator)
#	[longitude]{hhh.mm.pppp}	#if hhh is negative, this indicates West of the Prime Meridian
#	[altitude]{float in meters}	#to 1 decimal accuracy
#	[stacked]{boolean}	#flagged true if the counters are stacked
#
#		- all locations are relative to the *SPECIFIED GSP FOR THIS SITE* **in meters** -
#chan1:	[EAST-WEST location]{float}	[NORTH-SOUTH location]{float}	[UP-DOWN location]{float}	[AREA]{float}
#chan2:	[EAST-WEST location]{float}	[NORTH-SOUTH location]{float}	[UP-DOWN location]{float}	[AREA]{float}
#chan3:	[EAST-WEST location]{float}	[NORTH-SOUTH location]{float}	[UP-DOWN location]{float}	[AREA]{float}
#chan4:	[EAST-WEST location]{float}	[NORTH-SOUTH location]{float}	[UP-DOWN location]{float}	[AREA]{float}
#
#	- these 9 rows of data makeup ONE block of info for each setup of this board (changes when board scintilator locations change) -


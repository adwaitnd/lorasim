#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This library contains useful lora and radio related functions

import numpy as np

# The log-distance model
# Lpl = Lpld0 + 10*gamma*log10(d/d0) + X_normal

# model paramaters are initialized to NaNs to ensure they're setup befor being used
Lpld0 = np.nan
d0 = np.nan
gamma = np.nan
var = np.nan
GL = np.nan

def dBmtomW(pdBm):
	"""[summary]
	
	[description]
	
	Arguments:
		pdBm {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""
	pmW = 10.0**(pdBm/10.0)
	return pmW

def dBmtonW(pdBm):
	"""[summary]
	
	[description]
	
	Arguments:
		pdBm {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""
	pnW = 10.0**((pdBm+90.0)/10.0)
	return pnW

def getRXPower(pTX, distance):
	"""[summary]
	
	[description]
	
	Arguments:
		pTX {[type]} -- [description]
		distance {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""
	# get ideal RX power estimate assuming log-distance model
	pRX = pTX - Lpld0 - 10.0*gamma*np.log10(distance/d0)
	return pRX
	
def getTXPower(pRX, distance):
	"""[summary]
	
	[description]
	
	Arguments:
		pRX {[type]} -- [description]
		distance {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""
	# get ideal TX power estimate assuming log-distance model
	pTX = pRX + Lpld0 + 10.0*gamma*np.log10(distance/d0)
	return pTX

def getDistanceFromPL(pLoss):
	"""[summary]
	
	[description]
	
	Arguments:
		pLoss {float} -- path loss in dBm
	
	Returns:
		float -- distance the signal must travel for given path loss
	"""
	d = d0*(10.0**((pLoss-Lpld0)/(10.0*gamma)))
	return d

def getDistanceFromPower(pTX, pRX):
	"""[summary]
	
	[description]
	
	Arguments:
		pTX {[type]} -- [description]
		pRX {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""
	return getDistanceFromPL(pTX - pRX)

def getFreqBucketsFromSet(BSFreqSetList):
	"""[summary]
	
	This function gives a list of frequencies for various bandwidths used by
	our base-stations. This is currently only applicable to the US 902-928 +
	white space specifications. Other regions would need their own functions
	
	Arguments:
		BSFreqSetList {[type]} -- [description]
	
	Returns:
		[type] -- [description]
	"""

	freqSetList = np.unique(BSFreqSetList)
	freqBuckets = set()
	
	for i in freqSetList:
		if i < 8:
			freqBuckets.update(np.linspace(902300 + 200*8*i, 903700 + 200*8*i, 8, dtype=int))
		else:
			# assuming channel 5 is used for white spaces
			freqBuckets.update(np.linspace(72100 + 200*8*(i-8), 73700 + 200*8*(i-8), 8, dtype=int))

	return freqBuckets
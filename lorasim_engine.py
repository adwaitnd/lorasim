#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import simpy
import weakref
import numpy as np
import multiprocessing as mp

##### simulator options #####
useAimModel = True

### The idea is to modularize the simulator without global variables
class loraNetwork():
	"""[summary]
	
	[description]
	
	Variables:
		
	"""

	def __init__(self, nThreads):
		"""[summary]
		
		[description]
		
		Arguments:
			nthreads {int} -- The number of CPU threads to use. Use <= nCPUs
		"""
		# initialize as many environments as required by multiprocessing
		self.nThreads = nThreads
		print("CPU Threads to use: {}".format(self.nThreads))

		self.bsDict = []
		self.nodeDict = []
		for t in range(nThreads):

			# initialize dictionaries for node storage
			self.bsDict.extend({})
			self.nodeDict.extend({})

		# lorasimenv = simpy.Environment()

	def addRadios(self):
		pass

	def resetEnvironment(self):
		pass

	def simulate(self, endTime):
		pass


class myBS_AIM():
	"""base station object for AIM
	
	[description]
	
	Variables:
		
	"""
	def __init__(self, bsid, position, fset, networkid):
		self.bsid = bsid
		self.x, self.y = position
		self.fset = fset
		self.networkid = networkid
		
		self.packets = {}
			
		freqBuckets = lora_tools.getFreqBucketsFromSet(fset)
		self.packetsInBucket = {}
		self.signalLevel = {}
		for freq in freqBuckets:
			self.packetsInBucket[freq] = {}
			self.signalLevel[freq] = np.zeros((6,1))
		self.demodulator = set() # the set of demodulators being occupied

	
	def addPacket(self, nodeid, packet):
		"""Send a packet to the base station"""
		for fbucket in packet.signalLevel.keys():
			self.signalLevel[fbucket] = self.signalLevel[fbucket] + packet.signalLevel[fbucket]
			self.evaluateFreqBucket(fbucket)
			self.packetsInBucket[fbucket][nodeid] = packet
		self.packets[nodeid] = packet
				
	def evaluateFreqBucket(self, fbucket):
		signalInBucket = np.dot(interactionMatrix, self.signalLevel[fbucket])
		for nodeid, pkt in self.packetsInBucket[fbucket].viewitems():
			if not pkt.isLost and pkt.isCritical:
				if (1 + dBmtonW(6))*(pkt.signalLevel[fbucket][pkt.sf - 7]) < signalInBucket[pkt.sf - 7]:
#                 if (dBmtonW(6))*(pkt.signalLevel[fbucket][pkt.sf - 7]) < signalInBucket[pkt.sf - 7]:
					pkt.isLost = True

		
	def makeCritical(self, nodeid):
		"""Packet from node enters critical section"""
		pkt = self.packets[nodeid]
		if not pkt.isLost:
			if self.evaluatePacket(nodeid) and len(self.demodulator) <= nDemodulator and (pkt.fc, pkt.bw, pkt.sf) not in self.demodulator:
				self.demodulator.add((pkt.fc, pkt.bw, pkt.sf))
				pkt.isCritical = True
			else:
				pkt.isLost = True
				pkt.isCritical = False
				
	def evaluatePacket(self, nodeid):
		pkt = self.packets[nodeid]
		if pkt.isLost:
			return False
		else:
			lostFlag = False
			for fbucket in pkt.signalLevel.viewkeys():
#                 if np.random.randint(0,10000) == 747:
#                     print self.signalLevel[fbucket]
				signalInBucket = np.dot(interactionMatrix[pkt.sf - 7].reshape(1,6), self.signalLevel[fbucket])
				if (1 + dBmtonW(6))*(pkt.signalLevel[fbucket][pkt.sf - 7]) < signalInBucket:
#                 if (dBmtonW(6))*(pkt.signalLevel[fbucket][pkt.sf - 7]) < signalInBucket:
					lostFlag = True
			return not lostFlag

	
	def removePacket(self, nodeid):
		"""Stop sending a packet to the base station i.e. Remove it from all relevant lists"""
		pkt = self.packets[nodeid]
		# if packet was being demodulated, free the demodulator
		if pkt.isCritical and (pkt.fc, pkt.bw, pkt.sf) in self.demodulator:
			# only successfully demodulated packets i.e. Those that are critical are considered to be received
			self.demodulator.remove((pkt.fc, pkt.bw, pkt.sf))
		for fbucket in pkt.signalLevel.viewkeys():
			self.signalLevel[fbucket] = self.signalLevel[fbucket] - pkt.signalLevel[fbucket]
			
#             if np.random.randint(0,10000) == 747:
#                     print self.signalLevel[fbucket]
			
			foo = self.packetsInBucket[fbucket].pop(nodeid)
		foo = self.packets.pop(nodeid)
		return pkt.isCritical and not pkt.isLost
	

class myNode_AIM():
	"""node object for AIM
	
	[description]
	
	Variables:
		
	"""
	def __init__(self, nodeid, position, fset, bw, sf, cr, pTX, period, bsList):
		self.nodeid = nodeid
		self.x, self.y = position
		self.fset = fset
		self.bw = bw
		self.sf = sf
		self.cr = cr
		self.pTX = pTX
		self.period = period
		self.packetNumber = 0
		
		# counters for performance metrics
		self.packetsTransmitted = 0
		self.packetsSuccessful = 0
		
		self.proximateBS = self.generateProximateBS(bsList)
		self.packets = self.generatePacketsToBS()
			
	def generateProximateBS(self, bsList):
		# generate dictionary of base-stations in proximity
		maxInterferenceDist = getDistanceFromPL(self.pTX, interferenceThreshold)
		dist = np.sqrt((bsList[:,1] - self.x)**2 + (bsList[:,2] - self.y)**2)
		index = np.nonzero(dist <= maxInterferenceDist)

		proximateBS = {} # create empty dictionary
		for i in index[0]:
			proximateBS[int(bsList[i,0])] = dist[i]

		return proximateBS
	
	def generatePacketsToBS(self):
		packets = {} # empty dictionary to store packets originating at a node
		
		for bsid, dist in self.proximateBS.viewitems():
			packets[bsid] = myPacket_AIM(self.nodeid, bsid, dist, self.fset, self.bw, self.sf, self.cr, self.pTX)
			
		return packets
	
	def updateTXSettings(self):
		pass

class myPacket_AIM():
	"""[summary]
	
	[description]
	
	Variables:
		
	"""
	def __init__(self, nodeid, bsid, dist, fset, bw, sf, cr, pTX):
		self.nodeif = nodeid
		self.bsid = bsid
		self.dist = dist
		self.fset = fset
		self.bw = bw
		self.sf = sf
		self.cr = cr
		self.pTX = pTX
		self.pRX = getRXPower(pTX, self.dist)
		self.signalLevel = None
#         self.hoppingSequence = self.generateHoppingSequence()
		self.fc = None
		self.packetNumber = 0
		
		self.isLost = False
		self.isCritical = False
		
	def computePowerDist(self):
		global bsDict
		signalLevel = self.getPowerContribution()
		signalLevel = {x:signalLevel[x] for x in signalLevel.viewkeys() & bsDict[self.bsid].signalLevel.viewkeys()}
		return signalLevel
		
	def updateTXSettings(self, seedNo):
		self.packetNumber += 1
		self.fc = 902300 + 200*8*self.fset
#         self.fc = self.hoppingSequence[seedNo % len(self.hoppingSequence)]
		self.signalLevel = self.computePowerDist()
		
		if self.pRX >= sensi[self.sf-7, 1+int(self.bw/250)]:
			self.isLost = False
		else:
			self.isLost = True
			
		self.isCritical = False
		
	def getAffectedFreqBuckets(self):
		"""This funtion returns a list of affected buckets"""

		low = self.fc - self.bw/2 # Note: this is approx due to integer division for 125
		high = self.fc + self.bw/2 # Note: this is approx due to integer division for 125
		lowBucketStart = low - (low % 200) + 100
		highBucketEnd = high + 200 - (high % 200) - 100

		# the +1 ensures that the last value is included in the set
		return xrange(lowBucketStart, highBucketEnd + 1, 200)

	def getPowerContribution(self):
		"""This function should return the power contribution of a packet in various frequency buckets"""
		freqBuckets = self.getAffectedFreqBuckets()
		nBuckets = len(freqBuckets)

		powermW = dBmtonW(self.pRX)
		if nBuckets == 1:
			# this is the most common case with 125 kHz BW in the center of the bucket
			signal = np.zeros((nSF,1))
			signal[self.sf-7] = powermW
			return {freqBuckets[0]:signal}
		elif nBuckets == 4 and self.fc == freqBuckets[0] + 300:
			# this is the second most common case with 500 kHz BW spread between 4 channels
			signalDict = {}
			for i,freq in enumerate(freqBuckets):
				signal = np.zeros((nSF,1))
				if i == 0 or i == 3:
					signal[self.sf-7] = 0.1 * powermW
				else:
					signal[self.sf-7] = 0.4 * powermW
				signalDict[freq] = signal
			return signalDict
		else:
			raise NotImplementedError("non-centered frequencies and 250 kHz not implemented")
			
	def generateHoppingSequence(self):
		
		freqSetList = np.unique(self.fset)
		freqBuckets = []
		if self.bw == 125:
			for i in freqSetList:
				if i < 8:
					freqBuckets.extend(np.linspace(902300 + 200*8*i, 903700 + 200*8*i, 8, dtype=int))
				else:
					# assuming channel 5 is used for white spaces
					freqBuckets.extend(np.linspace(72100 + 200*8*(i-8), 73700 + 200*8*(i-8), 8, dtype=int))
			
		elif self.bw == 500:
			if self.fset < 8:
				freqBuckets.extend([903000 + 1600*i])
			else:
				# white space
				freqBuckets.extend([72900 + 1600*(i-8)])
				pass
			
		return np.random.permutation(freqBuckets)

class myBS_IIM():
	"""base station object for IIM
	
	[description]
	
	Variables:
		
	"""
	def __init__(self):
		pass


class myNode_IIM():
	"""node object for IIM
	
	[description]
	
	Variables:
		
	"""
	def __init__(self):
		raise NotImplementedError("myNode_IIM not yet implemented")

class myPacket_IIM():
	"""[summary]
	
	[description]
	
	Variables:
		
	"""
	def __init__(self):
		pass

if __name__ == "__main__":
	print("This module is meant to be imported, not run directly")

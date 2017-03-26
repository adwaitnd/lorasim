#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
 LoRaSim: simulate collisions in LoRa - multiple base stations variant
 Copyright © 2016 Thiemo Voigt <thiemo@sics.se> and Martin Bor <m.bor@lancaster.ac.uk>

 This work is licensed under the Creative Commons Attribution 4.0
 International License. To view a copy of this license,
 visit http://creativecommons.org/licenses/by/4.0/.

 Do LoRa Low-Power Wide-Area Networks Scale? Martin Bor, Utz Roedig, Thiemo Voigt
 and Juan Alonso, MSWiM '16, http://dx.doi.org/10.1145/2988287.2989163

 $Date: 2016-10-17 13:23:52 +0100 (Mon, 17 Oct 2016) $
 $Revision: 218 $
"""

"""
 SYNOPSIS:
   ./loraDirMulBS.py <nodes> <avgsend> <experiment> <simtime> <basestation> [collision]
 DESCRIPTION:
    nodes
        number of nodes to simulate
    avgsend
        average sending interval in milliseconds
    experiment
        experiment is an integer that determines with what radio settings the
        simulation is run. All nodes are configured with a fixed transmit power
        and a single transmit frequency, unless stated otherwise.
        0   use the settings with the the slowest datarate (SF12, BW125, CR4/8).
        1   similair to experiment 0, but use a random choice of 3 transmit
            frequencies.
        2   use the settings with the fastest data rate (SF6, BW500, CR4/5).
        3   optimise the setting per node based on the distance to the gateway.
        4   use the settings as defined in LoRaWAN (SF12, BW125, CR4/5).
        5   similair to experiment 3, but also optimises the transmit power.
    simtime
        total running time in milliseconds
    basestation
        number of base stations to simulate. Can be either 1, 2, 3, 4, 6, 8 or 24.
    collision
        set to 1 to enable the full collision check, 0 to use a simplified check.
        With the simplified check, two messages collide when they arrive at the
        same time, on the same frequency and spreading factor. The full collision
        check considers the 'capture effect', whereby a collision of one or the
 OUTPUT
    The result of every simulation run will be appended to a file named expX.dat,
    whereby X is the experiment number. The file contains a space separated table
    of values for nodes, collisions, transmissions and total energy spent. The
    data file can be easily plotted using e.g. gnuplot.
"""

import simpy
import random
import numpy as np
import math
import sys
import matplotlib.pyplot as plt
import os
from matplotlib.patches import Rectangle

# turn on/off graphics
graphics = 0

# do the full collision check
full_collision = False

# experiments:
# 0: packet with longest airtime, aloha-style experiment
# 0: one with 3 frequencies, 1 with 1 frequency
# 2: with shortest packets, still aloha-style
# 3: with shortest possible packets depending on distance



# this is an array with measured values for sensitivity
# see paper, Table 3
sf7 = np.array([7,-126.5,-124.25,-120.75])
sf8 = np.array([8,-127.25,-126.75,-124.0])
sf9 = np.array([9,-131.25,-128.25,-127.5])
sf10 = np.array([10,-132.75,-130.25,-128.75])
sf11 = np.array([11,-134.5,-132.75,-128.75])
sf12 = np.array([12,-133.25,-132.25,-132.25])

#
# check for collisions at base station
# Note: called before a packet (or rather node) is inserted into the list
#
# conditions for collions:
#     1. same sf
#     2. frequency, see function below (Martins email, not implementet yet):
def checkcollision(packet):
    col = 0 # flag needed since there might be several collisions for packet
    # lost packets don't collide
    if packet.lost:
       return 0
    if packetsAtBS[packet.bs]:
        for other in packetsAtBS[packet.bs]:
            if other.id != packet.nodeid:
               # simple collision
               if frequencyCollision(packet, other.packet[packet.bs]) \
                   and sfCollision(packet, other.packet[packet.bs]):
                   if full_collision:
                       if timingCollision(packet, other.packet[packet.bs]):
                           # check who collides in the power domain
                           c = powerCollision(packet, other.packet[packet.bs])
                           # mark all the collided packets
                           # either this one, the other one, or both
                           for p in c:
                               p.collided = 1
                       else:
                           # no timing collision, all fine
                           pass
                   else:
                       packet.collided = 1
                       other.packet[packet.bs].collided = 1  # other also got lost, if it wasn't lost already
                       col = 1
        return col
    return 0

#
# frequencyCollision, conditions
#
#        |f1-f2| <= 120 kHz if f1 or f2 has bw 500
#        |f1-f2| <= 60 kHz if f1 or f2 has bw 250
#        |f1-f2| <= 30 kHz if f1 or f2 has bw 125
def frequencyCollision(p1,p2):
    if (abs(p1.freq-p2.freq)<=120 and (p1.bw==500 or p2.freq==500)):
        return True
    elif (abs(p1.freq-p2.freq)<=60 and (p1.bw==250 or p2.freq==250)):
        return True
    else:
        if (abs(p1.freq-p2.freq)<=30):
            return True
    return False

def sfCollision(p1, p2):
    if p1.sf == p2.sf:
        # p2 may have been lost too, will be marked by other checks
        return True
    return False

def powerCollision(p1, p2):
    powerThreshold = 6 # dB
    if abs(p1.rssi - p2.rssi) < powerThreshold:
        # packets are too close to each other, both collide
        # return both packets as casualties
        return (p1, p2)
    elif p1.rssi - p2.rssi < powerThreshold:
        # p2 overpowered p1, return p1 as casualty
        return (p1,)
    # p2 was the weaker packet, return it as a casualty
    return (p2,)

def timingCollision(p1, p2):
    # assuming p1 is the freshly arrived packet and this is the last check
    # we've already determined that p1 is a weak packet, so the only
    # way we can win is by being late enough (only the first n - 5 preamble symbols overlap)

    # assuming 8 preamble symbols
    Npream = 8

    # we can lose at most (Npream - 5) * Tsym of our preamble
    Tpreamb = 2**p1.sf/(1.0*p1.bw) * (Npream - 5)

    # check whether p2 ends in p1's critical section
    p2_end = p2.addTime + p2.rectime
    p1_cs = env.now + Tpreamb
    if p1_cs < p2_end:
        # p1 collided with p2 and lost
        return True
    return False

# this function computes the airtime of a packet
# according to LoraDesignGuide_STD.pdf
#
def airtime(sf,cr,pl,bw):
    H = 0        # implicit header disabled (H=0) or not (H=1)
    DE = 0       # low data rate optimization enabled (=1) or not (=0)
    Npream = 8   # number of preamble symbol (12.25  from Utz paper)

    if bw == 125 and sf in [11, 12]:
        # low data rate optimization mandated for BW125 with SF11 and SF12
        DE = 1
    if sf == 6:
        # can only have implicit header with SF6
        H = 1

    Tsym = (2.0**sf)/bw
    Tpream = (Npream + 4.25)*Tsym
    payloadSymbNB = 8 + max(math.ceil((8.0*pl-4.0*sf+28+16-20*H)/(4.0*(sf-2*DE)))*(cr+4),0)
    Tpayload = payloadSymbNB * Tsym
    return Tpream + Tpayload



#
# this function creates a BS
#
class myBS():
    def __init__(self, id):
        self.id = id
        self.x = 0
        self.y = 0

        # This is a hack for now
        global nrBS
        global maxDist
        global maxX
        global maxY

        if (nrBS == 1 and self.id == 0):
            self.x = maxX/2.0
            self.y = maxY/2.0


        if (nrBS == 3 or nrBS == 2):
            self.x = (self.id+1)*maxX/float(nrBS+1)
            self.y = maxY/2.0

        if (nrBS == 4):
            if (self.id < 2):
                self.x = (self.id+1)*maxX/3.0
                self.y = maxY/3.0
            else:
                self.x = (self.id+1-2)*maxX/3.0
                self.y = 2*maxY/3.0

        if (nrBS == 6):
            if (self.id < 3):
                self.x = (self.id+1)*maxX/4.0
                self.y = maxY/3.0
            else:
                self.x = (self.id+1-3)*maxX/4.0
                self.y = 2*maxY/3.0

        if (nrBS == 8):
            if (self.id < 4):
                self.x = (self.id+1)*maxX/5.0
                self.y = maxY/3.0
            else:
                self.x = (self.id+1-4)*maxX/5.0
                self.y = 2*maxY/3.0

        if (nrBS == 24):
            if (self.id < 8):
                self.x = (self.id+1)*maxX/9.0
                self.y = maxY/4.0
            elif (self.id < 16):
                self.x = (self.id+1-8)*maxX/9.0
                self.y = 2*maxY/4.0
            else:
                self.x = (self.id+1-16)*maxX/9.0
                self.y = 3*maxY/4.0


        print("BSx:", self.x, "BSy:", self.y)

        global graphics
        if (graphics):
            global ax
            # XXX should be base station position
            ax.add_artist(plt.Circle((self.x, self.y), 3, fill=True, color='green'))
            ax.add_artist(plt.Circle((self.x, self.y), maxDist, fill=False, color='green'))

#
# this function creates a node
#
class myNode():
    def __init__(self, id, period, packetlen):
        global bs

        self.id = id
        self.period = period
        self.x = 0
        self.y = 0
        self.packet = []
        self.dist = []
        # this is very complex prodecure for placing nodes
        # and ensure minimum distance between each pair of nodes
        found = 0
        rounds = 0
        global nodes
        while (found == 0 and rounds < 100):
            global maxX
            global maxY
            posx = random.randint(0,int(maxX))
            posy = random.randint(0,int(maxY))
            if len(nodes) > 0:
                for index, n in enumerate(nodes):
                    dist = np.sqrt(((abs(n.x-posx))**2)+((abs(n.y-posy))**2))
                    if dist >= 10:
                        found = 1
                        self.x = posx
                        self.y = posy
                    else:
                        rounds = rounds + 1
                        if rounds == 100:
                            print("could not place new node, giving up")
                            exit(-2)
            else:
                print("first node")
                self.x = posx
                self.y = posy
                found = 1


        # create "virtual" packet for each BS
        global nrBS
        for i in range(0,nrBS):
            d = np.sqrt((self.x-bs[i].x)*(self.x-bs[i].x)+(self.y-bs[i].y)*(self.y-bs[i].y))
            self.dist.append(d)
            self.packet.append(myPacket(self.id, packetlen, self.dist[i], i))
        print(('node %d' %id, "x", self.x, "y", self.y, "dist: ", self.dist))

        self.sent = 0

        # graphics for node
        global graphics
        if (graphics == 1):
            global ax
            ax.add_artist(plt.Circle((self.x, self.y), 2, fill=True, color='blue'))

#
# this function creates a packet (associated with a node)
# it also sets all parameters, currently random
#
class myPacket():
    def __init__(self, nodeid, plen, distance, bs):
        global experiment
        global Ptx
        global gamma
        global d0
        global var
        global Lpld0
        global GL


        # new: base station ID
        self.bs = bs
        self.nodeid = nodeid
        # randomize configuration values
        self.sf = random.randint(6,12)
        self.cr = random.randint(1,4)
        self.bw = random.choice([125, 250, 500])

        # for certain experiments override these
        if experiment==1 or experiment == 0:
            self.sf = 12
            self.cr = 4
            self.bw = 125

        # for certain experiments override these
        if experiment==2:
            self.sf = 6
            self.cr = 1
            self.bw = 500


        # for experiment 3 find the best setting
        # OBS, some hardcoded values
        Prx = Ptx  ## zero path loss by default

        # log-shadow
        Lpl = Lpld0 + 10*gamma*math.log(distance/d0)
        print(Lpl)
        Prx = Ptx - GL - Lpl

        if (experiment == 3):
            minairtime = 9999
            minsf = 0
            minbw = 0

            for i in range(0,6):
                for j in range(1,4):
                    if (sensi[i,j] < Prx):
                        self.sf = sensi[i,0]
                        if j==1:
                            self.bw = 125
                        elif j==2:
                            self.bw = 250
                        else:
                            self.bw=500
                        at = airtime(self.sf,4,20,self.bw)
                        if at < minairtime:
                            minairtime = at
                            minsf = self.sf
                            minbw = self.bw

            self.rectime = minairtime
            self.sf = minsf
            self.bw = minbw
            if (minairtime == 9999):
                print("does not reach base station")
                exit(-1)

        # transmission range, needs update XXX
        self.transRange = 150
        self.pl = plen
        self.symTime = (2.0**self.sf)/self.bw
        self.arriveTime = 0
        self.rssi = Prx
        # frequencies: lower bound + number of 61 Hz steps
        self.freq = 860000000 + random.randint(0,2622950)

        # for certain experiments override these and
        # choose some random frequences
        if experiment == 1:
            self.freq = random.choice([860000000, 864000000, 868000000])
        else:
            self.freq = 860000000

        self.rectime = airtime(self.sf,self.cr,self.pl,self.bw)
        # denote if packet is collided
        self.collided = 0
        self.processed = 0
        # mark the packet as lost when it's rssi is below the sensitivity
        # don't do this for experiment 3, as it requires a bit more work
        if experiment != 3:
            global minsensi
            self.lost = self.rssi < minsensi
            print("node {} bs {} lost {}".format(self.nodeid, self.bs, self.lost))


#
# main discrete event loop, runs for each node
# a global list of packet being processed at the gateway
# is maintained
#
def transmit(env,node):
    while True:
        yield env.timeout(random.expovariate(1.0/float(node.period)))

        # time sending and receiving
        # packet arrives -> add to base station

        node.sent = node.sent + 1
        
        global packetSeq
        packetSeq = packetSeq + 1

        global nrBS
        for bs in range(0, nrBS):
           if (node in packetsAtBS[bs]):
                print("ERROR: packet already in")
           else:
                # adding packet if no collision
                if (checkcollision(node.packet[bs])==1):
                    node.packet[bs].collided = 1
                else:
                    node.packet[bs].collided = 0
                packetsAtBS[bs].append(node)
                node.packet[bs].addTime = env.now
                node.packet[bs].seqNr = packetSeq

        # take first packet rectime
        yield env.timeout(node.packet[0].rectime)

        # if packet did not collide, add it in list of received packets
        # unless it is already in
        for bs in range(0, nrBS):
            if node.packet[bs].lost:
                lostPackets.append(node.packet[bs].seqNr)
            else:
                if node.packet[bs].collided == 0:
                    packetsRecBS[bs].append(node.packet[bs].seqNr)
                    if (recPackets):
                        if (recPackets[-1] != node.packet[bs].seqNr):
                            recPackets.append(node.packet[bs].seqNr)
                    else:
                        recPackets.append(node.packet[bs].seqNr)
                else:
                    # XXX only for debugging
                    collidedPackets.append(node.packet[bs].seqNr)

        # complete packet has been received by base station
        # can remove it
        for bs in range(0, nrBS):
            if (node in packetsAtBS[bs]):
                packetsAtBS[bs].remove(node)
                # reset the packet
                node.packet[bs].collided = 0
                node.packet[bs].processed = 0

#
# "main" program
#

# get arguments
if len(sys.argv) >= 6:
    nrNodes = int(sys.argv[1])
    avgSendTime = int(sys.argv[2])
    experiment = int(sys.argv[3])
    simtime = int(sys.argv[4])
    nrBS = int(sys.argv[5])
    if len(sys.argv) > 6:
        full_collision = bool(int(sys.argv[6]))
    print("Nodes:", nrNodes)
    print("AvgSendTime (exp. distributed):",avgSendTime)
    print("Experiment: ", experiment)
    print("Simtime: ", simtime)
    print("nrBS: ", nrBS)
    if (nrBS > 4 and nrBS!=8 and nrBS!=6 and nrBS != 24):
        print("too many base stations, max 4 or 6 or 8 base stations")
        exit(-1)
    print("Full Collision: ", full_collision)
else:
    print("usage: ./loraDir nrNodes avgSendTime experimentNr simtime nrBS [full_collision]")
    print("experiment 0 and 1 use 1 frequency only")
    exit(-1)


# global stuff
nodes = []
packetsAtBS = []
env = simpy.Environment()


# max distance: 300m in city, 3000 m outside (5 km Utz experiment)
# also more unit-disc like according to Utz
nrCollisions = 0
nrReceived = 0
nrProcessed = 0

# global value of packet sequence numbers
packetSeq = 0

# list of received packets
recPackets=[]
collidedPackets=[]
lostPackets = []

Ptx = 14
gamma = 2.08
d0 = 40.0
var = 0           # variance ignored for now
Lpld0 = 127.41
GL = 0

sensi = np.array([sf7,sf8,sf9,sf10,sf11,sf12])

## figure out the minimal sensitivity for the given experiment
minsensi = -200.0
if experiment in [0,1,4]:
    minsensi = sensi[5,2]  # 5th row is SF12, 2nd column is BW125
elif experiment == 2:
    minsensi = -112.0   # no experiments, so value from datasheet
elif experiment == 3:
    minsensi = np.amin(sensi) ## Experiment 3 can use any setting, so take minimum

Lpl = Ptx - minsensi
print("amin", minsensi, "Lpl", Lpl)
maxDist = d0*(math.e**((Lpl-Lpld0)/(10.0*gamma)))
print("maxDist:", maxDist)

# base station placement
bsx = maxDist+10
bsy = maxDist+10
xmax = bsx + maxDist + 20
ymax = bsy + maxDist + 20

# maximum number of packets the BS can receive at the same time
maxBSReceives = 8



maxX = 2 * maxDist * math.sin(60*(math.pi/180)) # == sqrt(3) * maxDist
print("maxX ", maxX)
maxY = 2 * maxDist * math.sin(30*(math.pi/180)) # == maxdist
print("maxY", maxY)


# prepare graphics and add sink
if (graphics == 1):
    plt.ion()
    plt.figure()
    ax = plt.gcf().gca()

    ax.add_patch(Rectangle((0, 0), maxX, maxY, fill=None, alpha=1))

# list of base stations
bs = []

# list of packets at each base station, init with 0 packets
packetsAtBS = []
packetsRecBS = []
for i in range(0,nrBS):
    b = myBS(i)
    bs.append(b)
    packetsAtBS.append([])
    packetsRecBS.append([])







for i in range(0,nrNodes):
    # myNode takes period (in ms), base station id packetlen (in Bytes)
    # 1000000 = 16 min
    node = myNode(i, avgSendTime,20)
    nodes.append(node)
    env.process(transmit(env,node))

#prepare show
if (graphics == 1):
    plt.xlim([0, xmax])
    plt.ylim([0, ymax])
    plt.draw()
    plt.show()

# store nodes and basestation locations
with open('nodes.txt', 'w') as nfile:
    for node in nodes:
        nfile.write('{x} {y} {id}\n'.format(**vars(node)))

with open('basestation.txt', 'w') as bfile:
    for basestation in bs:
        bfile.write('{x} {y} {id}\n'.format(**vars(basestation)))

# start simulation
env.run(until=simtime)

# print stats and save into file
# print "nrCollisions ", nrCollisions
# print list of received packets
#print recPackets
print("nr received packets", len(recPackets))
print("nr collided packets", len(collidedPackets))
print("nr lost packets", len(lostPackets))

#print "sent packets: ", sent
#print "sent packets-collisions: ", sent-nrCollisions
#print "received packets: ", len(recPackets)
for i in range(0,nrBS):
    print("packets at BS",i, ":", len(packetsRecBS[i]))
print("sent packets: ", packetSeq)

# data extraction rate
der = len(recPackets)/float(packetSeq)
print("DER:", der)
#der = (nrReceived)/float(sent)
#print "DER method 2:", der

# this can be done to keep graphics visible
if (graphics == 1):
    sys.stdin.read()

# save experiment data into a dat file that can be read by e.g. gnuplot
# name of file would be:  exp0.dat for experiment 0
fname = "exp" + str(experiment) + "BS" + str(nrBS) + ".dat"
print(fname)
if os.path.isfile(fname):
    res = "\n" + str(nrNodes) + " " + str(der)
else:
    res = "# nrNodes DER\n" + str(nrNodes) + " " + str(der)
with open(fname, "a") as myfile:
    myfile.write(res)
myfile.close()

exit(-1)
#below not updated


# compute energy
energy = 0.0
mA = 90    # current draw for TX = 17 dBm
V = 3     # voltage XXX
sent = 0
for i in range(0,nrNodes):
#    print "sent ", nodes[i].sent
    sent = sent + nodes[i].sent
    energy = (energy + nodes[i].packet.rectime * mA * V * nodes[i].sent)/1000.0
print("energy (in mJ): ", energy)

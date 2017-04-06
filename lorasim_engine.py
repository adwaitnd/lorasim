import random
import simpy

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
# check for collisions at base station
# Note: called before a packet (or rather node) is inserted into the list
#
# conditions for collions:
#     1. same sf
#     2. frequency, see function below (Martins email, not implementet yet):
def checkcollision_IIM(packet):
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

#
# this function creates a BS
#
class myBS_IIM():
    def __init__(self, id, position):
        self.id = id
        self.x, self.y = position

#
# this function creates a node
#
class myNode_IIM():
    def __init__(self, id, position, period, packetlen):
        global bs

        self.id = id
        self.period = period
        self.x, self.y = position
        self.packet = []
        self.dist = []
        
        self.f, self.bw, self. sf, self.cr = self.getTransmissionParams()
        
        # create "virtual" packet for each BS
        global nrBS
        for i in range(0,nrBS):
            d = np.sqrt((self.x-bs[i].x)*(self.x-bs[i].x)+(self.y-bs[i].y)*(self.y-bs[i].y))
            self.dist.append(d)
            self.packet.append(myPacket(self.id, packetlen, self.dist[i], self.f, i, self.sf, self.cr, self.bw))

        self.sent = 0
        
    def getTransmissionParams(self):
        # this function currently returns fixed parameters
        freq = 902.3
        bw = 125
        sf = 11
        cr = 1
        return freq, bw, sf, cr
    
    def updateTransmissionParams(self):
        # use this function to create a hopping node
        pass

#
# this function creates a packet (associated with a node)
# it also sets all parameters, currently random
#
class myPacket():
    def __init__(self, nodeid, plen, distance, freq, bs, sf, cr, bw):
        global experiment
        global Ptx
        global gamma
        global d0
        global var
        global Lpld0
        global GL
        global sensi


        # new: base station ID
        self.bs = bs
        self.nodeid = nodeid
        
        # randomize configuration values
        self.sf = sf
        self.cr = cr
        self.bw = bw

        # log-shadow
        # note: transmit power is global variable
        Lpl = Lpld0 + 10*gamma*math.log(distance/d0)
#         print Lpl
        Prx = Ptx - GL - Lpl

        # transmission range, needs update XXX
        self.transRange = 150
        self.pl = plen
        self.symTime = (2.0**self.sf)/self.bw
        self.arriveTime = 0
        self.rssi = Prx
        self.freq = freq

        self.rectime = airtime(self.sf,self.cr,self.pl,self.bw)
        # denote if packet is collided
        self.collided = 0
        self.processed = 0

        packet_sensitivity = sensi[sf - 7, int(bw // 250) + 1]
        self.lost = self.rssi < packet_sensitivity
#         if self.lost:
#             print "node {} bs {} lost (rssi = {} < sensi = {})".format(self.nodeid, self.bs, self.rssi, packet_sensitivity)

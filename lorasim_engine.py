import random
import simpy

x_range = []
y_range = []

class myNode():
    """Class for a low-power end-node
    
    [description]
    
    Variables:
        nodeid {[type]} -- numerical identifier for node
    """
    def __init__(self, nodeid, position, period, packetlen):
        """[summary]
        
        [description]
        
        Arguments:
            nodeid {[int]} -- [numeric ID for the node]
            position {[tuple]} -- [2D location coordinate, format: (x,y)]
            period {[type]} -- [how frequently packets are sent (mean of exponential distribution)]
            packetlen {[type]} -- [length of data packets sent by this node]
        """

        self.x, self.y = position   # coordinates
        self.nodeid = nodeid        # numerical identifier
        self.period = period    # average period between messages
        self.packet = []        # list of "virtual" packets sent to each base-station
        self.dist = []          # list of distances to each base-station

class myBS():
    def __init__(self, nodeid, position):

        self.nodeid = nodeid
        self.x, self.y = position
        self.packetsAtBS = []       # list of 

class myPacket():
    def __init__(self, nodeid, bs, freq, bw, sf, cr, plen, ptx):

        self.nodeid = nodeid
        self.bs = bs
        self.freq = freq
        self.bw = bw
        self.sf = sf
        self.cr = cr
        self.ptx = ptx

def transmit(env, node):
    while True:
        yield env.timeout(random.expovariate(1.0/float(node.period)))
    pass

def generateNodeLocation(rng_seed = None):
    """function to generate locations of base-stations and end-devices in the simulation space
    
    [description]
    
    Keyword Arguments:
        rng_seed {[type]} -- [description] (default: {None})
    
    Returns:
        [type] -- [description]
    """
    global x_range
    global y_range

    random.seed(rng_seed)

    x = random.uniform(x_range[0], x_range[1])
    y = random.uniform(y_range[0], y_range[1])
    return x,y
    
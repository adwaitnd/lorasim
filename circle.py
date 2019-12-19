#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
 
theta = np.arange(0, 2*np.pi, 0.01)
xx = [1,2,3,10,15,8]
yy = [1,-1,0,0,7,0]
rr = [7,7,3,6,9,9]
 
fig = plt.figure()
axes = fig.add_subplot(111)
 
i = 0
while i < len(xx):
    x = xx[i] + rr[i] *np.cos(theta)
    y = xx[i] + rr[i] *np.cos(theta)
    axes.plot(x,y)
    axes.plot(xx[i], yy[i], color='#900302', marker='*')
    i = i+1
width = 20
hight = 20
axes.arrow(0,0,0,hight,width=0.01,head_width=0.1,head_length=0.3,fc='k',ec='k')
axes.arrow(0,0,width,0,width=0.01,head_width=0.1,head_length=0.3,fc='k',ec='k')

plt.show()
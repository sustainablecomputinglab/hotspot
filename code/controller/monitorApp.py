#!/usr/bin/python
__author__ = 'shastri@umass.edu'

from datetime import datetime
import os.path
import time

#------------------------------------------
# Globals initialized to default values
#------------------------------------------
monitorApp_lxcName = 'hotSpotLXC'
monitorApp_lastTime = datetime.now()
monitorApp_lastCPU = 0

#------------------------------------------
# Internal functions
#------------------------------------------

def getCpuTime():
    atTime = datetime.now()
    with open('/sys/fs/cgroup/cpu/lxc/hotSpotLXC/cpuacct.usage', 'r') as cpuFile:
        curUsage = int(cpuFile.readline())
        return (atTime,curUsage)
#END getCpuTime


#------------------------------------------
# Public functions
# -- monitorApp_init
# -- monitorApp_getResourceLevel 
# -- monitorApp_status
#------------------------------------------

def monitorApp_init(lxcName):
    global monitorApp_lastTime, monitorApp_lastCPU, monitorApp_lxcName
    monitorApp_lxcName = lxcName

    atTime, curUsage = getCpuTime()
    monitorApp_lastTime, monitorApp_lastCPU = atTime, curUsage 
    print 'Initialized CPU reading (' + str(atTime) + ',' + str(curUsage) + ')'
    return True
#END monitorAppInit


def monitorApp_getResourceLevel():
    global monitorApp_lastTime, monitorApp_lastCPU
    
    prevTime, prevCPU = monitorApp_lastTime, monitorApp_lastCPU
    curTime, curCPU   = getCpuTime()

    timeDiff = curTime - prevTime
    timeDiffInNanosec = ((timeDiff.seconds * 1000000) + timeDiff.microseconds) * 1000
    curPercent = float(curCPU - prevCPU) / timeDiffInNanosec
    #print 'timeDiff = '  + str(timeDiffInNanosec) + ', cur = ' + str(curCPU) + ', prev = ' + str(prevCPU)
    
    monitorApp_lastTime, monitorApp_lastCPU = curTime, curCPU 
    memSize = 0 # TBA    

    return curPercent * 100, memSize 
#END monitorApp_getResourceLevel


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("lxcName", help="Name of the container to be monitored")
    args = parser.parse_args()
    
    monitorApp_init(args.lxcName)
    time.sleep(5)
    
    for i in range(1,5):
        print str(monitorApp_getResourceLevel())
	time.sleep(i)



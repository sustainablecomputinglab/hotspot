#!/usr/bin/python

from datetime import datetime
import os, sys, re, time 
import subprocess
import infraEC2, monitorApp, monitorMarket 

MIN_LOOP_TIME = 5 * 60

def getCurTime():
    return datetime.strptime(confDict['startTime'],"%Y-%m-%dT%H:%M:%S")
# END getCurTime


def startController(confDict):
    # Parse the config dict, and initiate monitorMarket module.
    if confDict['endTime'] > 0:
        curMarketStartTime = confDict['endTime']
    else:
        curMarketStartTime = confDict['startTime']
    
    curMarket = confDict['spotMarket']
    migrFlag = False
    logStr = ''
   
    monitorMarket.setCurInst(curMarket, curMarketStartTime)

    # 2. Start the controller loop
    #    a. Monitor container state. If dormant, exit controller.
    #    b. Monitor market (as per policy) and determine next destination.
    #    c. If migration is not required, sleep until next iteration.
    #    d. If migration required, update confFile and trigger migration.
    while(True):
        loopStartTime = datetime.now()
        cpuUtil, memSize = autoMonitorApp.autoMonitorApp_getResourceLevel()
        logStr += 'HotSpot at ' + str(cpuUtil) + ' %cpu and ' + str(memSize) + '%mem\n'
        if cpuUtil < 1.0:
            logStr += getCurTime() + ': CPU utilization hit ' + str(cpuUtil) + '... Terminating\n'
            break
    
        nextMarket = monitorMarket.findTradeOff(cpuUtil, memSize)
        logStr +=  getCurTime() + ': got <' + str(marketVector) + '> as the best tradeoff\n'
        
        if(nextMarket != curMarket):
            migrFlag = True
            logStr += getCurTime() + ': Triggering migration to ' + nextMarket + '\n'
            break
           
        # If continuing on the same instance, sleep until next timeslot 
        loopTime = (datetime.now() - loopStartTime).seconds
        time.sleep(MIN_LOOP_TIME - loopTime)

    # Done with the controller loop. Update conf file and log file
    with open('/home/ubuntu/hotSpot/log', 'a') as logFp:
        logFp.write(logStr)

    curCost = monitorMarket.findCurInstCost()
    curCost += float(confDict['runCost'])
    confDict['runCost'] = str(curCost)
    confDict['spotMarket'] = curMarket
    confDict['endTime'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with open('/home/ubuntu/hotSpot/config', 'w') as confFp:
        for key, value in confDict.items():
            confFp.write(str(key) + ',' + str(value) + '\n')
    
    # Trigger migration, and terminate self. 
    if migrFlag == True:
        subprocess.call(['/home/ubuntu/scripts/hotSpotCleanup.sh'])
        
        nextMarket = re.sub('\.us-west-1[abcde]', '', nextMarket)
        nextMarket = re.sub('\.vpc', '', nextMarket)
        
        curInstId = infraEC2.infraEC2_getCurInstId()
        migrInstId = infraEC2.infraEC2_acquireInstance(nextMarket, 'us-west-1c', 'on-demand')
        infraEC2.infraEC2_moveEBSandENI('us-west-1c', curInstId, migrInstId)
        infraEC2.infraEC2_deleteInstance('us-west-1c', curInstId)

# END startController


if __name__ == '__main__':
    # Read the config file to get init information
    confDict = dict()
    with open('/home/ubuntu/hotSpot/config') as confFp:
        for line in confFp:
            line = line.rstrip('\n')
            v1, v2 = line.split(',')
            confDict[v1] = v2
    print confDict

    monitorApp.monitorApp_init('hotSpotLXC')
    infraEC2.infraEC2_init('CLOUD', confDict['ebsId'], confDict['eniId'])
    time.sleep(5)
    startController(confDict)
 

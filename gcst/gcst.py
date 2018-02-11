
# RESUME replace all hardcoded nums twd Pane class

# entry point from views.py is fcstgfx

# todo missing vals could vary w/ data array so must copy xs for each ys in order to add droppoints (for straight sides of clip) on each side of each run of missing vals.
# todo remove hi/lo temp if dont have that part of the day
# todo end graph early if data is missing toward the end of the week.
# todo fix nbars==12 but ndivs==11, wh caused "rain12_of_11.png 404 (Not Found)"
# todo swap folded vs unfolded; eg maxTempX should be smaller when folded, not unfolded.
# todo before turning on cacheData: re-getnewdata if too old; remove expired cached data
# todo svg units arent really pixels--change Px to Unit
# interesting https://www.wunderground.com/weather/api/

# glossary
#   eg=such as
#   Dt=Datetime
#   el=element [of xml]

from __future__ import print_function

from datetime import datetime as dt,timedelta
from time import mktime
from itertools import groupby
from collections import defaultdict

from gcst.util import (debug, missing, isOdd, minmax,
        classifyRange, Dataset, dict2obj)
from gcst.dataTypes import scaleData, checkConfig
from gcst.readFcst import getFcstData
from gcst.writeSvg import svgtmpl, computeSvg
from gcst.appinfo import appname, makepath as makeAppPath
from gcst.config import layout as dataObjs

cacheData = False  # see todo's

appcachedir=makeAppPath('cache/%s'%(appname))


# precip intensity
#   accto http://theweatherprediction.com/habyhints2/434/
#     inches per hour: light 0.1 rain 0.3 heavy 
#     whereas drizzle & snow are measured in terms of visibility eg: heavy 1/4mile drizzle 1/2mile light
#   we will try: mist .01 drizzle .03 lightRain .1 rain .3 heavyRain 1 downpour 3 torrent
# I=precip intensity
class I: none, mist, drizzle, lightRain, rain, heavyRain, downpour, torrent = range(8)
def classifyPrecipAmt(amtPerHr):
    if amtPerHr is missing:
        return I.none
    return classifyRange(amtPerHr,[
        (.0001,I.none),
        (.01,  I.mist),
        (.03,  I.drizzle),
        (.1 ,  I.lightRain),
        (.3 ,  I.rain),
        (1 ,   I.heavyRain),
        (3 ,   I.downpour),
        (999,  I.torrent),
        ])
maxPrecipAmt=float(I.torrent)

def fcstgfx(location):
    '''compute html for a group of svg "blocks" [abbreviated 'blk']
        for each 12hour day and night, compute two blocks, folded and unfolded
    '''
    global dataObjs
    dataObjs, npanes = checkConfig(dataObjs)
    data, startTimes, slots = getFcstData(location, cacheData)
    
    if data:
        nightwidthfactor=0.5  # nights are half the width of days [unfolded; folded, they are the same width]
        fullblockwidth=100    # in pixels
        
        startTimeA = startTimes[0]                                              # eg 0700
        midniteA=startTimeA.replace(hour=0, minute=0, second=0, microsecond=0)  # eg 01jan/0000
        hrsSinceMidniteA=int((startTimeA-midniteA).seconds/3600)                # eg 7
        # daytime is from 0600 until 1800; each startidx marks the start of a 1hour interval
        isdaytime0=(6<=hrsSinceMidniteA<18)
        nstarttimes=len(startTimes)
        
        '''compute range of those quantities that need scaling'''
        scaleData(data)
        minTemp, maxTemp, tempRange = data['hourly-temperature-minMaxRange']
        
        '''
            forecast may start at 10pm [22:00], so the first [and last] 12hr block
            of our display will be less than 12hrs wide.  here we group the 
            startTimes array indexes by which 12hr block they fall into.
        '''
        def adjustStartIdx(startidx):
            return classifyRange(startidx,[
                (6,   -6),  # eg 4am is  4 - -6 = 10hrs into its 12hr [nighttime] block
                (18,   6),  # eg 9am is  9 -  6 -  3hrs into its 12hr [daytime] block
                (24,  18),  # eg 9pm is 21 - 18 -  3hrs into its 12hr [nighttime] block
                ])
        floor=adjustStartIdx(hrsSinceMidniteA)
        idxz=[(
            (hour - floor) // 12,     # iblock: index of 12hr block starting at 6:00 (am or pm)
            (hour - floor) % 12,      # ihours: index within 12hr block (ie within a single svg)
            hour - hrsSinceMidniteA   # itimes: index of each hour within startTimes array
            ) for hour in range(hrsSinceMidniteA, hrsSinceMidniteA + nstarttimes)]
        #print(idxz)
        #idxz at  7:00am: [(0, 1, 0), (0, 2, 1), (0, 3, 2), (0, 4, 3), ... (0, 10, 9), (0, 11, 10), <entering new block> (1, 0, 11), (1, 1, 12), (1, 2, 13), ... (13, 11, 166), (14, 0, 167)]
        #idxz at 11:30am: [(0, 5, 0), (0, 6, 1), (0, 7, 2), (0, 8, 3), ... (0, 10, 5), (0, 11, 6), <entering new block> (1, 0, 7), (1, 1, 8), (1, 2, 9), ... (14, 3, 166), (14, 4, 167)]
        indexIter = groupby(idxz, lambda idx:idx[0])
        
        svgs=[]
        xpixelsaccum=0
        for isvg, (k, grp) in enumerate(indexIter):
            iblocks, ihours, itimes=zip(*grp)
            # all iblocks values should be the same [due to groupby] and equal to isvg
            iblock=iblocks[0]
            itime0 = itimes[0]
            itimeEnd = itimes[-1] + 1
            today=startTimes[itime0]
            isdaytime=isOdd(isdaytime0 + iblock)
            blockwidth=fullblockwidth*(len(ihours)/12.)
            if not isdaytime:
                blockwidth*=nightwidthfactor
            '''
                blk means 12hr block
                raw data is read from xml
                prp data is scaled from 0 to 1 ['prp' is proportion]
                svg data is scaled to svg units
            '''
            xdata=dict2obj()
            xdata.raw = list(ihours)  # convert from tuple
            xdata.prp = [
                (ihr-ihours[0])/float(len(ihours)-1) if len(ihours)>1 else .5
                    # [(ihr+0.5)/12 for ...  # this leaves gaps at start,end of block
                    # todo is '.5' reasonable default value for x?
                    # '-1' causes data to jump at start,end of block
                    for ihr in xdata.raw]
            for obj in dataObjs:
                # extract data for this 12hr block
                obj.setRawData(data, itime0, itimeEnd)
            # foldedOrUnfolded is merely initial state of block--block iscompact could be True or False
            foldedOrUnfolded='z' if blockwidth<30 else 'folded0'
            iscompact=False
            svgid='%d%s'%(isvg,foldedOrUnfolded[0])
            blkdatasvg=computeSvg(dataObjs, locals())
            xpixelsaccum+=blockwidth
            svgs.append(svgtmpl % blkdatasvg)
            if blockwidth>=30:  # ie foldedOrUnfolded!='z'
                iscompact=True
                # toggle foldedOrUnfolded state
                foldedOrUnfolded='folded0' if foldedOrUnfolded=='unfolded0' else 'unfolded0'
                svgid='%d%s'%(isvg,foldedOrUnfolded[0])
                blockwidth=svgwidth=25  # smaller for nights?
                blkdatasvg=computeSvg(dataObjs, locals())
                svgs.append(svgtmpl % blkdatasvg)
        slots['svgs'] = ''.join(svgs)
    else:
        # error, received no data from weather.gov
        slots.update(dict(
            svgs=('<h1>Hourly data temporarily unavailable from National Weather Service</h1>'
                  '<h3>"text" link below might work.</h3>'
                  '<h3>Try again soon.</h3>'),
            fcstAsOfDate='',
            fcstAsOfTime='',
            moreWthrInfo='',
            debugTabl='',
        ))

    return slots


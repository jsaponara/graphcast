
# entry point from views.py is fcstgfx

# todo missing vals could vary w/ data array so must copy xs for each ys in order to add droppoints (for straight sides of clip) on each side of each run of missing vals.
# todo remove hi/lo temp if dont have that part of the day
# todo end graph early if data is missing toward the end of the week.
# todo fix nbars==12 but ndivs==11, wh caused "rain12_of_11.png 404 (Not Found)"
# todo swap folded vs unfolded; eg maxTempShift should be smaller when folded, not unfolded.
# todo before turning on cacheData: re-getnewdata if too old; remove expired cached data

# glossary
#   eg=such as
#   Dt=Datetime
#   el=element [of xml]

from __future__ import print_function

from datetime import datetime as dt,timedelta
from time import mktime
from itertools import groupby
from collections import defaultdict

import attr

from gcst.util import debug, missing, Frame, isOdd, minmax, classifyRange
from gcst.readFcst import getFcstData
from gcst.writeSvg import bargraph, coordsToPath, svgtmpl
from gcst.appinfo import appname, makepath as makeAppPath

cacheData = False  # see todo's

appcachedir=makeAppPath('cache/%s'%(appname))

@attr.s
class Dataset(object):
    x = attr.ib(default=attr.Factory(list))
    cloud = attr.ib(default=attr.Factory(list))
    precipChance = attr.ib(default=attr.Factory(list))
    precipAmt = attr.ib(default=attr.Factory(list))
    temp = attr.ib(default=attr.Factory(list))
    weather = attr.ib(default=attr.Factory(list))
    # add wind?


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
    data, startTimes, slots = getFcstData(location, cacheData)

    nightwidthfactor=0.5  # nights are half the width of days [unfolded; folded, they are the same width]
    fullblockwidth=100    # in pixels

    startTimeA = startTimes[0]                                              # eg 0700
    midniteA=startTimeA.replace(hour=0, minute=0, second=0, microsecond=0)  # eg 01jan/0000
    hrsSinceMidniteA=int((startTimeA-midniteA).seconds/3600)                # eg 7
    # daytime is from 0600 until 1800; each startidx marks the start of a 1hour interval
    isdaytime0=(6<=hrsSinceMidniteA<18)
    nstarttimes=len(startTimes)

    '''compute range of quantities that need scaling'''
    minTemp,maxTemp=minmax(data['hourly-temperature'])
    tempRange=maxTemp-float(minTemp)

    '''
        if user requests forecast at 9:10pm [21:10], weather.gov may return a
        forecast that starts at 10pm [22:00], so the first [and last] 12hr block
        of our display will be less than 12hrs wide.  here we group the indexes
        into the startTimes array by which 12hr block they fall into.
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
        if debug: print('len(ihours),blockwidth',len(ihours),blockwidth)
        if not isdaytime:
            blockwidth*=nightwidthfactor
        '''
            blk means 12hr block
            blkdataraw holds arrays of the raw data
            blkdataprop holds arrays of the data
               transformed to a 0-to-1 coordinate space ['prop' is proportion]
            blkdatapixels is arrays of the data
               transformed to the svg [pixel] coordinate space
        '''
        blkdataraw=Dataset(
            x=list(ihours),  # convert from tuple
            # extract data for this 12hr block
            cloud=data['total-cloudamount'][itime0:itimeEnd],
            precipChance=data['floating-probabilityofprecipitation'][itime0:itimeEnd],
            precipAmt=data['floating-hourlyqpf'][itime0:itimeEnd],
            temp=data['hourly-temperature'][itime0:itimeEnd],
            weather=data['weather'][itime0:itimeEnd],
            )
        # pad *clip (as opposed to *path) datasets w/ zero at both ends--these are 'droppoints'
        # bug: data array may end in a run of missing values, so padding w/ zeroes wont result in a vertical drop cuz xs will advance from last number to first missingval.
        blkdataraw.cloud=[0]+blkdataraw.cloud+[0]
        blkdataprop=Dataset(
            # bug? if len(ihours)==1 then divideByZero here; also /tempRange here, divisions elsewhere?
            x=[(ihr-ihours[0])/float(len(ihours)-1) if len(ihours)>1 else .5
                # [(ihr+0.5)/12 for ...  # this leaves gaps at start,end of block
                # todo is '.5' reasonable default value for x?
                # '-1' causes data to jump at start,end of block
                for ihr in blkdataraw.x],
            cloud=[pct if pct is None else pct/100.
                for pct in blkdataraw.cloud],
            precipChance=[pct if pct is None else pct/100.
                for pct in blkdataraw.precipChance],
            precipAmt=[classifyPrecipAmt(amt)/maxPrecipAmt
                for amt in blkdataraw.precipAmt], 
            temp=[temp if temp is None else (temp-minTemp)/tempRange
                for temp in blkdataraw.temp],
            weather=None
            )
        def sumPrecipToString(amts):
            total=sum([y for y in blkdataraw.precipAmt if y is not missing])
            roundedtotal=round(total,1)
            if total>0.0 and roundedtotal==0.0:
                return total,'&lt;0.1'
            else:
                return total,str(roundedtotal)
        minTempBlock,maxTempBlock=minmax(blkdataraw.temp)
        # foldedOrUnfolded is merely initial state of block--block iscompact could be True or False
        foldedOrUnfolded='z' if blockwidth<30 else 'folded0'
        iscompact=False
        svgid='%d%s'%(isvg,foldedOrUnfolded[0])
        def computeSvg(**d):
            blockwidth=d['blockwidth']
            isvg=d['isvg']
            isdaytime=d['isdaytime']
            nightwidthfactor=d['nightwidthfactor']
            # len of blkdataraw: >0 means at least 1hr of data; >8 means data goes to at least 2pm
            knowMinTemp=(isvg> 0 or len(d['blkdataraw'].x)==12)
            knowMaxTemp=(isvg<14 or len(d['blkdataraw'].x)>8)
            minTempBlock=str(d['minTempBlock'])+r'&deg;' if d['minTempBlock'] and knowMinTemp else ''
            maxTempBlock=str(d['maxTempBlock'])+r'&deg;' if d['maxTempBlock'] and knowMaxTemp else ''
            blkdataraw=d['blkdataraw']
            foldedOrUnfolded=d['foldedOrUnfolded']
            if debug: print('blockwidth,isdaytime,foldedorun',blockwidth,isdaytime,foldedOrUnfolded)
            width,height=blockwidth,33.33 # 100x100 box w/ 3 frames, each 100x33.33px
            toppane,midpane,btmpane=(0,1,2)
            blkdatapixels=Dataset(
                x=[width*x for x in blkdataprop.x],
                cloud=[toppane*height+height*(1-y) for y in blkdataprop.cloud],
                precipChance=[midpane*height+height*(1-y) for y in blkdataprop.precipChance],
                precipAmt=[midpane*height+height*(1-y) for y in blkdataprop.precipAmt],
                temp=[btmpane*height+height*(1-y) for y in blkdataprop.temp],
                weather=None
                )
            #weathertips=[' &amp; '.join(types) for types,probs,prob in blkdataraw.weather]
            weathertips=[types for types,probs,prob in blkdataraw.weather]
            midframe=Frame(x=0,y=midpane*height,width=width,height=height)
            #print(blkdataprop.x)
            #print(blkdataprop.precipAmt)
            svgid='%d%s'%(isvg,foldedOrUnfolded[0])
            totalprecip,totalprecipAsStr=sumPrecipToString(blkdataraw.precipAmt)
            maxPrecipChance=max(blkdataraw.precipChance)
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none'
            magfactor=2.5
            blkdatasvg=dict(
                svgid=svgid,
                minTemp=minTempBlock,
                maxTemp=maxTempBlock,
                preciptot=totalprecipAsStr,
                precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
                preciptextcolor=preciptextcolor,
                precipamt=bargraph(midframe,blkdataprop.x,blkdataprop.precipAmt,weathertips,svgid=svgid),
                cloudclip=coordsToPath(blkdatapixels.x,blkdatapixels.cloud,closePath=True),
                precipclip=coordsToPath(blkdatapixels.x,blkdatapixels.precipChance),
                temppath=coordsToPath(blkdatapixels.x,blkdatapixels.temp),
                sunormoon='sun' if isdaytime else 'moon',
                vboxwidth=blockwidth,
                blockwidth=blockwidth,
                svgwidth=magfactor*blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
                svgheight=magfactor*100,
                dayofweekcolor='black' if isdaytime else 'none',
                dateofmonthcolor='black' if isdaytime else 'none',
                #title=today.strftime('%a %d%b'),
                dayofweek=today.strftime('%a'),
                dateofmonth=today.strftime('%d'),
                # for oclockpath lines (9:00 etc)
                # todo short day mightnt hav all 3 timesofday
                quarterwidth=.25*blockwidth,
                halfwidth=.5*blockwidth,
                threequarterwidth=.75*blockwidth,
                quarterwidthminus=.25*blockwidth-7,
                halfwidthminus=.5*blockwidth-9,
                threequarterwidthminus=.75*blockwidth-7,
                oclockcolor='#ddd' if isdaytime and not iscompact and blockwidth==fullblockwidth else 'none',
                debugInfo='blockwidth==%d fullblockwidth==%d'%(blockwidth,fullblockwidth) if debug else '',
                darkatnight='"#eee"' if not isdaytime else '"none"',
                minTempShift=0,
                maxTempShift=11 if foldedOrUnfolded=='unfolded0' else 60,
                hitempcolor='#c44' if isdaytime else 'none',
                lotempcolor='blue' if isdaytime else 'none',
                cloudtip='%%cloudiness: %s'%(str(blkdataraw.cloud[1:-1])),
                #preciptip='precipChance(%%): %s'%(str(blkdataraw.precipChance)),
                preciptip='precipAmt(in): %s'%(list(zip(blkdataraw.x,blkdataraw.precipAmt,weathertips))),
                temptip='temp(F): %s'%(str(blkdataraw.temp)),
                blockx=xpixelsaccum,
                iblock=iblock,
                nightorday='day' if isdaytime else 'night',
                foldedOrUnfolded=foldedOrUnfolded,
                )
            #print(today,blkdatasvg['nightorday'],foldedOrUnfolded,blkdatasvg['oclockcolor'])
            return blkdatasvg
        blkdatasvg=computeSvg(**locals())
        #print(blkdatasvg['precipamt'])
        xpixelsaccum+=blockwidth
        svgs.append(svgtmpl % blkdatasvg)
        if blockwidth>=30:  # ie foldedOrUnfolded!='z'
            iscompact=True
            # toggle foldedOrUnfolded state
            foldedOrUnfolded='folded0' if foldedOrUnfolded=='unfolded0' else 'unfolded0'
            svgid='%d%s'%(isvg,foldedOrUnfolded[0])
            blockwidth=svgwidth=25  # smaller for nights?
            #oclockcolor='#ddd' if isdaytime and not iscompact else 'none'
            oclockcolor='none'
            blkdatasvg=computeSvg(**locals())
            svgs.append(svgtmpl % blkdatasvg)
    slots['svgs'] = ''.join(svgs)
    #svgswidth=xpixelsaccum

    return slots


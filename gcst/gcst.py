
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

from gcst.util import debug, Frame, missing, isOdd, minmax, classifyRange, Dataset
from gcst.util import toppane,midpane,btmpane
from gcst.readFcst import getFcstData
from gcst.writeSvg import bargraph, coordsToPath, svgtmpl, computeSvg
from gcst.appinfo import appname, makepath as makeAppPath

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

class Temp(object):
    def __init__(self, pane):
        self.pane = pane
        self.reset()
    def reset(self):
        self.svgtmpl='''
            <path fill='none' stroke-width=3 stroke="#faa" title='%(temptip)s' d='%(temppath)s' />
            <desc> text of temperature </desc>
            <text x=%(minTempShift)d y=95 font-size=10 fill="%(lotempcolor)s">%(minTemp)s</text>
            <text x=%(maxTempShift)d y=80 font-size=10 fill="%(hitempcolor)s">%(maxTemp)s</text>'''
    def text(self, inn, out):
        self.reset()
        print('=====svgtmpl',self.svgtmpl)
        isvg=inn['isvg']
        blkdataraw=inn['blkdataraw']
        isdaytime=inn['isdaytime']
        foldedOrUnfolded=inn['foldedOrUnfolded']
        temptip='temp(F): %s'%(str(blkdataraw.temp))
        temppath='%(temppath)s'
        knowMinTemp=(isvg> 0 or len(blkdataraw.x)==12)
        knowMaxTemp=(isvg<14 or len(blkdataraw.x)>8)
        minTempBlock,maxTempBlock=minmax(blkdataraw.temp)
        minTemp=str(minTempBlock)+r'&deg;' if minTempBlock and knowMinTemp else ''
        print('minTemp,minTempBlock,knowMinTemp,isvg,len(blkdataraw.x)',minTemp,minTempBlock,knowMinTemp,isvg,len(blkdataraw.x))
        maxTemp=str(maxTempBlock)+r'&deg;' if maxTempBlock and knowMaxTemp else ''
        minTempShift=0
        maxTempShift=11 if foldedOrUnfolded=='unfolded0' else 60
        hitempcolor='#c44' if isdaytime else 'none'
        lotempcolor='blue' if isdaytime else 'none'
        self.svgtmpl=self.svgtmpl % vars()
        out.update(dict(
        ))
        return out
    def pathData(self, d, dataset, height):
        blkdataprop=d['blkdataprop']
        dataset.temp = [self.pane*height+height*(1-y) for y in blkdataprop.temp]
    def svgPath(self, dataset, svgDict):
        temppath=coordsToPath(dataset.x,dataset.temp)
        svgDict.update(dict(
            temptext=self.svgtmpl % vars()
        ))
        print(svgDict['temptext'])
    def svgGraph(self, dataset, svgDict, height, width, svgid):
        pass
class Clouds(object):
    def __init__(self, pane):
        self.pane = pane
    def reset(self):
        pass
    def text(self, inn, out):  # todo passthru could be inherited
        blkdataraw=inn['blkdataraw']
        out.update(dict(
            cloudtip='%%cloudiness: %s'%(str(blkdataraw.cloud[1:-1])),
        ))
        return out
    def pathData(self, d, dataset, height):
        blkdataprop=d['blkdataprop']
        dataset.cloud=[self.pane*height+height*(1-y) for y in blkdataprop.cloud]
    def svgPath(self, dataset, svgDict):
        svgDict.update(dict(
            cloudclip=coordsToPath(dataset.x,dataset.cloud,closePath=True)
        ))
    def svgGraph(self, dataset, svgDict, height, width, svgid):
        pass
class Precip(object):
    def __init__(self, pane):
        self.pane = pane
    def reset(self):
        pass
    def text(self, inn, out):  # todo passthru could be inherited
        blkdataraw=inn['blkdataraw']
        blkdataprop=inn['blkdataprop']
        totalprecip,totalprecipAsStr=self.sumPrecipToString(blkdataraw.precipAmt)
        maxPrecipChance=max(blkdataraw.precipChance)
        out.update(dict(
            preciptot=totalprecipAsStr,
            precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            #preciptip='precipChance(%%): %s'%(str(blkdataraw.precipChance)),
            preciptip='precipAmt(in): %s'%(list(zip(blkdataraw.x,blkdataraw.precipAmt,blkdataprop.weather))),
        ))
        return out
    def pathData(self, d, dataset, height):
        blkdataprop=d['blkdataprop']
        dataset.precipChance=[self.pane*height+height*(1-y) for y in blkdataprop.precipChance]
        dataset.precipAmt=[self.pane*height+height*(1-y) for y in blkdataprop.precipAmt]
    def svgPath(self, dataset, svgDict):
        svgDict.update(dict(
            precipclip=coordsToPath(dataset.x,dataset.precipChance),
        ))
    def svgGraph(self, dataset, svgDict, height, width, svgid):
        midframe=Frame(x=0,y=self.pane*height,width=width,height=height)
        svgDict.update(dict(
            precipamt=bargraph(midframe,dataset.x,dataset.precipAmt,dataset.weather,svgid=svgid),
        ))
    def sumPrecipToString(self, amts):
        total=sum([y for y in amts if y is not missing])
        roundedtotal=round(total,1)
        if total>0.0 and roundedtotal==0.0:
            return total,'&lt;0.1'
        else:
            return total,str(roundedtotal)


temp=Temp(midpane)
cloud=Clouds(toppane)
precip=Precip(midpane)
dataObjs=[temp, cloud, precip]

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
        for obj in dataObjs:
            obj.reset()
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
            weather=[types
                for types,probs,prob in blkdataraw.weather]  # weathertips
            )
        # foldedOrUnfolded is merely initial state of block--block iscompact could be True or False
        foldedOrUnfolded='z' if blockwidth<30 else 'folded0'
        iscompact=False
        svgid='%d%s'%(isvg,foldedOrUnfolded[0])
        blkdatasvg=computeSvg(dataObjs, locals())
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
            blkdatasvg=computeSvg(dataObjs, locals())
            svgs.append(svgtmpl % blkdatasvg)
    slots['svgs'] = ''.join(svgs)
    #svgswidth=xpixelsaccum

    return slots


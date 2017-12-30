
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

import re
from datetime import datetime as dt,timedelta
from time import mktime
from itertools import groupby
from collections import defaultdict

import attr

from gcst.util import missing, Frame, isOdd, minmax, classifyRange
from gcst.readFcst import getFcstData
from gcst.writeSvg import bargraph, coordsToPath
from gcst.appinfo import appname, makepath as makeAppPath

cacheData = False  # see todo's
debug=False

appcachedir=makeAppPath('cache/%s'%(appname))

# svg template for a single 12hr block
#    template has slots for: cloudclip precipclip precippct precipamt temppath templo temphi
#    where cloud=cloudiness, precip=precipitation, temp=temperature
#    and *clip is just points [pairs of ints] defining a polygon,
#    and *path is M x y L x y x y...  [M=moveto, L=lineto]
# foldedOrUnfolded: blocks can be full size [unfolded] or compact [folded] or marginal ['z']
#    marginal blocks dont respond to user clicks,
#    whereas other blocks toggle between folded and unfolded when clicked.
# todo accept text positions and maybe sizes as well
# odd: why doesnt rect work for background color?  instead it covers everything no matter if it's first or last
#      eg: more cross-browser solution currently would be to stick a <rect> element with width and height of 100% and fill="red" as the first child of the <svg> element  http://stackoverflow.com/questions/11293026/default-background-color-of-svg-root-element
#      <rect width=40%% height=40%% style="fill:#36a3e4">
#      instead using path
svgtmpl='''
    <svg id='%(iblock)d' class='%(nightorday)s %(foldedOrUnfolded)s' width=%(svgwidth)d height=%(svgheight)d viewBox="0 0 %(blockwidth)d 100" preserveAspectRatio="none">
        <desc>background color</desc>
        <path d='M %(halfwidth).0f 0 L %(halfwidth).0f 100 '
            fill='none' stroke-width=%(svgwidth)d stroke=%(darkatnight)s/>
        <desc> time of day lines at 9:00,12:00,3:00; draw oclockpath lines down only to 90ish to leave room for oclock times (9:00 etc) </desc>
        <path d='M %(quarterwidth).1f 0 L %(quarterwidth).1f 94  M %(halfwidth).1f 0 L %(halfwidth).1f 94  M %(threequarterwidth).1f 0 L %(threequarterwidth).1f 94'
            fill='none' stroke-width=1 stroke="%(oclockcolor)s"/>
        <desc> ---- top pane: bkgd of clear sky, clipped at start and end of fcst time range </desc>
        <image xlink:href="/static/gcst/img/%(sunormoon)s.png" 
            x=0 y=0 width=100 height=33 />
        <desc> top: foregd of clouds, clipped accto data </desc>
        <clipPath id="pctclouds%(svgid)s" >
            <path d="%(cloudclip)s"/>
            </clipPath>
        <image xlink:href="/static/gcst/img/%(sunormoon)sclouds.png" title='%(cloudtip)s' 
            x=0 y=0 width=100 height=33 clip-path="url(#pctclouds%(svgid)s)" />
        <desc> day and date (must come after sunormoon etc to avoid being hidden) </desc>
        <text x=3.3 y=10 font-size=12 fill="%(dayofweekcolor)s">%(dayofweek)s</text>
        <text x=6.8 y=20 font-size=12 fill="%(dateofmonthcolor)s">%(dateofmonth)s</text>
        <desc> ---- middle pane: foregd of rain, clipped accto data </desc>
        <path d="%(precipclip)s" title='%(preciptip)s' stroke='#aaa' stroke-width=3 fill='none' />
        <desc> mid: rain text </desc>
        <text x=4 y=50 font-size=10 fill="%(preciptextcolor)s">%(precippct)s%%</text>
        <text x=4 y=64 font-size=10 fill="%(preciptextcolor)s">%(preciptot)s"</text>
        <path d="M 0 67 L %(svgwidth)d 67" stroke='#444' stroke-width=1 fill='none' />
        <desc> ---- bottom pane: foregd of temperature, graphed accto data </desc>
        <path fill='none' stroke-width=3 stroke="#faa" title='%(temptip)s' d='%(temppath)s' />
        <desc> text of temperature </desc>
        <text x=%(minTempShift)d y=95 font-size=10 fill="%(lotempcolor)s">%(minTemp)s</text>
        <text x=%(maxTempShift)d y=80 font-size=10 fill="%(hitempcolor)s">%(maxTemp)s</text>
        <desc> text for oclock lines </desc>
        <g font-size=6 fill="%(oclockcolor)s">
            <text y=99 x=%(quarterwidthminus)d >9:00</text>
            <text y=99 x=%(halfwidthminus)d>12:00</text>
            <text y=99 x=%(threequarterwidthminus)d>3:00</text>
            <text x=78 y=6 >clouds</text>
            <text x=78 y=39 >storms</text>
            <text x=78 y=72 >temps</text>
            <line x1=0 y1=67 x2=100 y2=67 />
        </g>
        <desc>%(debugInfo)s</desc>
    </svg>
'''.strip()
if not debug:
    svgtmpl=re.sub(r'<desc>.*?<\/desc>\s*','',svgtmpl)

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
        def precipTotToString(amts):
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
            blkdatapixels=Dataset(
                x=[width*x for x in blkdataprop.x],
                cloud=[0+height*(1-y) for y in blkdataprop.cloud],
                precipChance=[height+height*(1-y) for y in blkdataprop.precipChance],
                precipAmt=[height+height*(1-y) for y in blkdataprop.precipAmt],
                temp=[2*height+height*(1-y) for y in blkdataprop.temp],
                weather=None
                )
            #weathertips=[' &amp; '.join(types) for types,probs,prob in blkdataraw.weather]
            weathertips=[types for types,probs,prob in blkdataraw.weather]
            toppane,midpane,btmpane=(0,1,2)
            midframe=Frame(x=0,y=midpane*height,width=width,height=height)
            #print(blkdataprop.x)
            #print(blkdataprop.precipAmt)
            svgid='%d%s'%(isvg,foldedOrUnfolded[0])
            totalprecip,totalprecipAsStr=precipTotToString(blkdataraw.precipAmt)
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
            svgs.append(svgtmpl%blkdatasvg)
    slots['svgs'] = ''.join(svgs)
    #svgswidth=xpixelsaccum

    return slots


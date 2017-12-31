
import re
from itertools import count, groupby

from gcst.util import minmax, missing, Frame, UnitFrame, debug, Dataset

ndivs=11

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

def makepath(xys,frame=None,closePath=False):
    if frame:
        xform=frame
    else:
        xform=UnitFrame()
    pathCloser=' z' if closePath else ''
    x,y=next(xys)
    x,y=xform(x,y)
    path0='M %f %f '%(round(x,1),round(y,1))
    path1='  '.join(
        ' '.join((
            str(round(xform.xtransform(x),1)),
            str(round(xform.ytransform(y),1))
            )) for x,y in xys)
    if path1:
        path=path0+'L '+path1+pathCloser
    else:
        path=None  # todo somehow mark the single point we M'd to in path0
    return path

def bargraph(frame,xs,ys,tipsz,ndivs=ndivs,**kwargs):
    locals().update(kwargs)
    if len(ys)==2+len(xs):
        ys=ys[1:-1]
    dx=xs[1]-xs[0] if len(xs)>1 else 1. # todo assuming gaps are all equal
    bars=[]
    #for x,y,tip in zip(xs,ys,tips):
    for key,grp in groupby(zip(count(),xs,ys,tipsz),lambda ixyt:(ixyt[2],ixyt[3])):
        #print(333,key,list(grp))
        i0,x0,y,tips=next(grp)
        theRest=list(grp)
        if theRest:
            iN,xN,yN,tipsN=theRest[-1]
            xN+=dx
        else:
            iN=i0
            xN=x0+dx
        path=makepath(iter(((x0,0),(x0,y),(xN,y),(xN,0))),frame,closePath=True)
        #x=x0
        #x0,y0=frame(x,0)
        #upperleft='x=%f y=%f '%(round(x0,1),round(y0,1))
        #x1,y1=frame(x+dx,0)
        #dims='width=%f height=%f '%(round(x1-x0,1),round(y1-y0,1))
        #bars.append('<rect '+upperleft+dims+"title='"+str(tip)+"' fill='none' stroke='black' stroke-width=1 />")
        #bars.append('<image xlink:href="rain.png" '+upperleft+dims+"title='"+str(tip)+"' />")
        top=frame.y
        nbars=1+iN-i0
        if nbars>ndivs:
            nbars=ndivs
        weatherImgs='rain snow'.split()
        for tip in tips:
            if tip in weatherImgs:
                img=tip
                break
        else:
            img='rain'
        tip=' &amp; '.join(tips)
        frx0=frame.xtransform(x0)
        # 100 rather than frame.width because the imgs were gen'd (in chopimg.py) at width=100
        #   using a different value (eg for night blocks whose width==25) causes strange effects as svg tries to maintain constant aspectratio
        #   but 25-px-wide blocks will now have same problem as 100px blocks did--the imgs will overflow the bar and obscure adjacent bars (eg rain will obscure snow)
        #bargrpwidth=nbars*dx*frame.width
        bargrpwidth=nbars*(100/float(ndivs))
        bars.append('''
            <clipPath id="precip%(svgid)s%(i0)d" >
            <path d="%(path)s" /> </clipPath>
            <image title="%(tip)s" xlink:href="/static/gcst/img/%(img)s%(nbars)d_of_%(ndivs)d.png" x=%(frx0).1f y=%(top).1f width=%(bargrpwidth).1f height=33 clip-path="url(#precip%(svgid)s%(i0)d)" />\n'''.strip()%locals())
    #from pprint import pprint as pp; pp(bars)
    return '\n\t\t'.join(bars)

def coordsToPath(xs,ys,closePath=False):
    # interleave and round x,y coords and convert to string
    pathSegs=[]
    if len(ys)==2+len(xs):
        # pad xs to match *clip (as opposed to *path) datasets w/ zero at both ends
        xs=[xs[0]]+xs+[xs[-1]]
        closePath=True
    for haveData,grp in groupby(zip(xs,ys),lambda x:x[1] is not missing):
        path=''
        pathCloser=' z' if closePath else ''
        if haveData:
            path1=makepath(grp,closePath=closePath)
            if path1:
                pathSegs.append(path1)
        else:
            pass # todo also return path around the missing data segments (ie not haveData) for clipping out the eg sky bkgd
    return '  '.join(pathSegs)

def sumPrecipToString(amts):
    total=sum([y for y in amts if y is not missing])
    roundedtotal=round(total,1)
    if total>0.0 and roundedtotal==0.0:
        return total,'&lt;0.1'
    else:
        return total,str(roundedtotal)

class Temp(object):
    def __init__(self, pane):
        self.pane = pane
    def text(self, inn, out):
        d=inn
        isvg=d['isvg']
        blkdataraw=d['blkdataraw']
        knowMinTemp=(isvg> 0 or len(blkdataraw.x)==12)
        knowMaxTemp=(isvg<14 or len(blkdataraw.x)>8)
        minTempBlock,maxTempBlock=minmax(blkdataraw.temp)
        out.update(dict(
            minTemp=str(minTempBlock)+r'&deg;' if minTempBlock and knowMinTemp else '',
            maxTemp=str(maxTempBlock)+r'&deg;' if maxTempBlock and knowMaxTemp else '',
        ))
        return out
    def pathData(self, d, dataset, height):
        blkdataprop=d['blkdataprop']
        dataset.temp = [self.pane*height+height*(1-y) for y in blkdataprop.temp]
    def svgPath(self, dataset):
        return coordsToPath(dataset.x,dataset.temp)

toppane,midpane,btmpane=(0,1,2)
temp=Temp(btmpane)

def computeSvg(**d):
    blockwidth=d['blockwidth']
    isvg=d['isvg']
    iblock=d['iblock']
    isdaytime=d['isdaytime']
    today=d['today']
    nightwidthfactor=d['nightwidthfactor']
    iscompact=d['iscompact']
    fullblockwidth=d['fullblockwidth']
    xpixelsaccum=d['xpixelsaccum']
    # len of blkdataraw: >0 means at least 1hr of data; >8 means data goes to at least 2pm
    dataDict = temp.text(d, {})
    blkdataraw=d['blkdataraw']
    blkdataprop=d['blkdataprop']
    foldedOrUnfolded=d['foldedOrUnfolded']
    if debug: print('blockwidth,isdaytime,foldedorun',blockwidth,isdaytime,foldedOrUnfolded)
    width,height=blockwidth,33.33 # 100x100 box w/ 3 frames, each 100x33.33px
    blkdatapixels=Dataset(
        x=[width*x for x in blkdataprop.x],
        cloud=[toppane*height+height*(1-y) for y in blkdataprop.cloud],
        precipChance=[midpane*height+height*(1-y) for y in blkdataprop.precipChance],
        precipAmt=[midpane*height+height*(1-y) for y in blkdataprop.precipAmt],
        weather=None
        )
    temp.pathData(d, blkdatapixels, height)
    #weathertips=[' &amp; '.join(types) for types,probs,prob in blkdataraw.weather]
    weathertips=[types for types,probs,prob in blkdataraw.weather]
    midframe=Frame(x=0,y=midpane*height,width=width,height=height)
    svgid='%d%s'%(isvg,foldedOrUnfolded[0])
    totalprecip,totalprecipAsStr=sumPrecipToString(blkdataraw.precipAmt)
    maxPrecipChance=max(blkdataraw.precipChance)
    preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none'
    magfactor=2.5
    blkdatasvg=dict(
        svgid=svgid,
        preciptot=totalprecipAsStr,
        precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
        preciptextcolor=preciptextcolor,
        precipamt=bargraph(midframe,blkdataprop.x,blkdataprop.precipAmt,weathertips,svgid=svgid),
        cloudclip=coordsToPath(blkdatapixels.x,blkdatapixels.cloud,closePath=True),
        precipclip=coordsToPath(blkdatapixels.x,blkdatapixels.precipChance),
    # N#EXT this shudnt need to know about temp!  see update(dataDict) below
        temppath=temp.svgPath(blkdatapixels),
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
        # todo short day might not have all 3 timesofday
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
    blkdatasvg.update(dataDict)
    #print(today,blkdatasvg['nightorday'],foldedOrUnfolded,blkdatasvg['oclockcolor'])
    return blkdatasvg

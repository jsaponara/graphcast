
import re
from itertools import count, groupby

from gcst.util import missing, Frame, UnitFrame, debug
from gcst.util import dict2obj

# svg template for a single 12hr block
#    template has slots for: cloudSvg precipSvg tempSvg
#    where cloud=cloudiness, precip=precipitation, temp=temperature
# data object files have the svg templates for the individual data objects: Temp Clouds Precip
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
    <svg id='%(iblock)d' class='%(nightorday)s %(foldedOrUnfolded)s' width=%(svgwidth)d height=%(svgheight)d viewBox="0 0 %(blockwidth)d %(blockheight)d" preserveAspectRatio="none">
        <desc>background color</desc>
        <path d='M %(halfwidth).0f 0 L %(halfwidth).0f 100 '
            fill='none' stroke-width=%(svgwidth)d stroke=%(darkatnight)s/>
        <desc> time of day lines at 9:00,12:00,3:00; draw oclockpath lines down only to 90ish to leave room for oclock times (9:00 etc) </desc>
        <path d='M %(quarterwidth).1f 0 L %(quarterwidth).1f 94  M %(halfwidth).1f 0 L %(halfwidth).1f 94  M %(threequarterwidth).1f 0 L %(threequarterwidth).1f 94'
            fill='none' stroke-width=1 stroke="%(oclockcolor)s"/>
        <path d="M 0 67 L %(svgwidth)d 67" stroke='#444' stroke-width=1 fill='none' />
        %(dataBlocks)s
        <g font-size=6 fill="%(oclockcolor)s">
            <desc> text for oclock lines </desc>
            <text y=99 x=%(quarterwidthminus)d >9:00</text>
            <text y=99 x=%(halfwidthminus)d>12:00</text>
            <text y=99 x=%(threequarterwidthminus)d>3:00</text>
            <desc> separator </desc>
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

def bargraph(frame,xs,ys,tipsz,**kwargs):
    ndivs=11
    locals().update(kwargs)
    if len(ys)==2+len(xs):
        ys=ys[1:-1]
    dx=xs[1]-xs[0] if len(xs)>1 else 1. # todo assuming gaps are all equal
    bars=[]
    #for x,y,tip in zip(xs,ys,tips):
    for key,grp in groupby(zip(count(),xs,ys,tipsz),lambda ixyt:(ixyt[2],ixyt[3])):
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

def computeSvg(dataObjs, dic):
    magfactor=2.5
    #dic['magfactor']=magfactor
    d=dict2obj(dic)
    d.update(dict(
        magfactor=magfactor,
    ))
    # len of blkdataraw: >0 means at least 1hr of data; >8 means data goes to at least 2pm
    if debug: print('blockwidth,isdaytime,foldedorun',d.blockwidth,d.isdaytime,d.foldedOrUnfolded)
    d.blockheight = d.npanes * 33.33
    d.width,d.height=d.blockwidth,33.33 # 100x100 box w/ 3 frames, each 100x33.33px
    d.xdata.svg = [d.width * x for x in d.xdata.prp]
    d.svgid='%d%s'%(d.isvg,d.foldedOrUnfolded[0])
    blkdatasvg=dict(
        svgid=d.svgid,
        vboxwidth=d.blockwidth,
        blockwidth=d.blockwidth,
        blockheight=d.blockheight,
        svgwidth=magfactor*d.blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
        svgheight=magfactor*d.blockheight,
        #title=today.strftime('%a %d%b'),
        # for oclockpath lines (9:00 etc)
        # todo short day might not have all 3 timesofday
        quarterwidth=.25*d.blockwidth,
        halfwidth=.5*d.blockwidth,
        threequarterwidth=.75*d.blockwidth,
        quarterwidthminus=.25*d.blockwidth-7,
        halfwidthminus=.5*d.blockwidth-9,
        threequarterwidthminus=.75*d.blockwidth-7,
        oclockcolor='#ddd' if d.isdaytime and not d.iscompact and d.blockwidth==d.fullblockwidth else 'none',
        debugInfo='blockwidth==%d fullblockwidth==%d'%(d.blockwidth,d.fullblockwidth) if debug else '',
        darkatnight='"#eee"' if not d.isdaytime else '"none"',
        blockx=d.xpixelsaccum,
        iblock=d.iblock,
        nightorday='day' if d.isdaytime else 'night',
        foldedOrUnfolded=d.foldedOrUnfolded,
        dataBlocks = '\n'.join(obj.renderBlock(d) for obj in dataObjs)
        )
    return blkdatasvg


from itertools import count, groupby
from gcst.util import missing, UnitFrame

ndivs=11

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

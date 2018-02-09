
from gcst.util import debug, Frame, missing, minmax, Dataset
from gcst.writeSvg import bargraph, coordsToPath

# general properties
isvgA = 0
isvgZ = 14
nHrsInFullBlock = 12
paneDescXProp = .78
paneDescYOffPx = 6
bigFontSize = 10
smallFontSize = 6
blockWdPx = 100
blockHtPx = 33

# temp properties
minHrsToKnowMaxTemp = 9
minTempXPx=0
maxTempFoldXPx=11
maxTempUnfoXPx=60
hiTempTextColor = '#c44'
loTempTextColor = 'blue'
minTempYOffPx = 28
maxTempYOffPx = 13

# precip properties
precippctX = 4

class Block(object):
    def __init__(self, blockData):
        self.__dict__.update(blockData.__dict__)
    def paneDescColor(self):
        d=self
        return '#bbb' if (
            d.isdaytime and not d.iscompact and d.blockwidth==d.fullblockwidth) else 'none'

class Layer(object):
    def process(obj, d):
        obj.initBlock(d)
        obj.text()
        obj.pathData()
        obj.svgPath()
        obj.svgGraph()
    def renderBlock(self, blockData):
        self.process(blockData)
        return self.svgtmpl % self.vars

class OpaqueLayer(Layer):
    isOpaque = True
class TransparentLayer(Layer):
    isOpaque = False

class Temp(TransparentLayer):
    def __init__(self, pane):
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <desc> path and min, max, and description text of temperature </desc>
            <path fill='none' stroke-width=3 stroke="#faa" title='%(temptip)s' d='%(temppath)s' />
            <text x=%(minTempX)d y=%(minTempY)s font-size=%(bigFontSize)s fill="%(lotempcolor)s">%(minTemp)s</text>
            <text x=%(maxTempX)d y=%(maxTempY)s font-size=%(bigFontSize)s fill="%(hitempcolor)s">%(maxTemp)s</text>
            <text x=%(paneDescX)s y=%(paneDescY)s font-size=%(smallFontSize)s fill="%(paneDescColor)s">temps</text>
        '''
    def initBlock(self, inn):
        self.block=Block(inn)
    def text(self):
        d=self.block
        minTempBlock,maxTempBlock=minmax(d.blkdataraw.temp)
        knowMinTemp=(d.isvg > isvgA or len(d.blkdataraw.x) == nHrsInFullBlock)
        knowMaxTemp=(d.isvg < isvgZ or len(d.blkdataraw.x) >= minHrsToKnowMaxTemp)
        self.vars.update(dict(
            temptip='temp(F): %s'%(str(d.blkdataraw.temp)),
            temppath='%(temppath)s',
            minTempY='%(minTempY)s',
            maxTempY='%(maxTempY)s',
            minTemp=str(minTempBlock)+r'&deg;' if minTempBlock and knowMinTemp else '',
            maxTemp=str(maxTempBlock)+r'&deg;' if maxTempBlock and knowMaxTemp else '',
            minTempX=minTempXPx,
            maxTempX=maxTempFoldXPx if d.foldedOrUnfolded=='unfolded0' else maxTempUnfoXPx,
            hitempcolor=hiTempTextColor if d.isdaytime else 'none',
            lotempcolor=loTempTextColor if d.isdaytime else 'none',
            bigFontSize=bigFontSize,
            smallFontSize=smallFontSize,
        ))
    def pathData(self):
        d=self.block
        d.blkdatapixels.temp = [self.pane*d.height+d.height*(1-y) for y in d.blkdataprop.temp]
    def svgPath(self):
        d=self.block
        dataset=d.blkdatapixels
        self.vars.update(dict(
            temppath=coordsToPath(dataset.x,dataset.temp)
        ))
    def svgGraph(self):
        d=self.block
        self.vars.update(dict(
            minTempY = str(self.pane * d.height + minTempYOffPx),
            maxTempY = str(self.pane * d.height + maxTempYOffPx),
            paneDescY=self.pane*d.height+paneDescYOffPx,
            paneDescX=paneDescXProp*d.blockwidth,
            paneDescColor=self.block.paneDescColor(),
        ))

class DayDate(TransparentLayer):
    def __init__(self, pane):
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <text x=3.3 y=%(dayofweekY)d font-size=12 fill="%(dayofweekcolor)s">%(dayofweek)s</text>
            <text x=6.8 y=%(dateofmonthY)d font-size=12 fill="%(dateofmonthcolor)s">%(dateofmonth)s</text>
        '''
    def initBlock(self, inn):
        self.block=Block(inn)
    def text(self):
        d=self.block
        self.vars.update(dict(
            svgid=d.svgid,
            dayofweek = d.dayofweek,
            dayofweekcolor = d.dayofweekcolor,
            dayofweekY = 10 + blockHtPx * self.pane,
            dateofmonth = d.dateofmonth,
            dateofmonthcolor = d.dateofmonthcolor,
            dateofmonthY = 20 + blockHtPx * self.pane,
        ))
    def pathData(self):
        pass
    def svgPath(self):
        pass
    def svgGraph(self):
        pass

class Clouds(OpaqueLayer):
    def __init__(self, pane):
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <desc> ---- top pane: bkgd of clear sky, clipped at start and end of fcst time range </desc>
            <image xlink:href="/static/gcst/img/%(sunormoon)s.png" 
                x=%(cloudBkgdX)d y=%(cloudBkgdY)d width=%(blockWdPx)d height=%(blockHtPx)d />
            <desc> top: foregd of clouds, clipped accto data </desc>
            <clipPath id="pctclouds%(svgid)s%(paneid)d" >
                <path d="%(cloudclip)s"/>
                </clipPath>
            <image xlink:href="/static/gcst/img/%(sunormoon)sclouds.png" title='%(cloudtip)s' 
                x=%(cloudBkgdX)d y=%(cloudBkgdY)d width=%(blockWdPx)d height=%(blockHtPx)d clip-path="url(#pctclouds%(svgid)s%(paneid)d)" />
            <text x=%(paneDescX)s y=%(paneDescY)s font-size=%(smallFontSize)s fill="%(paneDescColor)s">clouds</text>
        '''
    def initBlock(self, inn):
        self.block=Block(inn)
    def text(self):
        d=self.block
        self.vars.update(dict(
            svgid=d.svgid,
            sunormoon='sun' if d.isdaytime else 'moon',
            cloudtip='%%cloudiness: %s'%(str(d.blkdataraw.cloud[1:-1])),
            smallFontSize=smallFontSize,
            cloudBkgdX = 0,
            blockWdPx = blockWdPx,
            blockHtPx = blockHtPx,
            # for day and date text
            dayofweek = d.dayofweek,
            dayofweekcolor = d.dayofweekcolor,
            dayofweekY = 10 + blockHtPx * self.pane,
            dateofmonth = d.dateofmonth,
            dateofmonthcolor = d.dateofmonthcolor,
            dateofmonthY = 20 + blockHtPx * self.pane,
        ))
    def pathData(self):
        d=self.block
        d.blkdatapixels.cloud=[self.pane*d.height+d.height*(1-y) for y in d.blkdataprop.cloud]
    def svgPath(self):
        d=self.block
        self.vars.update(dict(
            cloudclip=coordsToPath(d.blkdatapixels.x,d.blkdatapixels.cloud,closePath=True)
        ))
    def svgGraph(self):
        d=self.block
        self.vars.update(dict(
            cloudBkgdY=self.pane*d.height,
            paneDescY=self.pane*d.height+6,
            paneDescX=.78*d.blockwidth,
            paneDescColor=self.block.paneDescColor(),
            paneid = self.pane,
        ))

class Precip(TransparentLayer):
    def __init__(self, pane):
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <path d="%(precipclip)s" title='%(preciptip)s' stroke='#aaa' stroke-width=3 fill='none' />
            <desc> mid: rain text </desc>
            <text x=%(precippctX)d y=%(precippctY)d font-size=%(bigFontSize)s fill="%(preciptextcolor)s">%(precippct)s%%</text>
            <text x=%(precippctX)d y=%(preciptotY)d font-size=%(bigFontSize)s fill="%(preciptextcolor)s">%(preciptot)s"</text>
            <text x=%(paneDescX)s y=%(paneDescY)s font-size=%(smallFontSize)s fill="%(paneDescColor)s">storms</text>
        '''
    def initBlock(self, inn):
        self.block=Block(inn)
    def text(self):
        d=self.block
        totalprecip,totalprecipAsStr=self.sumPrecipToString(d.blkdataraw.precipAmt)
        maxPrecipChance=max(d.blkdataraw.precipChance)
        self.vars.update(dict(
            svgwidth=d.magfactor*d.blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
            preciptot=totalprecipAsStr,
            precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            #preciptip='precipChance(%%): %s'%(str(d.blkdataraw.precipChance)),
            preciptip='precipAmt(in): %s'%(list(zip(d.blkdataraw.x,d.blkdataraw.precipAmt,d.blkdataprop.weather))),
            bigFontSize=bigFontSize,
            smallFontSize=smallFontSize,
            precippctX = precippctX,
        ))
    def pathData(self):
        d=self.block
        inDataset=d.blkdataprop
        outDataset=d.blkdatapixels
        outDataset.precipChance=[self.pane*d.height+d.height*(1-y) for y in inDataset.precipChance]
        outDataset.precipAmt=[self.pane*d.height+d.height*(1-y) for y in inDataset.precipAmt]
    def svgPath(self):
        d=self.block
        inDataset=d.blkdatapixels
        self.vars.update(dict(
            precipclip=coordsToPath(inDataset.x,inDataset.precipChance),
        ))
    def svgGraph(self):
        d=self.block
        dataset=d.blkdataprop
        frame=Frame(x=0,y=self.pane*d.height,width=d.width,height=d.height)
        self.vars.update(dict(
            precipamt=bargraph(frame,dataset.x,dataset.precipAmt,dataset.weather,svgid=d.svgid),
            precippctY=self.pane*d.height+13,
            preciptotY=self.pane*d.height+21,
            paneDescX=.78*d.blockwidth,
            paneDescY=self.pane*d.height+6,
            paneDescColor=self.block.paneDescColor(),
        ))
    def sumPrecipToString(self, amts):
        total=sum([y for y in amts if y is not missing])
        roundedtotal=round(total,1)
        if total>0.0 and roundedtotal==0.0:
            return total,'&lt;0.1'
        else:
            return total,str(roundedtotal)


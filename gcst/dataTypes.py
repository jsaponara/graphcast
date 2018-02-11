
from gcst.util import debug, Frame, missing, minmax, classifyRange
from gcst.writeSvg import bargraph, coordsToPath

# todo some of these belong in config
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
preciptotX = 4

# todo move into a precip.py?
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

datatypesThatNeedScaling = (
    'temperature',
    'windspeed',
)
def scaleData(data):
    minMaxRange = {}
    for key, dataset in data.items():
        if any(datatype in key for datatype in datatypesThatNeedScaling):
            minn,maxx=minmax(dataset)
            # unlike temperature, for windspeed zero should always be the minimum on the graph
            # careful to not match 'windchill', which is a temperature
            if 'windspeed' in key:
                minn = 0
            if minn is not missing and maxx is not missing:
                dataRange=maxx-float(minn)
                minMaxRange[key + '-minMaxRange'] = minn, maxx, dataRange
                minMaxRange[key + '-canScale'] = minn != maxx
            else:
                minMaxRange[key + '-canScale'] = False
    data.update(minMaxRange)

class Block(object):
    def __init__(self, blockData):
        self.__dict__.update(blockData.__dict__)
    def paneDescColor(self):
        d=self
        return '#bbb' if (
            d.isdaytime and not d.iscompact and d.blockwidth==d.fullblockwidth) else 'none'

class Layer(object):
    def __init__(self, dataD):
        self.dataD = dataD
    def initBlock(self, inn):
        self.block=Block(inn)
    def setRawData(self, data, istart, iend):
        for rawkey, xmlkey in self.dataD.items():
            # eg: self.rawtemp = data['hourly-temperature'][istart:iend]
            # todo make this a read-only view to avoid a copy
            setattr(self, rawkey,  data[xmlkey][istart:iend])
            if data.get(xmlkey + '-canScale'):
                self.min, maxx, self.range = data[xmlkey + '-minMaxRange']
        self.rawToProp()
    def rawToProp(self):
        # adjust raw data and transform to proportion
        # todo move to Qnty [ie out of Text]
        pass
    def prpToSvg(self):
        d=self.block
        for rawkey in self.dataD:
            # todo replace with isNumeric[data[rawkey]] test
            if rawkey != 'rawweather':
                prpkey = rawkey.replace('raw', 'prp')
                svgkey = rawkey.replace('raw', 'svg')
                dataset = getattr(self, prpkey)
                setattr(d, svgkey, [self.pane*d.height+d.height*(1-y) for y in dataset])
    def renderBlock(self, blockData):
        self.initBlock(blockData)
        d=self.block
        self.text()
        self.prpToSvg()
        self.pathData()
        self.svgPath()
        self.svgGraph()
        return self.svgtmpl % self.vars

class OpaqueLayer(Layer):
    # todo add medium opacity for graphs, which can partially obscure text
    isOpaque = True
    # todo can avoid this boilerplate?
    def __init__(self, dataD):
        Layer.__init__(self, dataD)
class TransparentLayer(Layer):
    isOpaque = False
    def __init__(self, dataD):
        Layer.__init__(self, dataD)

class Temp(TransparentLayer):
    def __init__(self, pane):
        TransparentLayer.__init__(self, dict(rawtemp='hourly-temperature'))
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <desc> path and min, max, and description text of temperature </desc>
            <path fill='none' stroke-width=3 stroke="#faa" title='%(temptip)s' d='%(temppath)s' />
            <text x=%(minTempX)d y=%(minTempY)s font-size=%(bigFontSize)s fill="%(lotempcolor)s">%(minTemp)s</text>
            <text x=%(maxTempX)d y=%(maxTempY)s font-size=%(bigFontSize)s fill="%(hitempcolor)s">%(maxTemp)s</text>
            <text x=%(paneDescX)s y=%(paneDescY)s font-size=%(smallFontSize)s fill="%(paneDescColor)s">temps</text>
        '''
    def rawToProp(me):
        me.prptemp=[
            (temp-me.min)/me.range if temp is not None else temp
                for temp in me.rawtemp]
    def text(self):
        d=self.block
        minTempBlock,maxTempBlock=minmax(self.rawtemp)
        knowMinTemp=(d.isvg > isvgA or len(d.xdata.raw) == nHrsInFullBlock)
        knowMaxTemp=(d.isvg < isvgZ or len(d.xdata.raw) >= minHrsToKnowMaxTemp)
        self.vars.update(dict(
            temptip='temp(F): %s'%(str(self.rawtemp)),
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
        d.svgtemp = [self.pane*d.height+d.height*(1-y) for y in self.prptemp]
    def svgPath(self):
        d=self.block
        self.vars.update(dict(
            temppath=coordsToPath(d.xdata.svg,d.svgtemp)
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

class Weather(TransparentLayer):
    # this class not yet finished!
    # see also the unused bargraph output in class PrecipAmt
    def __init__(self, pane):
        TransparentLayer.__init__(self, dict(rawweather='weather'))
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <text x=6.8 y=%(weatherY)d font-size=4 fill="%(weathercolor)s">%(weather)s</text>
        '''
    def rawToProp(me):
        # eg "chance of rain and slight chance of snow"
        me.prpweather = [' and '.join(prob + ' of ' + typ for prob, typ in zip(probs,types))
                for types,probs,prob in me.rawweather]
    def prpToSvg(self):
        pass
    def text(self):
        d=self.block
        self.vars.update(dict(
            svgid=d.svgid,
            weathercolor='black' if d.isdaytime else 'none',
            weather='code in progress',
            weatherY = 10 + blockHtPx * self.pane,
        ))
    def pathData(self):
        pass
    def svgPath(self):
        pass
    def svgGraph(self):
        pass

class DayDate(TransparentLayer):
    def __init__(self, pane):
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <text x=3.3 y=%(dayofweekY)d font-size=12 fill="%(dayofweekcolor)s">%(dayofweek)s</text>
            <text x=6.8 y=%(dateofmonthY)d font-size=12 fill="%(dateofmonthcolor)s">%(dateofmonth)s</text>
        '''
    # todo not using rawData mechanism--should Qnty vs Text be a mixin?
    def setRawData(self, data, istart, iend):
        pass
    def prpToSvg(self):
        pass
    def text(self):
        d=self.block
        self.vars.update(dict(
            svgid=d.svgid,
            dayofweekcolor='black' if d.isdaytime else 'none',
            dateofmonthcolor='black' if d.isdaytime else 'none',
            dayofweek=d.today.strftime('%a'),
            dateofmonth=d.today.strftime('%d'),
            dayofweekY = 10 + blockHtPx * self.pane,
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
        OpaqueLayer.__init__(self, dict(rawcloud='total-cloudamount'))
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
    def rawToProp(self):
        # pad *clip (as opposed to *path) datasets w/ zero at both ends--these are 'droppoints'
        # bug: data array may end in a run of missing values, so padding w/ zeroes wont result in a vertical drop cuz xs will advance from last number to first missingval.
        self.rawcloud = [0] + self.rawcloud + [0]
        self.prpcloud=[
            pct/100. if pct is not None else pct
                for pct in self.rawcloud]
    def text(self):
        d=self.block
        self.vars.update(dict(
            svgid=d.svgid,
            sunormoon='sun' if d.isdaytime else 'moon',
            cloudtip='%%cloudiness: %s'%(str(self.rawcloud[1:-1])),
            smallFontSize=smallFontSize,
            cloudBkgdX = 0,
            blockWdPx = blockWdPx,
            blockHtPx = blockHtPx,
        ))
    def pathData(self):
        d=self.block
        d.svgcloud = [self.pane*d.height+d.height*(1-y) for y in self.prpcloud]
    def svgPath(self):
        d=self.block
        self.vars.update(dict(
            cloudclip = coordsToPath(d.xdata.svg, d.svgcloud, closePath = True)
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

class PrecipProb(TransparentLayer):
    def __init__(self, pane):
        TransparentLayer.__init__(self, dict(
            rawprecipprob='floating-probabilityofprecipitation',
            rawprecipamt='floating-hourlyqpf',
        ))
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <path d="%(precipclip)s" title='%(preciptip)s' stroke='#aaa' stroke-width=3 fill='none' />
            <text x=%(paneDescX)s y=%(paneDescY)s font-size=%(smallFontSize)s fill="%(paneDescColor)s">storms</text>
        '''
    # todo mixin class PrecipData
    def rawToProp(self):
        self.prpprecipprob=[
            pct if pct is None else pct/100.
                for pct in self.rawprecipprob]
        self.prpprecipamt=[
            classifyPrecipAmt(amt)/maxPrecipAmt
                for amt in self.rawprecipamt] 
    def text(self):
        d=self.block
        totalprecip,totalprecipAsStr=self.sumPrecipToString(self.rawprecipamt)
        maxPrecipChance=max(self.rawprecipprob)
        self.vars.update(dict(
            svgwidth=d.magfactor*d.blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
            precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            #preciptip='precipChance(%%): %s'%(str(self.rawprecipprob)),
            preciptip='',
            bigFontSize=bigFontSize,
            smallFontSize=smallFontSize,
            precippctX = precippctX,
        ))
    def pathData(self):
        d=self.block
        d.svgprecipprob = [self.pane*d.height+d.height*(1-y) for y in self.prpprecipprob]
    def svgPath(self):
        d=self.block
        self.vars.update(dict(
            precipclip = coordsToPath(d.xdata.svg, d.svgprecipprob)
        ))
    def svgGraph(self):
        d=self.block
        frame=Frame(x=0,y=self.pane*d.height,width=d.width,height=d.height)
        self.vars.update(dict(
            precippctY=self.pane*d.height+13,
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

class PrecipMaxProb(TransparentLayer):
    def __init__(self, pane):
        TransparentLayer.__init__(self, dict(
            rawprecipamt='floating-hourlyqpf',
            rawprecipprob='floating-probabilityofprecipitation',
        ))
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <text x=%(precippctX)d y=%(precippctY)d font-size=%(bigFontSize)s fill="%(preciptextcolor)s">%(precippct)s%%</text>
        '''
    def rawToProp(self):
        self.prpprecipprob=[
            pct if pct is None else pct/100.
                for pct in self.rawprecipprob]
        self.prpprecipamt=[
            classifyPrecipAmt(amt)/maxPrecipAmt
                for amt in self.rawprecipamt] 
    def text(self):
        d=self.block
        totalprecip,totalprecipAsStr=self.sumPrecipToString(self.rawprecipamt)
        maxPrecipChance=max(self.rawprecipprob)
        self.vars.update(dict(
            svgwidth=d.magfactor*d.blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
            precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            #preciptip='precipChance(%%): %s'%(str(self.rawprecipprob)),
            preciptip='',
            bigFontSize=bigFontSize,
            smallFontSize=smallFontSize,
            precippctX = precippctX,
        ))
    def pathData(self):
        d=self.block
        d.svgprecipprob = [self.pane*d.height+d.height*(1-y) for y in self.prpprecipprob]
    def svgPath(self):
        d=self.block
        self.vars.update(dict(
            precipclip = coordsToPath(d.xdata.svg, d.svgprecipprob)
        ))
    def svgGraph(self):
        d=self.block
        frame=Frame(x=0,y=self.pane*d.height,width=d.width,height=d.height)
        self.vars.update(dict(
            precippctY=self.pane*d.height+13,
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

class PrecipAmt(TransparentLayer):
    def __init__(self, pane):
        TransparentLayer.__init__(self, dict(
            rawprecipamt='floating-hourlyqpf',
            rawprecipprob='floating-probabilityofprecipitation',
            rawweather='weather',
        ))
        self.pane = pane
        self.vars = {}
        self.svgtmpl='''
            <desc> mid: rain text </desc>
            <text x=%(preciptotX)d y=%(preciptotY)d font-size=%(bigFontSize)s fill="%(preciptextcolor)s">%(preciptot)s"</text>
        '''
    def rawToProp(self):
        self.prpprecipprob=[
            pct if pct is None else pct/100.
                for pct in self.rawprecipprob]
        self.prpprecipamt=[
            classifyPrecipAmt(amt)/maxPrecipAmt
                for amt in self.rawprecipamt] 
        self.prpweather = [' and '.join(prob + ' of ' + typ for prob, typ in zip(probs,types))
                for types,probs,prob in self.rawweather]
    def text(self):
        d=self.block
        totalprecip,totalprecipAsStr=self.sumPrecipToString(self.rawprecipamt)
        maxPrecipChance=max(self.rawprecipprob)
        self.vars.update(dict(
            svgwidth=d.magfactor*d.blockwidth, # if blockwidth<30 else fullblockwidth if isdaytime else fullblockwidth*nightwidthfactor,
            preciptot=totalprecipAsStr,
            preciptextcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            preciptip='precipAmt(in): %s'%(list(zip(d.xdata.raw,self.rawprecipamt,self.prpweather))),
            bigFontSize=bigFontSize,
            smallFontSize=smallFontSize,
            preciptotX = preciptotX,
        ))
    def pathData(self):
        d=self.block
        d.svgprecipamt = [self.pane*d.height+d.height*(1-y) for y in self.prpprecipamt]
    def svgPath(self):
        pass
    def svgGraph(self):
        d=self.block
        frame=Frame(x=0,y=self.pane*d.height,width=d.width,height=d.height)
        self.vars.update(dict(
            # precipamt is not currently graphed [see self.svgtmpl]
            #precipamt = bargraph(frame,d.xdata.prp,self.prpprecipamt,self.prpweather,svgid=d.svgid),
            preciptotY=self.pane*d.height+21,
        ))
    def sumPrecipToString(self, amts):
        total=sum([y for y in amts if y is not missing])
        roundedtotal=round(total,1)
        if total>0.0 and roundedtotal==0.0:
            return total,'&lt;0.1'
        else:
            return total,str(roundedtotal)


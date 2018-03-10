
from gcst.util import (debug, Frame, missing,
        minmax, classifyRange, enum, Obj, normalizePercentage)
from gcst.writeSvg import bargraph, coordsToPath
from gcst.properties import properties
from gcst.precip import normalizePrecipAmt, sumPrecipToString

properties = Obj(properties)

isvgA = 0
isvgZ = 14
nHrsInFullBlock = 12

# some datatypes, like percentages, are naturally scaled.
# others, like temperature, we scale between the extremes that occur during the forecast.
datatypesThatNeedScaling = dict(
    # temperature needs to be scaled but has no intrinsic floor or ceiling
    temperature = dict(),

    # for windspeed, unlike temperature, zero should always be the minimum on the graph.
    # use 'windspeed', not 'wind', to avoid matching 'windchill', which is a temperature
    windspeed = dict(floor = 0),
)

def scaleData(data):
    minMaxRange = {}
    for key, dataset in data.items():
        for datatype, limits in datatypesThatNeedScaling.items():
            if datatype in key:
                break
        else:
            continue
        minn, maxx = minmax(dataset)
        if 'floor' in limits:
            minn = limits['floor']
        if minn is not missing and maxx is not missing:
            dataRange = maxx - float(minn)
            minMaxRange[key + '-minMaxRange'] = minn, maxx, dataRange
            minMaxRange[key + '-canScale'] = minn != maxx
        else:
            minMaxRange[key + '-canScale'] = False
    data.update(minMaxRange)

Opacity = enum(
    textOnly = 0,    # essentially transparent
    lineGraph = .5,  # mostly transparent, tho line may obscure text
    clipGraph = 1    # graph formed by clipping an [opaque] image
)

class Block(Obj):
    def __init__(self, blockProperties):
        self.update(blockProperties)

class Pane(object):
    '''manage set of data objects in this pane
        and associate a description
        [currently displayed only when block is unfolded]
        '''
    def __init__(self, objs, desc = ''):
        self.desc = desc
        self.objs = objs
        self.checkLayers()
        if desc:
            # objs [eg Temp] are still classes, not yet instantiated.
            # they will be instantiated in processConfig.
            # thus here we add an instantiatable Description.
            descFactory = lambda ipane: Description(ipane, desc)
            descFactory.opacity = Opacity.textOnly
            self.objs.append(descFactory)
    def dataObjs(self):
        return self.objs
    def checkLayers(self):
        conflictingOpaqueLayers = sum(1 for layer in self.objs if layer.opacity == Opacity.clipGraph) > 1
        if conflictingOpaqueLayers:
            # todo tell which layer[s] conflict
            raise Exception('conflictingOpaqueLayers on pane [%d]' % (self.idx,))

def processConfig(panes):
    npanes = len(panes)
    transparency = lambda obj: -obj.opacity
    dataObjs = [
        Obj(ipane)
        for ipane, pane in enumerate(panes)
        for Obj in sorted(pane.dataObjs(), key = transparency)]
    return dataObjs, npanes


class Layer(object):
    def __init__(self, pane, dataD):
        self.pane = pane
        self.svgVars = {}
        self.svgVars.update(properties.common)
        self.dataD = dataD  # dataD means dataDictionary
    def setRawData(self, data, istart, iend):
        # add hourly data of relevant types
        for rawkey, xmlkey in self.dataD.items():
            # eg: self.rawtemp = data['hourly-temperature'][istart:iend]
            # todo make this a read-only view to avoid a pointless copy
            setattr(self, rawkey,  data[xmlkey][istart:iend])
            if data.get(xmlkey + '-canScale'):
                self.min, maxx, self.range = data[xmlkey + '-minMaxRange']
    def initBlock(self, blockProperties):
        self.block=Block(properties.common)
        self.block.update(blockProperties)
    def renderBlock(self, blockProperties = None):
        if blockProperties:
            self.initBlock(blockProperties)
        self.loadSvgVars()
        return self.svgtmpl % self.svgVars

class TextLayer(Layer):
    # layer that displays text independent of hourly data
    opacity = Opacity.textOnly
    def __init__(self, pane):
        dataD = {}  # a data-less layer
        Layer.__init__(self, pane, dataD)

class DataLayer(Layer):
    opacity = Opacity.textOnly
    def __init__(self, pane, dataD):
        Layer.__init__(self, pane, dataD)
    def loadSvgVars(self):
        self.rawToProp()
        self.text()

class GraphLayer(Layer):
    def __init__(self, pane, dataD):
        Layer.__init__(self, pane, dataD)
    def rawToProp(self):
        # adjust raw data and transform to proportion, if needed
        pass
    def prpToSvg(self):
        d=self.block
        for rawkey in self.dataD:
            # todo replace with isNumeric[data[rawkey]] test
            if rawkey != 'rawweather':
                prpkey = rawkey.replace('raw', 'prp')
                svgkey = rawkey.replace('raw', 'svg')
                dataset = getattr(self, prpkey)
                setattr(d, svgkey, [y if y is None else self.pane*d.height+d.height*(1-y) for y in dataset])
    def computePathData(self, prpData):
        d = self.block
        return [y if y is None else self.pane * d.height + d.height * (1 - y) for y in prpData]
    def loadSvgVars(self):
        self.text()
        self.rawToProp()
        self.prpToSvg()
        self.pathData()
        self.svgPath()

class LineLayer(GraphLayer):
    opacity = Opacity.lineGraph
    def __init__(self, pane, dataD):
        GraphLayer.__init__(self, pane, dataD)

class ClipLayer(GraphLayer):
    opacity = Opacity.clipGraph
    def __init__(self, pane, dataD):
        GraphLayer.__init__(self, pane, dataD)

class Description(TextLayer):
    def __init__(self, pane, desc):
        TextLayer.__init__(self, pane)
        self.desc = desc
        self.svgtmpl=('<text x=%(x)s y=%(y)s'
            ' font-size=%(smallFontSize)s fill="%(textcolor)s">%(desc)s</text>')
    def loadSvgVars(self):
        d=self.block
        d.update(properties.description)
        self.svgVars.update(dict(
            desc = self.desc,
            y = self.pane * d.height + d.paneDescYOffPx,
            x = d.paneDescXProp * d.blockwidth,
            textcolor = self.paneDescColor(),
        ))
    def paneDescColor(self):
        d=self.block
        return '#bbb' if (
            d.isdaytime and not d.iscompact and d.blockwidth==d.fullblockwidth) else 'none'

class Temp(LineLayer):
    # todo split Temp into graph vs max/min toward more modularity
    def __init__(self, pane):
        LineLayer.__init__(self, pane, dict(rawtemp='hourly-temperature'))
        self.svgtmpl='''
            <path fill='none' stroke-width=3 stroke="#faa" title='%(temptip)s' d='%(temppath)s' />
            <text x=%(minTempX)d y=%(minTempY)s font-size=%(bigFontSize)s fill="%(lotempcolor)s">%(minTemp)s</text>
            <text x=%(maxTempX)d y=%(maxTempY)s font-size=%(bigFontSize)s fill="%(hitempcolor)s">%(maxTemp)s</text>
        '''
    def rawToProp(me):
        me.prptemp=[
            (temp-me.min)/me.range if temp is not None else temp
                for temp in me.rawtemp]
    def text(self):
        d=self.block
        d.update(properties.temp)
        minTempBlock,maxTempBlock=minmax(self.rawtemp)
        knowMinTemp=(d.isvg > isvgA or len(d.xdata.raw) == nHrsInFullBlock)
        knowMaxTemp=(d.isvg < isvgZ or len(d.xdata.raw) >= d.minHrsToKnowMaxTemp)
        self.svgVars.update(dict(
            temptip='temp(F): %s'%(str(self.rawtemp)),
            minTemp=str(minTempBlock)+r'&deg;' if minTempBlock and knowMinTemp else '',
            maxTemp=str(maxTempBlock)+r'&deg;' if maxTempBlock and knowMaxTemp else '',
            minTempX = d.minTempXPx,
            maxTempX = d.maxTempFoldXPx if d.foldedOrUnfolded == 'unfolded0' else d.maxTempUnfoXPx,
            minTempY = str(self.pane * d.height + d.minTempYOffPx),
            maxTempY = str(self.pane * d.height + d.maxTempYOffPx),
            hitempcolor = d.hiTempTextColor if d.isdaytime else 'none',
            lotempcolor = d.loTempTextColor if d.isdaytime else 'none',
        ))
    def pathData(self):
        d=self.block
        d.svgtemp = self.computePathData(self.prptemp)
    def svgPath(self):
        d=self.block
        self.svgVars.update(dict(
            temppath=coordsToPath(d.xdata.svg,d.svgtemp)
        ))

class Weather(DataLayer):
    # this class is not yet finished!
    # see also the unused bargraph output in class PrecipAmt
    def __init__(self, pane):
        DataLayer.__init__(self, dict(rawweather='weather'))
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
        self.svgVars.update(dict(
            svgid=d.svgid,
            weathercolor='black' if d.isdaytime else 'none',
            weather='code in progress',
            weatherY = 10 + d.blockHtPx * self.pane,
        ))

class DayDate(TextLayer):
    # provides "Fri / 12" display
    def __init__(self, pane):
        TextLayer.__init__(self, pane)
        self.svgtmpl='''
            <text x=3.3 y=%(dayofweekY)d font-size=12 fill="%(dayofweekcolor)s">%(dayofweek)s</text>
            <text x=6.8 y=%(dateofmonthY)d font-size=12 fill="%(dateofmonthcolor)s">%(dateofmonth)s</text>
        '''
    def loadSvgVars(self):
        d=self.block
        self.svgVars.update(dict(
            svgid=d.svgid,
            dayofweekcolor='black' if d.isdaytime else 'none',
            dateofmonthcolor='black' if d.isdaytime else 'none',
            dayofweek=d.today.strftime('%a'),
            dateofmonth=d.today.strftime('%d'),
            dayofweekY = 10 + d.blockHtPx * self.pane,
            dateofmonthY = 20 + d.blockHtPx * self.pane,
        ))

class Clouds(ClipLayer):
    # graph %clouds via clipping cloudy image over clear sky image
    def __init__(self, pane):
        ClipLayer.__init__(self, pane, dict(rawcloud='total-cloudamount'))
        self.svgtmpl='''
            <image xlink:href="/static/gcst/img/%(sunormoon)s.png" 
                x=%(cloudBkgdX)d y=%(cloudBkgdY)d width=%(blockWdPx)d height=%(blockHtPx)d />
            <clipPath id="pctclouds%(svgid)s%(paneid)d" >
                <path d="%(cloudclip)s"/>
                </clipPath>
            <image xlink:href="/static/gcst/img/%(sunormoon)sclouds.png" title='%(cloudtip)s' 
                x=%(cloudBkgdX)d y=%(cloudBkgdY)d width=%(blockWdPx)d height=%(blockHtPx)d clip-path="url(#pctclouds%(svgid)s%(paneid)d)" />
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
        self.svgVars.update(dict(
            svgid=d.svgid,
            sunormoon='sun' if d.isdaytime else 'moon',
            cloudtip='%%cloudiness: %s'%(str(self.rawcloud[1:-1])),
            cloudBkgdX = 0,
            cloudBkgdY = self.pane*d.height,
            paneid = self.pane,  # maybe move up to ClipLayer
        ))
    def pathData(self):
        d=self.block
        d.svgcloud = self.computePathData(self.prpcloud)
    def svgPath(self):
        d=self.block
        #print(len(d.xdata.svg),len(d.svgcloud))  # generally 12,14 or 12,16--how 16??
        # how did clouds work before without padding xdata to reflect padding w/ zeroes in rawToProp?
        xdata = [d.xdata.svg[0]] + d.xdata.svg + [d.xdata.svg[-1]]
        self.svgVars.update(dict(
            cloudclip = coordsToPath(xdata, d.svgcloud, closePath = True)
        ))

class PrecipProb(LineLayer):
    # line graph of precip probability
    def __init__(self, pane):
        LineLayer.__init__(self, pane, dict(
            rawprecipprob='floating-probabilityofprecipitation',
        ))
        self.svgtmpl='''
            <path d="%(precipclip)s" title='%(preciptip)s' stroke='#aaa' stroke-width=3 fill='none' />
        '''
    def rawToProp(self):
        self.prpprecipprob = normalizePercentage(self.rawprecipprob)
    def text(self):
        d=self.block
        d.update(properties.precip)
        self.svgVars.update(dict(
            #preciptip='precipChance(%%): %s'%(str(self.rawprecipprob)),
            preciptip='',
            precippctY = self.pane*d.height+13,
        ))
    def pathData(self):
        d=self.block
        d.svgprecipprob = self.computePathData(self.prpprecipprob)
    def svgPath(self):
        d=self.block
        self.svgVars.update(dict(
            precipclip = coordsToPath(d.xdata.svg, d.svgprecipprob)
        ))

class PrecipMaxProb(DataLayer):
    # display greatest hourly precip probability for the block
    def __init__(self, pane):
        DataLayer.__init__(self, pane, dict(
            rawprecipamt='floating-hourlyqpf',
            rawprecipprob='floating-probabilityofprecipitation',
        ))
        self.svgtmpl='''
            <text x=%(x)d y=%(y)d font-size=%(bigFontSize)s fill="%(textcolor)s">%(precippct)s%%</text>
        '''
    def rawToProp(self):
        self.prpprecipprob = normalizePercentage(self.rawprecipprob)
        self.prpprecipamt = normalizePrecipAmt(self.rawprecipamt)
    def text(self):
        d=self.block
        d.update(properties.precip)
        totalprecip, totalprecipAsStr = sumPrecipToString(self.rawprecipamt)
        maxPrecipChance=max(self.rawprecipprob)
        self.svgVars.update(dict(
            precippct=str(int(round(maxPrecipChance,-1))) if maxPrecipChance else '',
            textcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            #preciptip='precipChance(%%): %s'%(str(self.rawprecipprob)),
            preciptip='',
            x = d.precippctX,
            y = self.pane*d.height+13,
        ))

class PrecipAmt(DataLayer):
    # display total precip for the block [ie for the day or the night]
    def __init__(self, pane):
        DataLayer.__init__(self, pane, dict(
            rawprecipamt='floating-hourlyqpf',
            rawprecipprob='floating-probabilityofprecipitation',
            rawweather='weather',
        ))
        self.svgtmpl='''
            <text x=%(x)d y=%(y)d font-size=%(bigFontSize)s fill="%(textcolor)s">%(preciptot)s"</text>
        '''
    def rawToProp(self):
        self.prpprecipprob = normalizePercentage(self.rawprecipprob)
        self.prpprecipamt = normalizePrecipAmt(self.rawprecipamt)
        self.prpweather = [' and '.join(prob + ' of ' + typ for prob, typ in zip(probs,types))
                for types,probs,prob in self.rawweather]
    def text(self):
        d=self.block
        d.update(properties.precip)
        totalprecip, totalprecipAsStr = sumPrecipToString(self.rawprecipamt)
        # former bug: maxPrecipChance = max(self.rawprecipamt)
        #   current error msg: TypeError: unorderable types: NoneType() > float()
        #   provide msg [via pint?] like: type mismatch, probability vs amount
        maxPrecipChance=max(self.rawprecipprob)
        self.svgVars.update(dict(
            preciptot = totalprecipAsStr,
            textcolor='black' if totalprecip>=.1 or maxPrecipChance>=20 else 'none',
            preciptip='precipAmt(in): %s'%(list(zip(d.xdata.raw, self.rawprecipamt, self.prpweather))),
            x = d.preciptotX,
            y = self.pane*d.height+21,
        ))


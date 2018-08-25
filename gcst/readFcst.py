
from os import access,makedirs,O_RDONLY
from collections import namedtuple, defaultdict
from dateutil.parser import parse as parseDate
from lxml import etree
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO, BytesIO
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen
from gcst.util import missing

class NoData(Exception): pass
# todo mock this
simulateNoData = False

def getnewdata(zipc, lat, lon, dataurl, cacheData):
    '''get xml forecast from weather.gov [not from cache]'''
    xml=urlopen(dataurl).read()
    if simulateNoData:
        xml=''
    if not xml:
        # render frame around data, incl links to NWS,
        #   but replace data with user-readable message
        raise NoData('<a href="%(dataurl)s">empty xml response</a> from <a href="http://weather.gov">NWS</a>')
    if cacheData and zipc:
        if not os.access(appcachedir,O_RDONLY):
            makedirs(appcachedir)
            open('%s/%s.xml'%(appcachedir,zipc),'w').write(xml)
    #todo record age/expirationDate of this fcst
    return xml

def startparse(xml):
    '''create parse tree and parse the list of starttimes
      [of the hourly time segments in the forecast].
      see sample xml forecast at:
        http://forecast.weather.gov/MapClick.php?lat=40.357439&lon=-74.64922&FcstType=digitalDWML
    '''
    tree   = etree.parse(BytesIO(xml))
    starttimes=[parseDate(starttime) for starttime in tree.xpath('data/time-layout/start-valid-time/text()')]
    return tree,starttimes

def getdata(location, dataurl, cacheData):
    '''get data [from cache or fresh] and start parse'''
    zipc,lat,lon=(location[k] for k in 'zipc,lat,lon'.split(','))
    xml = None
    if cacheData:
        try:
            xml = open('%s/%s.xml'%(appcachedir,zipc)).read()
            tree, starttimes = startparse(xml)
            fcststart = starttimes[0]
            if fcststart - dt.now()<0.1*hour:
                xml = None
        except Exception as e:
            pass
    if not xml:
        xml = getnewdata(zipc, lat, lon, dataurl, cacheData)
        tree, starttimes = startparse(xml)
    return tree, starttimes

def getFcstData(location, cacheData):
    # forecast is one week, ie approx 168hours,
    #   generally 14blocks of 12hours each, except the first and
    #   last blocks are usually incomplete (ie are less than 12hours)
    lat,lon=(location[k] for k in 'lat lon'.split())
    slots = dict(
        # eg ringoes http://forecast.weather.gov/MapClick.php?lat=40.44659793594707&lon=-74.8513979210764&FcstType=digitalDWML
        dataurl=   'http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s&FcstType=digitalDWML'%(lat,lon),
        tabularurl='http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s&FcstType=digital'%(lat,lon),
        humanurl=  'http://forecast.weather.gov/MapClick.php?lat=%s&lon=%s'%(lat,lon),
    )
    try:
        # parameters section contains temperature [of several types], cloud-amount, wind-speed, etc
        tree, starttimes = getdata(location, slots['dataurl'], cacheData)
        #alt=tree.xpath('data/location/height/text()')[0]
        #loc=tree.xpath('data/location/city/text()')[0]
        def getFcstDt(tree, slots):
            '''get date and time of the forecast as strings'''
            fcstDt=tree.xpath('head/product/creation-date/text()')[0]
            date,time=fcstDt.split('T')
            time,tz=time.rsplit('-',1)
            time=time.rsplit(':',1)[0]
            slots.update(dict(
                fcstAsOfDate = date,
                fcstAsOfTime = time,
            ))
        def getMoreWthrInfoUrl(tree, slots):
            '''get url for "more weather info"'''
            url=tree.xpath('data/moreWeatherInformation/text()')[0]
            slots.update(dict(
                moreWthrInfo = url
            ))
        getMoreWthrInfoUrl(tree, slots)
        getFcstDt(tree, slots)
        els=[el for el in tree.xpath('data/parameters/node()') if type(el)==etree._Element]
        def conv(typ,val):
            # todo should use typ eg for weather-conditions as well
            return missing if val is missing else int(val) if typ!='floating' else float(val)
        def dataname(el):
            '''
            '<temperature type="dew point" ...>' -> 'dewpoint-temperature'
            '<wind-speed type="gust" ...>'       -> 'gust-windspeed'
            '''
            return '-'.join([x
                for x in (el.attrib.get('type','').replace(' ',''),el.tag.replace('-',''))
                    if x])
        data=dict([
            (dataname(el),[
                conv(
                    el.attrib.get('type'),
                    val.text if val.text is not None else missing )
                for val in el if el.tag!='weather'])
            for el in els])
        WeatherInfo=namedtuple('WeatherInfo','types probs prob')
        def weatherSegment(elattribs):
            weather=defaultdict(list)
            for elattrib in elattribs:
                for xmlattrib,mykey in (('weather-type','types'),('coverage','probability')):
                    if xmlattrib in elattrib:
                        weather[mykey].append(elattrib[xmlattrib])
            # todo check that all probability's are equal
            # todo is first type listed somehow 'primary'
            # we use [0:1] for 1st element because slices can return None w/o error
            return WeatherInfo(
                types=weather['types'],
                probs=weather['probability'],
                prob=weather['probability'][0] if len(weather['probability']) else None)
        data['weather']=[
            weatherSegment(wconds.attrib for wconds in el.getchildren())
                for el in tree.xpath('data/parameters/weather/weather-conditions')
                    if type(el)==etree._Element]
        #print(data.keys())
    except NoData:
        data = {}
        starttimes = []
    return data, starttimes, slots



from gcst.appinfo import appname,makepath
appdir=makepath()

zipcodelines=open('%s/zipcode.csv'%(appdir)).read().split('\n')
zip2latlon=dict([(zipc,(lat,lon,city,state))
    for zipc,city,state,lat,lon,tz,dst in
    [line.replace('"','').split(',') for line in zipcodelines if line.strip()]])
city2zip=dict([((city.lower()+','+state.lower()),zipc)
    for zipc,city,state,lat,lon,tz,dst in
    [line.replace('"','').split(',') for line in zipcodelines if line.strip()]])
del zipcodelines
#TODO move dicts into db
#TODO key by state,city; fuzzy text search?; convert full state name eg 'new jersey'->'nj'

def find(loc):
    '''
        loc can be either zipcode or city,state
        >>> locationInfo = find('08540')   # returns {'city': 'Princeton', 'lat': '40.357439', 'loc': '08540', 'lon': '-74.64922', 'state': 'NJ', 'zipc': '08540'}
        >>> tuple(locationInfo[key] for key in 'city state lat lon zipc'.split())
        ('Princeton', 'NJ', '40.357439', '-74.64922', '08540')
        >>> locationInfo = find('Princeton, NJ')
        >>> tuple(locationInfo[key] for key in 'city state lat lon zipc'.split())
        ('Princeton', 'NJ', '40.349206', '-74.652811', '08544')
        >>> locationInfo = find('princeton nj')   # returns {'city': 'Princeton', 'l': 'princeton', 'lat': '40.349206', 'loc': 'princeton nj', 'lon': '-74.652811', 'state': 'NJ', 'zipc': '08544'}
        >>> tuple(locationInfo[key] for key in 'city state lat lon zipc'.split())
        ('Princeton', 'NJ', '40.349206', '-74.652811', '08544')
        '''
    seekloc=loc.strip()
    zipc=None
    import re
    if re.match(r'\d{5}.*',seekloc):
        # loc is a zipcode
        info=zip2latlon.get(seekloc[:5])
        if info:
            lat,lon,city,state=info
            zipc=loc
    else:
        # loc is a city,state
        if ',' not in seekloc and ' ' in seekloc:
            # replace the last space with comma
            l,r=seekloc.rsplit(' ',1)
            seekloc=l+', '+r
            del l,r
        seekloc=seekloc.replace(' ','').lower()
        zipc=city2zip.get(seekloc)
        if zipc:
            lat,lon,city,state=zip2latlon[zipc]
    if zipc:
        data=dict((k,v) for k,v in locals().items()
            if k in 'loc zipc lat lon city state')
    else:
        data={'errmsg':'cannot find "%s", please try again'%(loc)}
    return data


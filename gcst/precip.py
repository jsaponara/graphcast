
from gcst.util import missing, enum, classifyRange

# precip intensity
#   accto http://theweatherprediction.com/habyhints2/434/
#     inches per hour: light 0.1 rain 0.3 heavy 
#     whereas drizzle & snow are measured in terms of visibility eg: heavy 1/4mile drizzle 1/2mile light
#   we will try: mist .01 drizzle .03 lightRain .1 rain .3 heavyRain 1 downpour 3 torrent
# I=precip intensity
I = enum(*'none mist drizzle lightRain rain heavyRain downpour torrent'.split())
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

def normalizePrecipAmt(rawprecipamt):
    return [classifyPrecipAmt(amt)/maxPrecipAmt for amt in rawprecipamt] 

# todo two sep funcs?
def sumPrecipToString(amts):
    total=sum([y for y in amts if y is not missing])
    roundedtotal=round(total,1)
    if total>0.0 and roundedtotal==0.0:
        return total,'&lt;0.1'
    else:
        return total,str(roundedtotal)


debug=False
missing=None

def isEven(k): return k/2.==int(k/2.)
def isOdd(k): return not isEven(k)

def enum(*sequential, **named):
    # from https://stackoverflow.com/questions/36932
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.items())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

# merely for convenience: dictionary.key rather than dictionary['key']
class Obj(object):
    def __init__(self, dic = None):
        if dic is None:
            dic = {}
        self.__dict__ = dic
    def update(self, dic):
        try:
            self.__dict__.update(dic)
        except TypeError:
            self.__dict__.update(dic.__dict__)
def dict2obj(dic = None):
    return Obj(dic)

def minmax(seq):
    # single pass thru seq; also min(seq) would return None if None is present in seq
    # todo is it possible to have a seq of all None's?
    def nonNone(seq):
        return (item for item in seq if item is not None)
    gen=nonNone(seq)
    try:
        minn=maxx=next(gen)
    except StopIteration:
        return None, None
    for val in gen:
        if val<minn:
            minn=val
        elif val>maxx:
            maxx=val
    return minn,maxx

def normalizePercentage(rawpct):
    return [pct if pct is None else pct/100.
        for pct in rawpct]

def classifyRange(amt,classes):
    '''
        >>> classifyRange(2.4, [(1, 'a'), (2, 'b'), (3, 'c')])
        'c'
    '''
    for limit,classs in classes:
        if amt<limit:
            return classs
    return classes[-1][1]

class Frame:
    '''
    transforms given point [via __call__] or
    coordinate [via xtransform or ytransform] into the
    frame defined by upperLeft corner [x,y], width, and height [in __init__]
    '''
    def __init__(self,x,y,width,height):
        self.x=float(x)
        self.y=float(y)
        self.width=float(width)
        self.height=float(height)
    def __call__(self,x,y):
        # assumes normalized inputs (ie, in the interval 0..1)
        #print(self.x,self.y,self.width,self.height,'--',x,y,'--',self.x+self.width*x,self.y+(1.0-y)*self.height)
        assert 0<=x<=1 and 0<=y<=1, 'x,y=%s,%s' % (x, y)
        return self.x+self.width*x,self.y+(1.0-y)*self.height
    def xtransform(self,x):
        #assert 0<=x<=1, 'x=%s' % x  # got x==1.5, via bargraph/makepath[line20], why?
        return self.x+self.width*x
    def ytransform(self,y):
        assert 0<=y<=1, 'y=%s' % y
        return self.y+(1.0-y)*self.height

class UnitFrame:
    # if data are already in screen units, no need to transform
    def __init__(self):
        pass
    def __call__(self,x,y):
        return x,y
    def xtransform(self,x):
        return x
    def ytransform(self,y):
        return y


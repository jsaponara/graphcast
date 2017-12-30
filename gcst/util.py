
def isEven(k): return k/2.==int(k/2.)
def isOdd(k): return not isEven(k)

def nonNone(seq):
    return (item for item in seq if item is not None)
def minmax(seq):
    # single pass thru seq; also min(seq) would return None if None is present in seq
    # todo is it possible to have a seq of all None's?
    gen=nonNone(seq)
    minn=maxx=next(gen)
    for val in gen:
        if val<minn:
            minn=val
        elif val>maxx:
            maxx=val
    return minn,maxx

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
    def __init__(self,x,y,width,height):
        self.x=float(x)
        self.y=float(y)
        self.width=float(width)
        self.height=float(height)
    def __call__(self,x,y):
        # assumes normalized inputs (ie, in the interval 0..1)
        #print(self.x,self.y,self.width,self.height,'--',x,y,'--',self.x+self.width*x,self.y+(1.0-y)*self.height)
        return self.x+self.width*x,self.y+(1.0-y)*self.height
    def xtransform(self,x):
        return self.x+self.width*x
    def ytransform(self,y):
        return self.y+(1.0-y)*self.height

class NullFrame:
    # if data are already in screen units, no need to transform
    def __init__(self):
        pass
    def __call__(self,x,y):
        return x,y
    def xtransform(self,x):
        return x
    def ytransform(self,y):
        return y

class MissingValue:
    # a NoneType that we can configure to behave conveniently
    # operations return self, comparisons return False
    def __str__(self): return self.__repr__()
    def __repr__(self): return ''
    def __nonzero__(self): return False
    def __add__(self,x): return x    # act like zero
    def __sub__(self,x): return self
    def __mul__(self,x): return self
    def __div__(self,x): return self
    # __trunc__ must return Integral type...can MissingValue inherit from Integral?
    #def __trunc__(self): return self 
    # TypeError: nb_float should return float object
    #def __float__(self): return self
    def __lt__(self,x): return False
    def __gt__(self,x): return False
    def __eq__(self,x): return False
    def __le__(self,x): return self
    def __abs__(self): return self
    def __and__(self,x): return self
    def __floordiv__(self,x): return self
    def __invert__(self,x): return self
    def __long__(self): return self
    def __lshift__(self,x): return self
    def __mod__(self,x): return self
    def __neg__(self,x): return self
    def __or__(self,x): return self
    def __pos__(self,x): return self
    def __pow__(self,x): return self
    def __radd__(self,x): return self
    def __rsub__(self,x): return self
    def __rand__(self,x): return self
    def __rdiv__(self,x): return self
    def __rfloordiv__(self,x): return self
    def __rlshift__(self,x): return self
    def __rmod__(self,x): return self
    def __rmul__(self,x): return self
    def __ror__(self,x): return self
    def __rpow__(self,x): return self
    def __rrshift__(self,x): return self
    def __rshift__(self,x): return self
    def __rtruediv__(self,x): return self
    def __rxor__(self,x): return self
    def __truediv__(self,x): return self
    def __xor__(self,x): return self

missing=MissingValue()


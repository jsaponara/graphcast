
appname='gcst'

def makepath(path='.'):
	from os.path import dirname,join as pathjoin
	return pathjoin(dirname(__file__),path)


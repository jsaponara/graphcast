from django.template import Context, loader
from gcst.models import Fcst,Loc

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext

from gcst.locate import find
from gcst.gcst import fcstgfx

def index(request):
	#latest= Fcst.objects.all()[:5]
	#t = loader.get_template('gcst/index.html')
	#c = Context({ 'latest': latest, })
	#return HttpResponse(t.render(c))
	# OR
	#return RequestContext( 'gcst/index.html' )
	data={}
	loc=request.GET.get('loc')
	if loc:
		data=find(loc)
		if 'errmsg' not in data:
			fcstdata=fcstgfx(data)
			data.update(fcstdata)
	return render_to_response(
		'gcst/index.html',
		data,
		context_instance=RequestContext(request)  # arg needed for staticfiles to load
		)


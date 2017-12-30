from django.urls import path
from gcst import views

urlpatterns = [
	path(r'', views.index, 'main-view'),
	#url(r'^gcst/lat=(?P<gcst_lat>[.\d]+),lon=(?P<gcst_lon>[.\d]+)/$', 'detail'),
	]


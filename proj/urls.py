from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    # Examples:
    # path(r'^$', 'proj.views.home', name='home'),
    # path(r'^proj/', include('proj.foo.urls')),

    path(r'gcst/', include('gcst.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    path(r'admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    #path(r'^admin/', include(admin.site.urls)),
        # Passing a 3-tuple to include() is not supported. Pass a 2-tuple containing the list of patterns and app_name, and provide the namespace argument to include() instead.
]
urlpatterns += staticfiles_urlpatterns()

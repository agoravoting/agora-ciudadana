from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'media/(?P<path>.*)$', 'django.views.static.serve', {'document_root' : settings.ROOT_PATH + '/media'}),

    # just for testing
    (r'templates/(?P<path>.*)$', 'views.serve_templates', {'document_root' : settings.ROOT_PATH + '/templates'}),

    # Uncomment the admin/doc line below to enable admin documentation:
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
)

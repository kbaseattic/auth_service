from django.conf.urls import patterns, include, url
from django.conf.urls.defaults import *
from oauth import AuthStatus

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'authorization_server.views.home', name='home'),
    # url(r'^authorization_server/', include('authorization_server.foo.urls')),
    url(r'^Roles/(?P<role_id>[^/]+)$','authorization_server.handlers.role_handler'),
    url(r'^Roles/?$','authorization_server.handlers.role_handler'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^authstatus/?$', AuthStatus),
)

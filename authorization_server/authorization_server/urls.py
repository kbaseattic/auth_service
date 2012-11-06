from django.conf.urls import patterns, include, url
from django.conf.urls.defaults import *
from oauth import AuthStatus
from django.conf import settings
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'authorization_server.views.home', name='home'),
    # url(r'^authorization_server/', include('authorization_server.foo.urls')),
    url(r'^Roles/(?P<role_id>[^/]+)$','authorization_server.handlers.role_handler'),
    url(r'^Roles/?$','authorization_server.handlers.role_handler'),
    url(r'^Sessions/?$','session.views.show_login_screen'),
    url(r'^Sessions/Login/?$','session.views.login', name='session.login-handler'),
    url(r'^Sessions/Logout/?$','session.views.logout', name='session.logout-handler'),
    url(r'^Sessions/login-dialog$','session.views.login_js'),
    url(r'^Sessions/login-form/?$','session.views.login_form', name='session.login-form'),
    url(r'^Sessions/Exists/?$','session.views.exists'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^authstatus/?$', AuthStatus),
)

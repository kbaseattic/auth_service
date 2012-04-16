from django.conf.urls.defaults import patterns, include, url
from piston.resource import Resource
from KBaseAuth.handlers import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

# RESTful handlers
profile_rez = Resource( ProfileHandler)
oauthkeys_rez = Resource( OAuthKeysHandler)
oauthtokens_rez = Resource( OAuthTokensHandler)
group_rez = Resource( GroupHandler)
role_rez = Resource( RoleHandler)
rolemembers_rez = Resource( RoleMembersHandler)

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'hello.views.home', name='home'),
    # url(r'^hello/', include('hello.foo.urls')),
    url(r'^world/$', 'world.views.index'),
    url(r'^$', 'world.views.index'),

    url(r'^poll/$', 'poll.views.index'),
    url(r'^poll/(?P<poll_id>\d+)/$', 'poll.views.detail'),
    url(r'^poll/(?P<poll_id>\d+)/results/$', 'poll.views.results'),
    url(r'^poll/(?P<poll_id>\d+)/vote/$', 'poll.views.vote'),
    url(r'^poll/authstatus/$', 'poll.views.authstatus'),

    url(r'^profiles/(?P<user_id>\w+)$', profile_rez),
    url(r'^profiles$', profile_rez),
    url(r'^oauthkeys/(?P<oauth_key>\w+)$', oauthkeys_rez),
    url(r'^oauthtokens$', oauthtokens_rez),
    url(r'^oauthtokens/(?P<oauth_token>\w+)$', oauthtokens_rez),
    url(r'^oauthkeys$', oauthkeys_rez),
    url(r'^group/(?P<name>\w+)$', group_rez),
    url(r'^group$', group_rez),
    url(r'^groupmembers/(?P<name>\w+)$', group_rez),
    url(r'^groupmembers$', group_rez),
    url(r'^role/(?P<name>\w+)$', role_rez),
    url(r'^role$', role_rez),
    url(r'^rolemembers/(?P<name>\w+)$', rolemembers_rez),
    url(r'^rolemembers$', rolemembers_rez),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

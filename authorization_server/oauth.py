import logging
import httplib2
import json
import os
import hashlib

# This module performs authentication based on the tokens
# issued by Globus Online's Nexus service, see this URL for
# details:
# http://globusonline.github.com/nexus-docs/api.html
#
# Import the Globus Online client libraries, originally
# sourced from:
# https://github.com/globusonline/python-nexus-client
from nexus import Client

from django.contrib.auth.models import AnonymousUser,User
from django.contrib.auth import login,authenticate
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.conf import settings
from django.http import HttpResponse
from pprint import pformat

"""
This is the 2-legged OAuth authentication code from tastypie
heavily modified into a django authentication middleware.
We base this on RemoteUserMiddleware so that we can get access to the
request object to have access to the request headers, and then we
simply re-use the existing remote user backend code

https://docs.djangoproject.com/en/1.4/howto/auth-remote-user/

   You configure it the same way using the normal instructions, except
that you use this module oauth.TwoLeggedOAuthMiddleware instead of
django.contrib.auth.middleware.RemoteUserMiddleware

   The django.contrib.auth.backends.RemoteUserBackend module is also
used with this module, add it into the AUTHENTICATION_BACKENDS
declaration in settings.py

   To set the authentiction service to be used, set AUTHSVC in your
settings.py file. Here is an example:

AUTHSVC = 'https://graph.api.go.sandbox.globuscs.info/'

   Django modules can check the request.META['KBASEsessid'] for the
session ID that will be used within the KBase session management
infrastructure

   To test this, bind the sample handler into urls.py like this:
...
from oauth import AuthStatus
...
urlpatterns = patterns( ...
    ...
    url(r'^authstatus/?$', AuthStatus),
    ...
)

   Then visit the authstatus URL to see the auth state.

   If you have the perl Bio::KBase::AuthToken libraries installed,
you can test it like this:
token=`perl -MBio::KBase::AuthToken -e 'print Bio::KBase::AuthToken->new( user_id => "papa", password => "papa")->token,"\n";'`
curl -H "Authorization: Bearer $token" http://127.0.0.1:8000/authstatus/

   Steve Chan
   sychan@lbl.gov
   9/6/2012

   Previous documentation follows:

This is a simple 2-legged OAuth authentication model for tastypie.

Copied nearly verbatim from gregbayer's piston example 
 - https://github.com/gregbayer/django-piston-two-legged-oauth

Dependencies: 
 - python-oauth2: https://github.com/simplegeo/python-oauth2
Adapted from example:  
 - http://philipsoutham.com/post/2172924723/two-legged-oauth-in-python
"""

class OAuth2Middleware(AuthenticationMiddleware):

    """
    Two Legged OAuth authenticator. 
    
    This Authentication method checks for a provided HTTP_AUTHORIZATION
    and looks up to see if this is a valid OAuth Consumer
    """

    # Authentication server
    # Create a Python Globus client
    client = Client(config_file=os.path.join(os.path.dirname(__file__), 'nexus/nexus.yml'))

    try:
        authsvc = "https://%s/" % client.config['server']
    except:
        authsvc = 'https://nexus.api.globusonline.org/'


    # Set the salt used for computing a session hash from the signature hash
    salt = "(African || European)?"

    def __init__(self, realm='API'):
        self.realm = realm
        self.user = None
        self.http = httplib2.Http(disable_ssl_certificate_validation=True)
        # The shortcut option will bypass token validation if we already have a django session
        self.shortcut = False

    def process_request(self, request):
        """
        Verify 2-legged oauth request. Parameters accepted as
        values in "Authorization" header, or as a GET request
        or in a POST body.
        """
        # AuthenticationMiddleware is required so that request.user exists.
        if not hasattr(request, 'user'):
            raise ImproperlyConfigured(
                "The Django remote user auth middleware requires the"
                " authentication middleware to be installed.  Edit your"
                " MIDDLEWARE_CLASSES setting to insert"
                " 'django.contrib.auth.middleware.AuthenticationMiddleware'"
                " before the RemoteUserMiddleware class.")
        try:
            if 'HTTP_AUTHORIZATION' in request.META:
                auth_header = request.META.get('HTTP_AUTHORIZATION')
            else:
                logging.debug("No authorization header found.")
                return None
            # Extract the token based on whether it is an OAuth or Bearer
            # token
            if auth_header[:6] == 'OAuth ':
                token = auth_header[6:]
            elif auth_header[:7] == 'Bearer ':
                token = auth_header[7:]
            else:
                logging.info("Authorization header did not contain OAuth or Bearer type token")
                return None
            # Push the token into the META for future reference
            request.META['KBASEtoken'] = token
            if (request.user.is_authenticated() and self.shortcut):
                return

            user_id = OAuth2Middleware.client.authenticate_user( token)
            if not user_id:
                logging.error("Authentication token failed validation")
                return None
            else:
                logging.info("Validated as user " + user_id)
            token_map = {}
            for entry in token.split('|'):
                key, value = entry.split('=')
                token_map[key] = value
            profile = self.get_profile(token)
            if (profile == None):
                logging.error("Token validated, but could not retrieve user profile")
                return None
            # For now, compute a sessionid based on hashing the
            # the signature with the salt
            request.META['KBASEsessid'] = hashlib.sha256(token_map['sig']+OAuth2Middleware.salt).hexdigest()
            # Add in some useful details that came in from the token validation
            request.META['KBASEprofile'] = profile
            # See if the username is already associated with any currently logged
            # in user, if so just pass over the rest
            # Raises exception if it doesn't pass 
            user = authenticate(remote_user=profile['username'])
            if user:
                request.user = user
                # For now, compute a sessionid based on hashing the
                # the signature with the salt
                request.META['KBASEsessid'] = hashlib.sha256(token_map['sig']+OAuth2Middleware.salt).hexdigest()
                print pformat( request.META['KBASEsessid'])
                # Add in some useful details that came in from the token validation
                request.META['KBASEprofile'] = profile
                login(request,user)
            else:
                logging.error( "Failed to return user from call to authenticate() with username " + profile['username'])
        except KeyError, e:
            logging.exception("KeyError in TwoLeggedOAuthMiddleware: %s" % e)
            request.user = AnonymousUser()
        except Exception, e:
            logging.exception("Error in TwoLeggedOAuthMiddleware: %s" % e)


    def get_profile(self,token):
        try:
            token_map = {}
            for entry in token.split('|'):
                key, value = entry.split('=')
                token_map[key] = value
            keyurl = self.__class__.authsvc + "/users/" + token_map['un'] + "?custom_fields=*"
            res,body = self.http.request(keyurl,"GET",
                                         headers={ 'Authorization': 'Globus-Goauthtoken ' + token })
            if (200 <= int(res.status)) and ( int(res.status) < 300):
                profile = json.loads( body)
                return profile
            logging.error( body)
            raise Exception("HTTP", res)
        except Exception, e:
            logging.exception("Error in get_profile.")
            return None


def AuthStatus(request):
    res = "request.user.is_authenticated = %s \n" % request.user.is_authenticated()
    if request.user.is_authenticated():
        res = res + "request.user.username = %s\n" % request.user.username
        if 'KBASEsessid' in request.META:
            res = res + "Your KBase SessionID is %s\n" % request.META['KBASEsessid']
        if 'KBASEprofile' in request.META:
            res = res + "Your profile record is:\n%s\n" % pformat( request.META['KBASEprofile'])
        if 'KBASEtoken' in request.META:
            res = res + "Your OAuth token is:\n%s\n" % pformat( request.META['KBASEtoken'])
    return HttpResponse(res)

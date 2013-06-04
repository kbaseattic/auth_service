# Create your views here.
import datetime
import httplib2
import hashlib
import json
import base64
import os
import logging
import pprint
import rsa
import django.template
import re
from datetime import datetime,timedelta
from django.http import HttpResponse
from django.conf import settings
from nexus import Client
from pymongo import Connection,ReadPreference
from authorization_server.handlers import RoleHandler
import xml.etree.ElementTree as ET

# Authentication server

# Create a Python Globus client
client = Client(config_file=os.path.join(os.path.dirname(__file__), '../nexus/nexus.yml'))

try:
    authsvc = "https://%s/" % client.config['server']
except:
    authsvc = 'https://nexus.api.globusonline.org/'

try:
    salt = settings.KBASE_SESSION_SALT
except:
    logging.info("KBASE_SESSION_SALT not set in settings file, using hard coded default")
    salt = "(African || European)?"

# If we have a front end proxy, hopefully the URL used to access the
# django instance will be configured in the settings file
try:
    proxy_baseurl = settings.PROXY_BASEURL
except:
    proxy_baseurl = None

http = httplib2.Http(disable_ssl_certificate_validation=True)

# Get an instance of the roles handlers so that we can use it to fetch role
# information
role_handler = RoleHandler()

pp = pprint.PrettyPrinter(indent=4)

# regex for parsing session cookies
cookie_re = re.compile(r"un=(\w+)\|kbase_sessionid=(\w+)")

# Setup MongoDB connection
try:
    conn = Connection(settings.MONGODB_CONN)
except AttributeError as e:
    logging.info("No connection settings specified: %s. Using default mongodb." % e)
    conn = Connection(['mongodb.kbase.us'])
except Exception as e:
    logging.warning("Generic exception %s: %s. Connecting to default mongodb." % (type(e),e))
    conn = Connection(['mongodb.kbase.us'])
db = conn.authorization
db.read_preference = ReadPreference.PRIMARY_PREFERRED
sessiondb = db.sessions
sessiondb.ensure_index('kbase_sessionid')

# Default session lifetime in seconds from settings file
# otherwise default to 1 hour
try:
    session_lifetime = settings.SESSION_DB_LIFETIME
except:
    session_lifetime = 3600

# field name mappings from GO to Bio::KBase::AuthUser fields
field_rename = { "username" : "user_id",
                 "email_validated" : "verified",
                 "opt_in" : "opt_in",
                 "fullname" : "name",
                 "email" : "email",
                 "system_admin" : "system_admin",
                 "custom_fields" : "custom_fields"}

# Default fields to return in body of response when
# logging in. CSV of the fieldnames
default_fields = 'user_id,name,email,groups,kbase_sessionid'

# List of fields that we fetch from GO
GO_fields = ",".join(field_rename.keys())

# list of fields that we offer
tmp = set(field_rename.values())
tmp.remove('custom_fields')
tmp.add('groups')
tmp.add('token')
tmp.add('kbase_sessionid')
all_fields = ",".join([ '\'%s\'' % x for x in tmp])

class AuthFailure( Exception ):
    pass

def get_profile(token):
    token_map = {}
    for entry in token.split('|'):
        key, value = entry.split('=')
        token_map[key] = value
    keyurl = authsvc + "/users/" + token_map['un'] + "?custom_fields=*&fields=%s" % GO_fields
    res,body = http.request(keyurl,"GET",
                            headers={ 'Authorization': 'Globus-Goauthtoken ' + token })
    if (200 <= int(res.status)) and ( int(res.status) < 300):
        profile = json.loads( body)
        # rename the fields to match
        profile2 = { field_rename[key] : profile[ key ] for key in field_rename.keys() }
        profile2['groups'] = role_handler.get_groups( profile2['user_id'])
        # strip out unrequested fields
        return profile2
    logging.error( body)
    if int(res.status) == 401 or int(res.status) == 403:
        raise AuthFailure( "Error fetching profile with token - %s" % ET.fromstring(body).find("title").text)
    else:
        raise Exception("HTTP", res)

def get_nexus_token( url, user_id, password):
    h = httplib2.Http(disable_ssl_certificate_validation=True)
    auth = base64.encodestring( user_id + ':' + password )
    headers = { 'Authorization' : 'Basic ' + auth }
    
    h.add_credentials(user_id, password)
    h.follow_all_redirects = True
    
    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    tok = json.loads(content)
    if status>=200 and status<=299:
        return tok['access_token']
    elif status == 401 or status == 403:
        raise AuthFailure( "%s" % tok['message'])
    else:
        raise Exception(tok['message'])

def current_datetime(request):
    now = datetime.now()
    html = "<html><body>It is now %s.</body></html>" % now
    return HttpResponse(html)

def get_baseurl(request):
    if proxy_baseurl is None:
        if request.is_secure():
            scheme = 'https://'
        else:
            scheme = 'http://'
        url = '%s%s' % (scheme, request.META.get('HTTP_HOST', request.get_host()))
    else:
        url = proxy_baseurl
    return( url)

def show_login_screen(request):
    return_url = request.GET.get('return_url')
    base_url = get_baseurl(request)
    if return_url is not None:
        login_screen = django.template.loader.render_to_string('login-screen.html',
                                                               { 'return_url' : return_url,
                                                                 'base_url' : base_url })
    else:
        login_screen = django.template.loader.render_to_string('login-screen.html',
                                                               { 'base_url' : base_url})
    return HttpResponse( login_screen)

def login_js(request):
    base_url = get_baseurl(request)
    login_js = django.template.loader.render_to_string('login-dialog.js',{'base_url' : base_url,
                                                                           'all_fields' : all_fields})
    return HttpResponse( login_js, content_type='text/javascript')

def login_form(request):
    login_form = django.template.loader.render_to_string('login-form.html',{})
    HTTPres = HttpResponse( login_form)
    return HTTPres


def exists(request):
    try:
        response = {}
        session_id = request.REQUEST.get('kbase_sessionid')
        client_ip = request.REQUEST.get('client_ip')
        if session_id is None or client_ip is None:
            response['error_msg'] = "Require kbase_sessionid and client_ip as parameters"
            retcode = 400
        else:
            res = sessiondb.find_one( { 'kbase_sessionid' : session_id,
                                        'client_ip' : client_ip,
                                        'expiration' : { '$gte' : datetime.now() }})
            if res is not None:
                response['expiration'] = "%s" % res['expiration']
                retcode = 200
            else:
                response['error_msg'] = "No session found"
                retcode = 404
        # Expire old sessions
        sessiondb.remove( { 'expiration' : { '$lte' : datetime.now() }})
    except Exception, e:
        error = "Error checking existence of session: %s" % e
        logging.error( error)
        response['error_msg'] = error
        retcode = 500
    HTTPres = HttpResponse( json.dumps(response), mimetype="application/json", status = retcode)
    return HTTPres
        
def logout(request):
    try:
        cookie = request.COOKIES.get('kbase_session')
        if cookie is None:
            raise Exception( 'kbase_session cookie required for logout')
        try:
            (username,kbase_sessionid) = cookie_re.match(cookie).groups()
        except:
            raise Exception( 'invalid kbase_session cookie')
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(',')[-1].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        res = sessiondb.find_one( { 'kbase_sessionid' : kbase_sessionid,
                                    'client_ip' : client_ip,
                                    'username' : username })
        if res is not None:
            sessiondb.remove( res)
            HTTPres = HttpResponse( json.dumps({ 'message' : 'session %s deleted' % kbase_sessionid }),
                                    mimetype="application/json")
            cookie = "un=%s|kbase_sessionid=%s" % (username,kbase_sessionid)
            HTTPres.set_cookie( 'kbase_session', cookie,domain=".kbase.us", path="/",expires='Thu, 01 Jan 1970 00:00:01 GMT')

        else:
            HTTPres = HttpResponse( json.dumps({ 'message' : 'session %s not found' % kbase_sessionid }),
                                    mimetype="application/json",status=404)
    except Exception, e:
        HTTPres = HttpResponse( json.dumps({ 'error_msg' : "%s" % e}),
                                mimetype="application/json",status=400)
    return HTTPres

# Main handler to take care logins using either username/password or an existing token        
def login(request):
    try:
        response = {
            'user_id' : request.POST.get('user_id'),
            }
        password = request.POST.get('password')
        cookie = request.POST.get('cookie')
        sessiondoc = dict()
        # Accept a token in lieu of a user_id, password to generate a session
        # for a user that has already logged in
        token = request.POST.get('token')
        # Session lifetime for mongodb sessions. Default set in settings file
        lifetime = request.POST.get('lifetime',session_lifetime)
        fields = request.POST.get('fields',default_fields)
        if (token is not None or (response['user_id'] is not None and password is not None)):
            if not token:
                url = authsvc + "goauth/token?grant_type=client_credentials"
                token = get_nexus_token( url, response['user_id'],password)
            token_map = {}
            for entry in token.split('|'):
                key, value = entry.split('=')
                token_map[key] = value
            profile = get_profile(token)
            if not profile:
                raise AuthFailure( "Failed to fetch profile with token")
            response['kbase_sessionid'] = hashlib.sha256(token_map['sig']+salt).hexdigest()
            response['token'] = token
            custom_fields = profile.get( 'custom_fields',{})
            del profile['custom_fields']
            profile.update(custom_fields)
            response.update(profile)
            sessiondoc=dict(response)
            delkeys = set(response.keys()) - set( fields.split(","))
            for key in delkeys:
                del response[key]
        else:
            raise AuthFailure( "Must specify user_id and password in POST message body")
        if cookie == "only":
            HTTPres = HttpResponse()
        else:
            HTTPres = HttpResponse(json.dumps(response), mimetype="application/json")
        # Push the session into the database if there was a sessionid generated
        if 'kbase_sessionid' in response:
            sessiondoc['creation'] = datetime.now()
            sessiondoc['expiration'] = datetime.now() + timedelta(seconds = lifetime)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                sessiondoc['client_ip'] = x_forwarded_for.split(',')[-1].strip()
            else:
                sessiondoc['client_ip'] = request.META.get('REMOTE_ADDR')
            sessiondb.insert(sessiondoc)
            # Expire old sessions
            sessiondb.remove( { 'expiration' : { '$lte' : datetime.now() }})
            # Convert the datetime objects to string representations
            response['creation'] = "%s" % sessiondoc['creation']
            response['expiration'] = "%s" % sessiondoc['expiration']
        # If we were asked for a cookie, set a kbase_sessionid cookie in the response object
        if cookie is not None and 'kbase_sessionid' in sessiondoc:
            cookie = "un=%s|kbase_sessionid=%s" % (sessiondoc['user_id'],sessiondoc['kbase_sessionid'])
            HTTPres.set_cookie( 'kbase_session', cookie,domain=".kbase.us")
    except AuthFailure, a:
        response['error_msg'] = "%s" % a
        HTTPres = HttpResponse(json.dumps(response), mimetype="application/json", status = 401)
    except Exception, e:
        if type(e).__name__ != "Exception" :
            response['error_msg'] = "%s e: %s" % (type(e).__name__,e)
        else:
            response['error_msg'] = "Exception: %s" % e
        HTTPres = HttpResponse(json.dumps(response), mimetype="application/json", status = 500)
    return HTTPres


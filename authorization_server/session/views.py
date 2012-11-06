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
from pymongo import Connection
from authorization_server.handlers import RoleHandler

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
    logging.error("KBASE_SESSION_SALT not set in settings file, using hard coded default")
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
    print "No connection settings specified: %s\n" % e
    conn = Connection(['mongodb.kbase.us'])
except Exception as e:
    print "Generic exception %s: %s\n" % (type(e),e)
    conn = Connection(['mongodb.kbase.us'])
db = conn.authorization
sessiondb = db.sessions
sessiondb.ensure_index('kbase_sessionid')

# Default session lifetime in seconds from settings file
# otherwise default to 1 hour
try:
    session_lifetime = settings.SESSION_DB_LIFETIME
except:
    session_lifetime = 3600

def get_profile(token):
    try:
        token_map = {}
        for entry in token.split('|'):
            key, value = entry.split('=')
            token_map[key] = value
        keyurl = authsvc + "/users/" + token_map['un'] + "?custom_fields=*&fields=groups,username,email_validated,fullname,email"
        res,body = http.request(keyurl,"GET",
                                headers={ 'Authorization': 'Globus-Goauthtoken ' + token })
        if (200 <= int(res.status)) and ( int(res.status) < 300):
            profile = json.loads( body)
            profile['groups'] = role_handler.get_groups( profile['username'])
            return profile
        logging.error( body)
        raise Exception("HTTP", res)
    except Exception, e:
        logging.exception("Error in get_profile: %s" % e)
        return None

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
            print "HTTP_HOST='%s'\nget_host() = '%s'" % (request.META['HTTP_HOST'],request.get_host())
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
    login_js = django.template.loader.render_to_string('login-dialog.js',{'base_url' : base_url})
    HTTPres = HttpResponse( login_js, content_type = "text/javascript")
    try:
        HTTPres['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
    except Exception as e:
        HTTPres['Access-Control-Allow-Origin'] = "*"
    return HTTPres

def login_form(request):
    login_form = django.template.loader.render_to_string('login-form.html',{})
    HTTPres = HttpResponse( login_form)
    # Enable some basic CORS support
    HTTPres['Access-Control-Allow-Credentials'] = 'true'
    try:
        HTTPres['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
    except Exception as e:
        HTTPres['Access-Control-Allow-Origin'] = "*"
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
    return HttpResponse( json.dumps(response), mimetype="application/json", status = retcode)
        
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
    try:
        HTTPres['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
    except Exception as e:
        HTTPres['Access-Control-Allow-Origin'] = "*"
    return HTTPres
        
def login(request):
    try:
        response = {
            'user_id' : request.POST.get('user_id'),
            }
        password = request.POST.get('password')
        cookie = request.POST.get('cookie')
        # Session lifetime for mongodb sessions. Default set in settings file
        lifetime = request.POST.get('lifetime',session_lifetime)
        if (response['user_id'] is not None and password is not None):
            url = authsvc + "goauth/token?grant_type=client_credentials"
            try:
                response['token'] = get_nexus_token( url, response['user_id'],password)
                token_map = {}
                for entry in response['token'].split('|'):
                    key, value = entry.split('=')
                    token_map[key] = value
                response['kbase_sessionid'] = hashlib.sha256(token_map['sig']+salt).hexdigest()
                profile = get_profile(response['token'])
                response.update(profile)
                response.update(profile['custom_fields'])
                del response['custom_fields']
            except Exception as e:
                response['error_msg'] = "%s" % e
        else:
            response['error_msg'] = "Must specify user_id and password in POST message body"
        if cookie == "only":
            HTTPres = HttpResponse()
        else:
            HTTPres = HttpResponse(json.dumps(response), mimetype="application/json")
        # Push the session into the database if there was a sessionid generated
        if 'kbase_sessionid' in response:
            response['creation'] = datetime.now()
            response['expiration'] = datetime.now() + timedelta(seconds = lifetime)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                response['client_ip'] = x_forwarded_for.split(',')[-1].strip()
            else:
                response['client_ip'] = request.META.get('REMOTE_ADDR')
            sessiondb.insert(response)
            # Expire old sessions
            sessiondb.remove( { 'expiration' : { '$lte' : datetime.now() }})

        # Enable some basic CORS support
        HTTPres['Access-Control-Allow-Credentials'] = 'true'
        try:
            HTTPres['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
        except Exception as e:
            HTTPres['Access-Control-Allow-Origin'] = "*"
        # If we were asked for a cookie, set a kbase_sessionid cookie in the response object
        if cookie is not None and 'kbase_sessionid' in response:
            cookie = "un=%s|kbase_sessionid=%s" % (response['user_id'],response['kbase_sessionid'])
            HTTPres.set_cookie( 'kbase_session', cookie,domain=".kbase.us")
    except Exception, e:
        response['error_msg'] = "%s" % e
        HTTPres = HttpResponse(json.dumps(response), mimetype="application/json", status = 500)
    return HTTPres

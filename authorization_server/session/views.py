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
    raise Exception("KBASE_SESSION_SALT has not been set in settings file.")

http = httplib2.Http(disable_ssl_certificate_validation=True)

# Get an instance of the roles handlers so that we can use it to fetch role
# information
role_handler = RoleHandler()
pp = pprint.PrettyPrinter(indent=4)

# Setup MongoDB connection
try:
    conn = Connection(settings.MONGODB_CONN)
except AttributeError as e:
    print "No connection settings specified: %s\n" % e
    conn = Connection(['mongodb.kbase.us'])
except Exception as e:
    print "Generic exception %s: %s\n" % (type(e),e)
    conn = Connection()
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
    now = datetime.datetime.now()
    html = "<html><body>It is now %s.</body></html>" % now
    return HttpResponse(html)

def login(request):
    response = {
        'user_id' : request.REQUEST.get('user_id'),
        }
    password = request.REQUEST.get('password')
    cookie = request.REQUEST.get('cookie')
    # Session lifetime for mongodb sessions. Default set in settings file
    lifetime = request.REQUEST.get('lifetime',session_lifetime)
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
        response['error_msg'] = "Must specify user_id and password"
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
        HTTPres.set_cookie( 'kbase_session', cookie)
    return HTTPres

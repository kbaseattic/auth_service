# Create your views here.
import datetime
import httplib2
import hashlib
import json
import base64
import os
from django.http import HttpResponse
from django.conf import settings
from nexus import Client

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

def get_nexus_token( url, user_id, password):
    h = httplib2.Http(disable_ssl_certificate_validation=True)
    auth = base64.encodestring( user_id + ':' + password )
    headers = { 'Authorization' : 'Basic ' + auth }
    
    h.add_credentials(user_id, password)
    h.follow_all_redirects = True
    
    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    print "Resp = %s\nStatus = %d\nContent = %s\n" % (resp,status, content)
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
    if (response['user_id'] is not None and password is not None):
        url = authsvc + "goauth/token?grant_type=client_credentials"
        try:
            response['token'] = get_nexus_token( url, response['user_id'],password)
            token = response['token']
            token_map = {}
            for entry in response['token'].split('|'):
                key, value = entry.split('=')
                token_map[key] = value
            response['kbase_sessionid'] = hashlib.sha256(token_map['sig']+salt).hexdigest()
        except Exception as e:
            response['error_msg'] = "%s" % e
    print "%s" % response
    HTTPres = HttpResponse(json.dumps(response), mimetype="application/json")
    # Enable some basic CORS support
    HTTPres['Access-Control-Allow-Credentials'] = 'true'
    try:
        HTTPres['Access-Control-Allow-Origin'] = request.META['HTTP_ORIGIN']
    except Exception as e:
        HTTPres['Access-Control-Allow-Origin'] = "*"
    return HTTPres

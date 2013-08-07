"""

Handlers for the Session service.

This is a set of mongodb backed handlers for a session service. The session service
is used to store session information such as:

authentication token
cross application session data
client information

This service is a web based interface between Globus Nexus and the KBase mongodb
backend service. This service handles logins and then provides a session token
that can be used as a key into Mongodb where actual login tokens are stored

"""


from piston.handler import BaseHandler
from piston.utils import rc
import pprint
import datetime
import json
from pymongo import Connection
from piston.resource import Resource
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

pp = pprint.PrettyPrinter(indent=4)

class SessionHandler( BaseHandler):
    allowed_methods = ('GET','POST','PUT','DELETE')
    fields = ('session_id','token','members','read','modify','delete',
              'impersonate','grant','create','role_owner','role_updater')
    exclude = ( '_id', )
    # We need to define the appropriate settings and set them here
    try:
        print "Connecting to %s" % settings.MONGODB_CONN
        conn = Connection(settings.MONGODB_CONN)
    except AttributeError as e:
        print "No connection settings specified: %s\n" % e
        conn = Connection(['mongodb.kbase.us'])
    except Exception as e:
        print "Generic exception %s: %s\n" % (type(e),e)
        conn = Connection()
    db = conn.authorization
    roles = db.sessions




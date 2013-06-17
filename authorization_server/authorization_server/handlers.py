"""

Handlers for the Roles service.

This is a set of mongodb backed handlers for a REST based authorization
service. The authorization service simply serves up JSON docs that specify
a set of permissions, and the users who have that set of permissions. Here
is a sample JSON object:

{
    "_id": "509ae71f1d41c83cd046f57e",
    "role_owner": "sychan",
    "role_id": "kbase_users",
    "description": "List of user ids who are considered KBase users",
    "members": [
        "sychan",
        "kbasetest",
        "kbauthorz"
    ],
    "role_updater": [
        "sychan",
        "kbauthorz"
    ],
    "read": [],
    "create": [],
    "modify": [],
    "impersonate": [],
    "delete": []
}

   Here are the semantics of the fields:

`   '_id' : 'Unique ID generated by DB backend for this role',
   'role_id' : 'Unique human readable identifer for role (required)',
   'description' : 'Description of the role (required)',
   'role_owner' : 'Owner(creator) of this role',
   'role_updater' : 'User_ids that can update this role',
   'members' : 'A list of the user_ids who are members of this group',
   'read' : 'List of kbase object ids (strings) that this role allows read privs',
   'modify' : 'List of kbase object ids (strings) that this role allows modify privs',
   'delete' : 'List of kbase object ids (strings) that this role allows delete privs',
   'impersonate' : 'List of kbase user_ids (strings) that this role allows impersonate privs',
   'grant' : 'List of kbase authz role_ids (strings) that this role allows grant privs',
   'create' : 'Boolean value - does this role provide the create privilege'

   The service is typically mounted under /Roles. Here are the authentication requirements
for each HTTP method:

   GET : requires valid token and membership in role_id in settings.kbase_users
   PUT : requires valid token and user in role_owner, or in the role_updater field for object
   POST : requires valid token and membership in role_id in settings.kbase_users
   DELETE : requires valid token and request must come from role_owner of target object

   The GET method supports the MongoDB options for filter and fields. For queries and filter
parameters the filter parameter is passed as the first parameter and the fields parameter is
the second parameter passed into the pymongo collection.find() method, see:

http://api.mongodb.org/python/current/api/pymongo/collection.html

   As an example, the following query returns all role objects that have sychan as a member:
http://authorization_host/Roles?filter={ "members" : "sychan"}

   To pull up only the role_id fields:

http://authorization_host/Roles?filter={ "members" : "sychan"}&fields={"role_id" : "1"}

   To pull up the role_id fields for roles with "test" as part of their name (PCRE regex):

http://authorization_host/Roles?filter={ "role_id" : { "$regex" : ".*test.*" }}&fields={ "role_id" : "1" }

"""


from piston.handler import BaseHandler
from piston.utils import rc,require_mime
import pprint
import datetime
import json
import copy
import logging
import common
from jsonschema import validate
from pymongo import Connection
from piston.resource import Resource
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from GlobusGroupsSync import GlobusGroupsSync

pp = pprint.PrettyPrinter(indent=4)

class RoleHandler( BaseHandler):
    version = '0.3.0'
    allowed_methods = ('GET','POST','PUT','DELETE')
    fields = ['role_id','description','members','read','modify','delete',
              'impersonate','grant','create','role_owner','role_updater',
              'globus_group']
    exclude = []
    # We need to define the appropriate settings and set them here
    try:
        conn = Connection(settings.MONGODB_CONN)
    except AttributeError as e:
        logging.info("No connection settings specified: %s. Connecting to default mongodb service" % e)
        conn = Connection(['mongodb.kbase.us'])
    except Exception as e:
        logging.warning("Generic exception %s: %s. Connecting to default mongodb service" % (type(e),e))
        conn = Connection(['mongodb.kbase.us'])
    db = conn.authorization
    roles = db.roles
    roles.ensure_index( 'role_id', unique=True )
    roles.ensure_index( 'members' )
    # Set the role_id to require for updates to the roles db
    try:
        kbase_users = settings.KBASE_USERS
    except AttributeError as e:
        kbase_users = 'kbase_users'

    # Set the role_id specifying which user_ids can create
    # roles that contain ownership information
    try:
        kbase_owners = settings.KBASE_OWNERS
    except AttributeError as e:
        kbase_owners = 'kbase_users'
    
    # Help object when queries go to the top level with no search specification
    help_json = { 'id' : 'KBase Authorization',
                  'version' : version,
                  'documentation' : 'https://docs.google.com/document/d/1CTkthDUPwNzMF22maLyNIktI1sHdWPwtd3lJk0aFb20/edit',
                  'documentation2' : 'https://docs.google.com/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/edit',
                  'resources' : { 'role_id' : 'Unique human readable identifer for role (required)',
                                  'description' : 'Description of the role (required)',
                                  'role_owner' : 'Owner(creator) of this role',
                                  'role_updater' : 'User_ids that can update this role',
                                  'members' : 'A list of the user_ids who are members of this group',
                                  'read' : 'List of kbase object ids (strings) that this role allows read privs',
                                  'modify' : 'List of kbase object ids (strings) that this role allows modify privs',
                                  'delete' : 'List of kbase object ids (strings) that this role allows delete privs',
                                  'impersonate' : 'List of kbase user_ids (strings) that this role allows impersonate privs',
                                  'grant' : 'List of kbase authz role_ids (strings) that this role allows grant privs',
                                  'create' : 'Boolean value - does this role provide the create privilege',
                                  'owns' : 'List of document_ids that are owned by the role_owner and role_updaters',
                                  'globus_group' : 'Optional group path in Globus Online that is used to synchronize members field'
                                  },
                  'contact' : { 'email' : 'sychan@lbl.gov'},
                  'usage'   : 'This is a standard REST service. Note that read handler takes ' + 
                  'MongoDB filtering and JSON field selection options passed as ' +
                  'URL parameters \'filter\' and \'fields\' respectively. ' +
                  'For example, to get a list of all role_id\'s use: ' + 
                  '/Roles/?filter={ "role_id" : { "$regex" : ".*" }}&fields={ "role_id" : "1"} ' + 
                  'Please look at MongoDB pymongo collection documentation for details. ' +
                  'Read and Create are currently open to all authenticated users in role "%s", but' % kbase_users +
                  'delete requires ownership of the document (in field role_owner), ' + 
                  'update requires ownership or membership in the target document\'s role_updaters list.'
                  }

    # Schema used to validate input
    input_schema = { 'type' : 'object',
                     'properties' : { '_id' : { 'type' : 'string' },
                                      'role_id' : { 'type' : 'string', "required":True },
                                      'description' : { 'type' : 'string', "required":True },
                                      'role_owner' : { 'type' : 'string' },
                                      'role_updater' : { 'type' : 'array' },
                                      'members' : { 'type' : 'array' },
                                      'read' : { 'type' : 'array' },
                                      'create' : { 'type' : 'boolean' },
                                      'modify' : { 'type' : 'array' },
                                      'delete' : { 'type' : 'array' },
                                      'impersonate' : { 'type' : 'array' },
                                      'owns' : { 'type' : 'array' },
                                      'globus_group' : { 'type' : 'string' }
                                      }
                     }

    # Schema used for updates
    update_schema = copy.deepcopy(input_schema)
    update_schema['properties']['description'] = { 'type' : 'string'}

    # instance of the class used to synchronize mongodb role members against
    # Globus Online
    gclient = GlobusGroupsSync()

    # Check mongodb to see if the user is in kbase_user role, necessary
    # before they can perform any kinds of updates
    # Note that possessing a Globus Online ID is not sufficient unless
    # the "bypass_kbase_users" setting is defined.
    def check_kbase_user(self, user_id):
        try:
            if not ( hasattr(settings, 'REQUIRE_KBASE_USERS') and
                       settings.REQUIRE_KBASE_USERS ):
                return True
            res = self.roles.find_one( { 'role_id' : self.kbase_users,
                                         'members' : user_id })
            if res is not None:
                return True
            else:
                return False
        except:
            return False


    # Check mongodb to see if the user is in kbase_user role, necessary
    # before they can perform any kinds of updates
    # Note that possessing a Globus Online ID is not sufficient
    def check_kbase_owners(self, user_id):
        try:
            res = self.roles.find_one( { 'role_id' : self.kbase_owners,
                                         'members' : user_id })
            return res is not None
        except:
            return False

    # Given a user_id and document ID array, returns true if the user has ownership
    # privs on the docs
    # basically is this user in the role_owner or role_updater for
    # for a role that specifies ownership of this doc_id
    def owns(self, user_id, doc_ids):
        try:
            owned_docs = self.roles.find( { 'owns' : { '$in' : doc_ids},
                                            '$or' :  [ {'role_owner' : user_id },
                                                       {'role_updater' : user_id} ]},
                                          { 'owns' : 1 }).distinct("owns");
            return set(doc_ids) <= set(owned_docs)
        except:
            # rethrow exception
            raise

    # Check to see if the documents have no ownership assignments
    def no_owners(self, doc_ids):
        try:
            owners = self.roles.find( { 'owns' : { '$in' : doc_ids}},
                                      { 'role_owner' : 1,
                                        'role_updater' : 1 })
            return owners.count() == 0
        except:
            # rethrow exception
            raise


    # Helper function that returns all the groups for a userid, used more for
    # external services than local services
    def get_groups(self, user_id):
        try:
            roles = self.roles.find( { 'members' : user_id }, { 'role_id' : '1' })
            res = [ roles[x]['role_id'] for x in range( roles.count()) ]
            return res
        except Exception, e:
            logging.error( "Failed to fetch groups for user %s : %s" % ( user_id, e))
            return []

    # dedupes array entries in the role doc
    def dedupe( self, doc):
        try:
            keys = [ field for field in self.input_schema['properties'].keys()
                     if self.input_schema['properties'][field]['type'] == 'array']
            for key in keys:
                if key in doc:
                    doc[key] = list(set(doc[key]))
        except:
            # Hmmm, something very strange happened, reraise!
            raise

    # Main query handler
    def read(self, request, role_id=None):
        try:
            if not request.user.username or not self.check_kbase_user( request.user.username):
                res = rc.FORBIDDEN
                res.write(' request not from a member of %s' % self.kbase_users)
            # Just send the informational response if we have "about" in query params
            elif 'about' in request.GET:
                res = [self.help_json]
            else:
                if role_id == None and 'role_id' in request.GET:
                    role_id = request.GET.get('role_id')
                mongo_filter = {}
                mongo_fields = {}
                # set the user_id filter if is is specified
                user_id = request.GET.get('user_id')
                if user_id:
                    mongo_filter['members'] = user_id
                doc_id = request.GET.get('doc_id')
                if doc_id:
                    tmp = [ {x : doc_id} for x in ('grant','read','create','modify','delete',
                                                 'owns')]
                    mongo_filter['$or'] = tmp
                filter = request.GET.get('filter')
                if filter:
                    filter = json.loads(filter)
                    mongo_filter.update( filter)
                fields = request.GET.get('fields')
                if fields:
                    fields = json.loads(fields)
                    mongo_fields.update( fields )
                if fields is not None and '_id' not in fields:
                    self.exclude.append('_id')
                if role_id != None:
                    mongo_filter['role_id'] = role_id
                # Was a merge requested?
                merge = 'union' in request.GET

                # Filter and fields should all be built, lets do the query
                # Sending an empty mongo_fields filters out everything, so if the
                # user didn't specify, leave it out
                if len(mongo_fields.keys()) == 0:
                    match = list(self.roles.find( mongo_filter ))
                else:
                    match = list(self.roles.find( mongo_filter, mongo_fields ))
                if merge:
                    role_ids = ",".join(( match[x]['role_id'] for x in range(len(match))))
                    merged = { 'role_id' : role_ids }
                    for acls in ('grant','read','modify','delete','owns','members'):
                        merged[acls] = list(reduce( set.union, [ set(match[x].get(acls,[])) for x in range(len(match))]))
                    match = [merged]
                if len(mongo_filter.keys()) > 0:
                    res = [ match[x] for x in range( len(match))]
                    for x in res:
                        for excl in self.exclude:
                            if excl in x:
                                del x[excl]
                else:
                    res = [ match[x]['role_id'] for x in range( len(match))]
        except Exception as e:
            res = rc.BAD_REQUEST
            res.write(' error: %s' % e )
        return(res)

    # Verify that the role_owner actually has ownership on the documents being ACL'ed
    def ownership_legit( self, doc, user_id):
        doc_ids = set(doc.get('read',[]) + doc.get('modify',[]) + doc.get('delete',[]))
        # is this an initial ownership assertion?
        own_ids = doc.get('owns', [])
        if own_ids != [] and not self.no_owners(own_ids):
            raise Exception( "Some of the documents in the own clause already have owners")
        # if we had a new claim of ownership, then subtract them from the list of documents
        # that we're going to check ownership for
        doc_ids = doc_ids - set(own_ids)
        if not self.owns( user_id, list(doc_ids)):
            raise Exception( "You do not have ownership privileges on all of these doc_ids: %s" % ",".join(list(doc_ids)))
        return True

    
    @method_decorator(csrf_exempt)
    @require_mime('json')
    def create(self, request):
        try:
            r = request.data
            if not request.user.is_authenticated():
                res = rc.FORBIDDEN
                res.write(' request is not authenticated ')
            elif not self.check_kbase_user( request.user.username):
                res = rc.FORBIDDEN
                res.write(' request not from a member of %s' % self.kbase_users)
            elif self.roles.find( { 'role_id': r['role_id'] }).count() == 0:
                # Schema validation
                new = { x : r.get(x,[]) for x in ('read','modify','delete','impersonate',
                                                  'grant','members','role_updater','owns') }
                new['create'] = r['create']
                new['role_id'] = r['role_id']
                new['description'] = r['description']
                new['role_owner'] = request.user.username
                new['globus_group'] = r.get('globus_group','')
                validate(r,self.input_schema)
                self.dedupe( new)

                # Verify that the current user actually has privs to set ownership
                # on documents at all
                if new['owns'] != [] and not self.check_kbase_owners( request.user.username):
                    raise Exception( "You must be a member of the kbase_owners group in order to set ownership of documents")
                # Verify that the role_owner actually has ownership on the documents being ACL'ed
                try:
                    self.ownership_legit( new, new['role_owner'])
                except:
                    raise
                self.roles.insert( new)
                res = rc.CREATED
            else:
                res = rc.DUPLICATE_ENTRY
        except KeyError as e:
            res = rc.BAD_REQUEST
            res.write(' required fields: %s' % e )
        except Exception as e:
            res = rc.BAD_REQUEST
            res.write(' error: %s' % e )
        return(res)


    @method_decorator(csrf_exempt)
    @require_mime('json')
    def update(self, request, role_id=None):
        try:
            r = request.data
            if not request.user.is_authenticated():
                res = rc.FORBIDDEN
                res.write(' request is not authenticated')
            elif not self.check_kbase_user( request.user.username):
                res = rc.FORBIDDEN
                res.write(' request not from a member of %s' % self.kbase_users)
            elif role_id == None:
                role_id = r['role_id']
            # If (add/del)member is among the URL variables, we are simply adding/deleting
            # "member" attribute to the existing one, ignore all other entries
            addmembers = 'addmembers' in request.GET
            delmembers = 'delmembers' in request.GET
            # If syncglobus is among the URL variables, then ignore everything else and
            # and synchronize the members field against the globus online group specified
            # in the role's globus_group field, all the normal restrictions apply for who can do it
            syncglobus = 'syncglobus' in request.GET
            if addmembers and delmembers:
                raise Exception('Cannot use addmembers and delmembers in single request')
            old = self.roles.find_one( { 'role_id': role_id })
            if old != None:
                if request.user.username == old['role_owner'] or request.user.username in old['role_updater'] :
                    # only allow the role_owner to be updated by the role_owner
                    if 'role_owner' in r and r['role_owner'] != old['role_owner'] and old['role_owner'] != request.user.username:
                        res = rc.FORBIDDEN
                        res.write( " %s role_owner can only be updated by %s, but request is from user %s" %
                                   (old['role_id'],old['role_owner'], request.user.username))
                    else:
                        # addmembers/delmembers coerces the members field into a set, so
                        # it is okay to have members as either a string or an array
                        if addmembers:
                            old['members'] = list( set( old['members']) | set(r['members']))
                        elif delmembers:
                            old['members'] = list( set(old['members']) - set(r['members']))
                        elif syncglobus:
                            if 'globus_group' not in old:
                                raise Exception( "Cannot use syncglobus operation when globus_group is not defined")
                            members = self.gclient.getGroupMembersByPath( old['globus_group'] ).keys()
                            old['members'] = list( set( old['members']) | set(members))
                        else:
                            validate(r,self.update_schema)
                            # Verify that the current user actually has privs to set ownership
                            # on documents at all
                            if r['owns'] != [] and not self.check_kbase_owners( request.user.username):
                                raise Exception( "You must be a member of the %s group in order to set ownership of documents" %
                                                 self.kbase_owners)
                            old.update(r)
                            self.dedupe(old)
                            self.ownership_legit(old, request.user.username)
                        self.roles.save( old)
                        res = rc.CREATED
                else:
                    res = rc.FORBIDDEN
                    res.write( " %s is owned by %s and updated by %s, but request is from user %s" %
                               (old['role_id'],old['role_owner'], pp.pformat(old['role_updater']),request.user.username))
            else:
                res = rc.NOT_HERE
        except KeyError as e:
            res = rc.BAD_REQUEST
            res.write(' required fields: %s' % e )
        except Exception as e:
            res = rc.BAD_REQUEST
            res.write(' error: %s' % e )
        return(res)

    def delete(self, request, role_id = None):
        try:
            if not request.user.is_authenticated():
                res = rc.FORBIDDEN
                res.write(' request is not authenticated')
            elif not self.check_kbase_user( request.user.username):
                res = rc.FORBIDDEN
                res.write(' request not from a member of %s' % self.kbase_users)
            elif role_id is None:
                raise KeyError('No role_id specified')
            else:
                old = self.roles.find_one( { 'role_id': role_id })
                if old != None:
                    if request.user.username == old['role_owner']:
                        self.roles.remove( { '_id' : old['_id'] }, safe=True)
                        res = rc.DELETED
                    else:
                        res = rc.FORBIDDEN
                        res.write( " %s is owned by %s, but request is from user %s" %
                                   (old['role_id'],old['role_owner'], request.user.username))
                else:
                    res = rc.NOT_HERE
        except KeyError as e:
            res = rc.BAD_REQUEST
            res.write(' role_id must be specified')
        except Exception as e:
            res = rc.BAD_REQUEST
            res.write(' error: %s' % e)
        return(res)



# Handlers for piston API
# sychan 9/6/2012

role_handler = Resource( RoleHandler)

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from django.conf import settings
from django.utils import unittest
from nexus import Client
from pymongo import Connection
from pymongo.read_preferences import ReadPreference
from authorization_server.handlers import RoleHandler
import pprint
import json
import os
import base64
import httplib2
import urllib
import time
import random
import string
import operator

# Function to grab a bearer token from Globus Online
# cribbed from Shreyas' cluster services module
#
def get_token(auth_svc, username, password):
    h = httplib2.Http(disable_ssl_certificate_validation=True)
    
    auth = base64.encodestring( username + ':' + password )
    headers = { 'Authorization' : 'Basic ' + auth }
    
    h.add_credentials(username, password)
    h.follow_all_redirects = True
    url = auth_svc
    
    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    if status>=200 and status<=299:
        tok = json.loads(content)
    else: 
        raise Exception(str(resp))
        
    return tok['access_token']

client = Client(config_file=os.path.join(os.path.dirname(__file__), '../nexus/nexus.yml'))
url = "https://%s/goauth/token?grant_type=client_credentials" % client.config['server']
papatoken = get_token( url, "papa","papapa")
kbusertoken = get_token( url, "kbasetest","@Suite525")
charset = string.ascii_uppercase + string.digits
pp = pprint.PrettyPrinter(indent=4)

# Pull in RoleHandler so we can call the dedupe function
rh = RoleHandler()

# flag for whether the mongodb instance is a slave instance
is_slave = None

class RoleHandlerTest(TestCase):
    """
    Unit Test of REST interface to make sure correct status codes are returned
    """

    def setUp(self):
        # TODO: Pull out all the common POST code into setup
        try:
            conn = Connection(settings.MONGODB_CONN, read_preference = ReadPreference.PRIMARY_PREFERRED,safe=True)
        except AttributeError as e:
            print "No connection settings specified: %s\n" % e
            conn = Connection(['mongodb.kbase.us'])
        except Exception as e:
            print "Generic exception %s: %s\n" % (type(e),e)
            conn = Connection(['mongodb.kbase.us'])
        global is_slave
        # If we're on a slave instance, set the is slave flag and then
        if not conn.is_primary:
            is_slave = not conn.is_primary
        db=conn.authorization
        self.roles = db.roles
        self.testdata = { "role_updater": ["sychan","kbauthorz"],
                          "description": "Steve's test role",
                          "read": [],
                          "create": True,
                          "modify": [],
                          "grant" : [],
                          "role_owner": "kbasetest",
                          "role_id": "unittest_",
                          "impersonate": [],
                          "members": ["sychan","kbasetest","kbauthorz"],
                          "delete": [],
                          "owns": [],
                          "globus_group": ""
                          }
        self.test_docid = "doc_" + "".join(random.sample(charset,10))
        # clear out any cruft from previous unittest runs
        if not is_slave:
            self.roles.remove( { 'role_id' : { '$regex' : 'unittest.*' } } )
        # insert a test record for unittesting
        testdata=dict(self.testdata)
        testdata['role_id'] += "".join(random.sample(charset,10))
        self.test_role_id = testdata['role_id']
        testdata['read'] = [self.test_docid]
        testdata['delete'] = [self.test_docid]
        testdata['modify'] = [self.test_docid]
        testdata['create'] = [self.test_docid]
        testdata['owns'] = [self.test_docid]
        if not is_slave:
            self.roles.insert( testdata)

    def tearDown(self):
        # clear out any cruft from current unittest run
        if not is_slave:
            self.roles.remove( { 'role_id' : { '$regex' : 'unittest.*' } } )

    def testCreate(self):
        if is_slave:
            raise unittest.SkipTest("MongoDB db is a slave instance, cannot test creation")
        h = self.client
        url = "/Roles/"
        authstatus = "/authstatus/"
        testdata = dict(self.testdata)
        testdata['role_id'] += "".join(random.sample(charset,10))
        id = testdata['role_id']

        testdata2 = dict(self.testdata)
        testdata2['role_id'] += "".join(random.sample(charset,10))

        testdata3 = dict(self.testdata)
        testdata3['role_id'] += "".join(random.sample(charset,10))

        dbobj = self.roles.find( { 'role_id' : testdata['role_id'] } );
        if dbobj.count() != 0:
            self.roles.remove( { 'role_id' : testdata['role_id'] } )

        dbobj = self.roles.find( { 'role_id' : testdata2['role_id'] } );
        if dbobj.count() != 0:
            self.roles.remove( { 'role_id' : testdata2['role_id'] } )

        dbobj = self.roles.find( { 'role_id' : testdata3['role_id'] } );
        if dbobj.count() != 0:
            self.roles.remove( { 'role_id' : testdata3['role_id'] } )

        data = json.dumps(testdata )

        resp = h.post(url, data, content_type="application/json" )

        self.assertEqual(resp.status_code, 401, "Should reject create without auth token")

        if hasattr(settings, 'REQUIRE_KBASE_USERS') and settings.REQUIRE_KBASE_USERS:
            resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % papatoken, content_type="application/json" )
            self.assertEqual(resp.status_code, 401, "Should reject create without KBase membership")

        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )

        #print pprint.pformat( data)
        #print pprint.pformat( resp.status_code)
        #print pprint.pformat( resp.content)
        self.assertEqual(resp.status_code, 201, "Should accept creation from legit kbase test user")
        # verify that object was inserted into database properly
        dbobj = self.roles.find( { 'role_id' : testdata['role_id'] } );
        self.assertEqual( dbobj.count(), 1, "Should be only a single instance of %s role" % testdata['role_id'])
        testdatadb = dbobj[0];
        del testdatadb['_id']
        # Now we have to convert this to unicode by doing a JSON conversion and then back
        testdata = json.loads(json.dumps( testdata))
        rh.dedupe( testdata)
        rh.dedupe( testdatadb)
        #print "testdata = %s" % pp.pformat( testdata)
        #print "testdatadb = %s" % pp.pformat( testdatadb)
        self.assertTrue( testdata == testdatadb,"Data in mongodb should equal source testdata - minus _id field")
        data = json.dumps(testdata )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 409, "Should reject creation of duplicate role_id")

        # strip out the role_id field to to force validation error
        del testdata['role_id']
        data = json.dumps(testdata )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 400, "Should refuse creation")
        self.assertTrue(resp.content.count('role_id') >= 1, "Should call out role_id as missing field")

        # try a duplicate role_id to force error
        testdata['role_id'] = id
        data = json.dumps(testdata )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 409, "Should refuse creation")

        # strip out the description field to to force validation error
        testdata['role_id'] += "".join(random.sample(charset,10))
        del testdata['description']
        data = json.dumps(testdata )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 400, "Should refuse creation")
        self.assertTrue(resp.content.count('description') >= 1, "Should call out description as missing field")

        # try to insert a role without ownership of the documents
        testdata2['read'] = [ "doc_" + "".join(random.sample(charset,10))]
        data = json.dumps(testdata2 )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 400, "Should refuse creation")
        self.assertTrue(resp.content.count('ownership privileges') >= 1, "Should call out ownership privilege issue")

        # add an owns clause and retry
        testdata2['owns'] = testdata2['read']
        data = json.dumps(testdata2 )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 201, "Should allow creation with owns clause")

        # One more role that references docs with immediate and external owns clauses
        testdata3['owns'] = [ "doc_" + "".join(random.sample(charset,10))]
        testdata3['read'] = testdata2['owns']
        testdata3['delete'] = testdata2['owns'] + testdata3['owns']
        data = json.dumps(testdata3 )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 201, "Should allow creation with immediate and external owns clauses")

        # try to add one more role that claims ownership of a doc that is already owned
        testdata4 = dict(self.testdata)
        testdata4['role_id'] += "".join(random.sample(charset,10))
        testdata4['owns'] = testdata3['owns']
        data = json.dumps(testdata4 )
        resp = h.post(url, data, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken, content_type="application/json" )
        self.assertEqual(resp.status_code, 400, "Should deny creation of role that re-owns a document")
        self.assertTrue(resp.content.count('already have owners') >= 1, "Should call out existing owners")

        # Remove the database record directly
        self.roles.remove( { 'role_id' : id } )
        self.roles.remove( { 'role_id' : testdata2['role_id'] } )
        self.roles.remove( { 'role_id' : testdata3['role_id'] } )

    def testRead(self):
        h = self.client
        url = "/Roles/"

        resp = h.get(url)
        self.assertEqual(resp.status_code, 401, "Should reject queries without auth token")

        if hasattr( settings, 'REQUIRE_KBASE_USERS') and settings.REQUIRE_KBASE_USERS:
            resp = h.get(url, {}, HTTP_AUTHORIZATION="OAuth %s" % papatoken)
            self.assertEqual(resp.status_code, 401, "Should reject queries without KBase membership")

        resp = h.get(url+"?about", {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Should accept queries from legit kbase test user")
        respjson = json.loads(resp.content)
        usage = respjson[0].get('usage')
        self.assertIsNotNone(usage, "Expecting usage message")

        resp = h.get(url, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        #print "Response from query was: %s %s" % (resp.status_code, resp.content)
        self.assertEqual(resp.status_code, 200, "Should accept queries from legit kbase test user")
        respjson = json.loads(resp.content)
        self.assertIn("kbase_users",respjson, "Expecting usage message")

        url2 = "%skbase_users" % url
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying for kbase_user role from legit kbase test user")
        respjson = json.loads(resp.content)
        members = respjson[0].get('members')
        self.assertIsNotNone(members, "Expecting members field")

        url2 = "%s?role_id=kbase_users" % url
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying for kbase_user role from legit kbase test user using GET param")
        respjson = json.loads(resp.content)
        members = respjson[0].get('members')
        self.assertIsNotNone(members, "Expecting members field")

        # try to query long random role name, expecting no result!
        bogorole = "".join(random.sample(charset,20))
        url2 = "%s%s" % (url,bogorole)
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying for nonexistent role using kbase test user")
        respjson = json.loads(resp.content)
        self.assertTrue(len(respjson)==0, "Expecting no response")

        # try a regex filter search for all possible role_ids
        filter = { "role_id" : { "$regex" : ".*" }}
        filterjs = json.dumps( filter )
        url2 = "%s?filter=%s" % (url,filterjs)
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying using regex filter")
        respjson = json.loads(resp.content)
        self.assertTrue(len(respjson) > 0, "Expecting multiple responses")
        fields = list(set(reduce( operator.add,[respjson[x].keys() for x in range(len(respjson))],[] )))
        self.assertTrue( len(fields) > 1, "Expecting a multiple fields in results set")

        # try a regex filter search for all possible role_ids, but returning only one field
        filter = { "role_id" : { "$regex" : ".*" }}
        filterjs = json.dumps( filter )
        fields = { "role_id" : "1", "_id" : "1" }
        fieldsjs = json.dumps( fields )
        url2 = "%s?filter=%s&fields=%s" % (url,filterjs,fieldsjs)
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying using regex filter and field selection")
        respjson = json.loads(resp.content)
        self.assertTrue(len(respjson) > 0, "Expecting multiple responses")
        fields = list(set(reduce( operator.add,[respjson[x].keys() for x in range(len(respjson))],[] )))
        self.assertEquals( fields,['_id','role_id'], "Expecting two fields, ['_id','role_id'], across all results")

        # double check by pulling all records from mongodb and making sure the role_id values match
        role_ids = [x['role_id'] for x in respjson]
        role_ids.sort()
        dbroles = self.roles.find( filter, fields)
        role_idsdb = [x['role_id'] for x in dbroles]
        role_idsdb.sort()
        self.assertEquals( role_ids, role_idsdb, "Should get identical results from pymongo query and REST interface query")

        # Perform query using the user_id param and verify against mongodb
        url2 = "%s?user_id=kbasetest" % url
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying for roles with user_id=kbasetest using GET param")
        respjson = json.loads(resp.content)
        role_ids = [x['role_id'] for x in respjson]
        role_ids.sort()
        filter = { 'members' : 'kbasetest' }
        fields = { 'role_id' : 1 }
        dbroles = self.roles.find( filter, fields)
        role_idsdb = [x['role_id'] for x in dbroles]
        role_idsdb.sort()
        self.assertEquals( role_ids, role_idsdb, "Should get identical results from pymongo query and user_id=kbasetest query")

        # Perform query using the doc_id param and verify against sample doc_id
        # skip if we are on a slave mongodb
        if not is_slave:
            url2 = "%s?doc_id=%s" % (url,self.test_docid)
            resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
            self.assertEqual(resp.status_code, 200, "Querying for roles with doc_id=%s using GET param" % self.test_docid)
            respjson = json.loads(resp.content)
            self.assertTrue( len(respjson) == 1, "Should get single result matching random doc_id from test suite")
            self.assertEquals( respjson[0]['role_id'], self.test_role_id, "Should get matching role_ids for doc_id query")

        # Perform query using the union and user_id parameters and verify against mongodb
        url2 = "%s?user_id=kbasetest&union=" % url
        resp = h.get(url2, {}, HTTP_AUTHORIZATION="OAuth %s" % kbusertoken)
        self.assertEqual(resp.status_code, 200, "Querying for roles with user_id=kbasetest using GET param")
        respjson = json.loads(resp.content)
        self.assertEquals( len(respjson), 1, "Should be only a single result from union query")
        role_ids = set(respjson[0]['role_id'].split(','))
        filter = { 'members' : 'kbasetest' }
        dbroles = list(self.roles.find( filter))
        # Compare results - check the role_ids and then the contents
        role_idsdb = set([x['role_id'] for x in dbroles])
        self.assertTrue( role_ids == role_idsdb, "Should get identical role_ids from pymongo and user_id=kbasetest&union=query")
        merged=dict()
        for acls in ('grant','read','modify','delete','owns','members'):
            merged[acls] = reduce( set.union, [ set(x.get(acls,[])) for x in dbroles])
            self.assertTrue( merged[acls] == set(respjson[0][acls]), "Should get identical %s ACL from pymongo and user_id=kbasetest&union= query" % acls)

    def testUpdate(self):
        if is_slave:
            raise unittest.SkipTest("MongoDB db is a slave instance, cannot test updates")
        h = self.client
        url = "/Roles/"

        # Push a record into the mongodb directly so that we can modify it
        testdata = dict(self.testdata)
        testdata['role_id'] += "".join(random.sample(charset,10))
        testdata['role_owner'] = "sychan"
        self.roles.insert(testdata)
        # create a copy of the testdata
        testdata2 = dict(testdata)
        id = testdata2['_id']
        del testdata2['_id']
        jdata = json.dumps( testdata2)

        url_roleid = "%s%s" % (url,testdata2['role_id'])

        # try without auth, should fail
        resp = h.put( url_roleid, jdata, content_type="application/json")
        #print "resp.status_code = %s" % pp.pformat( resp.status_code)
        #print "resp.content = %s" % pp.pformat( resp.content)
        self.assertEqual(resp.status_code, 401, "Should reject update without auth token")

        # try with non kbase auth, should fail
        resp = h.put( url_roleid, jdata, content_type="application/json",
                      HTTP_AUTHORIZATION = "OAuth %s" % papatoken )
        self.assertEqual(resp.status_code, 401, "Should reject update with non kbase user")

        # try with kbasetest user, should fail because not in updaters
        resp = h.put( url_roleid, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 401, "Should reject update from wrong user")


        # try with kbasetest user, but bogus role_id, should fail
        resp = h.put( url_roleid + "_blabla", jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 410, "Should reject update to bogus role_id")

        # add kbasetest to the updaters so that we can change things
        testdata['role_updater'].append("kbasetest");
        testdata['_id'] = id
        self.roles.save( testdata)
        #print pprint.pformat( testdata)
        testdata2 = dict(testdata)
        del testdata2['_id']
        testdata2['description'] = "New test role description"
        testdata2['read'] = ['bugsbunny','roadrunner']
        jdata = json.dumps( testdata2)

        # try again, should deny update because of ownership
        resp = h.put( url_roleid, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        #print pprint.pformat( url_roleid)
        #print pprint.pformat( jdata)
        #print pprint.pformat( resp.status_code)
        #print pprint.pformat( resp.content)
        self.assertEqual(resp.status_code, 400, "Should deny update")

        # try again, set ownership which should allow update
        testdata_no_own = dict( testdata2)
        testdata2['owns'] = ['bugsbunny','roadrunner']
        jdata = json.dumps( testdata2)
        resp = h.put( url_roleid, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        #print pprint.pformat( resp.status_code)
        #print pprint.pformat( resp.content)
        self.assertEqual(resp.status_code, 201, "Should allow update")


        # try again but try to reset role_owner, should deny update
        testdata3 = dict(testdata2)
        testdata3['role_owner'] = "bugsbunny"
        # clear the ownership assertion
        testdata3['owns'] = []
        jdata3 = json.dumps(testdata3)
        resp = h.put( url_roleid, jdata3, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 401, "Should deny update of role_owner by non-owner")

        # pull record from the DB and make sure it is identical to what
        # we sent
        dbobj = self.roles.find( { 'role_id' : testdata2['role_id'] })
        self.assertEqual( dbobj.count(), 1, "Should be only a single instance of %s role" % testdata2['role_id'])
        testdatadb = dbobj[0];
        del testdatadb['_id']
        # Now we have to convert this to unicode by doing a JSON conversion and then back
        testdata2 = json.loads(json.dumps( testdata2))
        rh.dedupe( testdatadb)
        rh.dedupe( testdata2)
        self.assertTrue( testdata2 == testdatadb,"Data in mongodb should equal source testdata - minus _id field")

        # try one more no op update, but the role_id is from the message body
        jdata = json.dumps( testdata_no_own)
        resp = h.put( url, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 201, "Should accept update")

        # try one more no op update, but with no role_id specified
        role_id = testdata2['role_id']
        del testdata2['role_id']
        jdata = json.dumps( testdata2)
        resp = h.put( url, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 400, "Should decline update without role_id")

        # test out the addmember and delmember functions
        url2 = "%s?addmembers=" % url
        jdata = json.dumps( { 'role_id' : role_id,
                              'members' : [ 'captainkirk', 'tweetybird']})
        resp = h.put( url2, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        #print resp.content
        self.assertEqual(resp.status_code, 201, "Should accept addmembers")

        # test out the addmember and delmember functions
        url2 = "%s?delmembers=" % url
        resp = h.put( url2, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        #print resp.content
        self.assertEqual(resp.status_code, 201, "Should accept delmembers")

        # test out the addmember and delmember functions
        url2 = "%s?delmembers=&addmembers=" % url
        resp = h.put( url2, jdata, content_type="application/json",
                     HTTP_AUTHORIZATION = "OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 400, "Should reject simultaneous addmembers and delmembers")
        self.assertTrue(resp.content.count('addmembers and delmembers') >= 1, "Should call out conflicting options")

        self.roles.remove( { '_id' : id }, safe=True)
        
    def testDelete(self):
        if is_slave:
            raise unittest.SkipTest("MongoDB db is a slave instance, cannot test deletion")
        h = self.client
        url = "/Roles/"
        testdata = dict(self.testdata)
        testdata['role_id'] += "".join(random.sample(charset,10))
        # insert the testdata
        testdata['role_owner'] = "kbasetest"
        self.roles.insert( testdata)

        url = "%s%s" % (url, testdata['role_id'])
        resp = h.delete( url)
        self.assertEqual(resp.status_code, 401, "Should reject delete without auth token")

        resp = h.delete( url,{},HTTP_AUTHORIZATION="OAuth %s" % papatoken )
        self.assertEqual(resp.status_code, 401, "Should reject for non kbase user")

        resp = h.delete( '/Roles/',{},HTTP_AUTHORIZATION="OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 400, "Should reject delete without role_id")

        resp = h.delete( "%s%s" % (url,"_blahblah"),{},HTTP_AUTHORIZATION="OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 410, "Should reject delete for nonexistent role_id")

        resp = h.delete( url,{},HTTP_AUTHORIZATION="OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 204, "Should allow delete with kbasetest auth token")

        testdata['role_owner'] = "elmerfudd"
        self.roles.insert( testdata)
        resp = h.delete( url,{},HTTP_AUTHORIZATION="OAuth %s" % kbusertoken )
        self.assertEqual(resp.status_code, 401, "Should reject delete with kbasetest auth token")

        # Remove the database record directly
        self.roles.remove( { 'role_id' : testdata['role_id'] } )




import httplib2
import json
from nexus.go_rest_client import GlobusOnlineRestClient
import time
import logging
from pymongo import Connection

try:
    from django.conf import settings
except:
    pass

class GlobusGroupsSync:
    """
    Class to support automatic synchronization of members in KBase authorization
    groups against Globus Online group members

    Steve Chan
    sychan@lbl.gov

    """
    try:
        GlobusBaseURL =  settings.GLOBUSBASEURL
    except:
        GlobusBaseURL =  "nexus.api.globusonline.org"
    try:
        GlobusUser = settings.GLOBUSUSER
    except:
        GlobusUser = 'kbasetest'
    try:
        GlobusPassword = settings.GLOBUSPASSWORD
    except:
        GlobusPassword = "@Suite525"
    # This group ID should be the root group for kbase, "kbase_users". All KBase groups
    # should be children of this group
    try:
        RootGID = settings.ROOTGID
    except:
        RootGID = '99d2a548-7218-11e2-adc0-12313d2d6e7f'
    # This is the number of seconds that the group dict instance var can linger before
    # it needs to be updated
    try:
        GroupCacheTTL = settings.GROUPCACHETTL
    except:
        GroupCacheTTL = 60

    # We need to define the appropriate settings and set them here
    try:
        conn = Connection(settings.MONGODB_CONN)
    except AttributeError as e:
        print "No connection settings specified: %s\nConnection to mongodb.kbase.us by default." % e
        conn = Connection(['mongodb.kbase.us'])
    except Exception as e:
        print "Generic exception %s: %s\nConnection to mongodb.kbase.us by default" % (type(e),e)
        conn = Connection(['mongodb.kbase.us'])
    db = conn.authorization
    roles = db.roles

    def __init__(self):
        try:
            self.GlobusClient = GlobusOnlineRestClient( go_host = self.GlobusBaseURL,
                                                        username = self.GlobusUser, password = self.GlobusPassword)
            resHeader,self.RootGroup = self.GlobusClient._issue_rest_request('/groups/%s/tree' % self.RootGID)
            if resHeader.status != 200:
                raise Exception( "Failed to fetch KBase root group %s from Globus Online response code %s" %
                                 ( rootGID, resHeader.status))
            else:
                self.URL = '/groups/%s' % self.RootGID # shortcut for baseURL
            # cached dictionary of groupnames to group IDs, and the timestamp for the cache
            self.GroupDict = dict()
            self.GroupTree = {}
            self.GroupCacheTime = 0
            self.getGroupList()

        except Exception, e:
            logging.exception("Error initializing globus client: %s" % e)
            raise

    # Traverse the groups tree and return a flattened dictionary of id : name
    # for all entries in the tree
    def walkGroupsTree( self, tree, path = ''):
        res = { path + '/' + tree['name'] : tree['id'] }
        if 'children' in tree:
            for child in tree['children']:
                res.update( self.walkGroupsTree( child, path + '/' + tree['name']))
        return res
    
    # Return a dictionary of group names : group ids, and the full groups
    # tree from GO
    def getGroupList(self):
        try:
            resHeader,list = self.GlobusClient._issue_rest_request('%s/tree?depth=20' % self.URL)
            if resHeader.status != 200:
                raise Exception( "Could not fetch members of GID %s http response code %s", gid, resHeader.status)
            groupDict = self.walkGroupsTree( list)
            self.GroupDict = groupDict
            self.GroupTree = list
            self.GroupCacheTime = time.time()
        except Exception, e:
            logging.exception("Error fetching group list: %s" % e)
            raise
        return(groupDict, list)

    # Return a dict of active group members username : role where role can be "member"
    # or "manager" or "admin". Input is the group id
    def getGroupMembersByGID(self, gid):
        try:
            resHeader,content = self.GlobusClient._issue_rest_request('/groups/%s/members' % gid)
            if resHeader.status != 200:
                raise Exception( "Could not fetch members of GID %s http response code %s", gid, resHeader.status)
            members = { u['username'] : u['role'] for u in content['members'] if u['status'] == 'active'}
        except Exception, e:
            raise
        return( members)

    # Return a dict of active group members username : role where role can be "member"
    # or "manager" or "admin". Input is the group id
    def getGroupMembersByPath(self, path):
        try:
            if time.time() >= self.GroupCacheTime + self.GroupCacheTTL:
                self.getGroupList()
            if path not in self.GroupDict:
                raise Exception( "Path %s not found among KBase groups" % path)
        except Exception, e:
            raise
        return( self.getGroupMembersByGID( self.GroupDict[path]))

    # Update a MongoDB group with the members from a GO group
    def syncGOGroup2KBaseGroup( self, GOGroupPath, KBGroupName):
        try:
            GOMembers = self.getGroupMembersByPath( GOGroupPath )
        except:
            raise
        try:
            filter = { 'role_id' : KBGroupName }
            kbGroup = self.roles.find_one( filter )
            if kbGroup is not None:
                kbGroup['members'] = GOMembers.keys()
                self.roles.save( kbGroup )
            else: # new group
                raise Exception( "KBase group %s does not exist" % GOGroupPath)
        except:
            raise
        return self

    # Update a MongoDB group by appending members from a GO group
    def appendGOGroup2KBaseGroup( self, GOGroupPath, KBGroupName):
        try:
            GOMembers = self.getGroupMembersByPath( GOGroupPath )
        except:
            raise
        try:
            filter = { 'role_id' : KBGroupName }
            kbGroup = self.roles.find_one( filter )
            if kbGroup is not None:
                kbGroup['members'] = list( set( kbGroup['members']) | set(GOMembers.keys()))
                self.roles.save( kbGroup )
            else: # new group
                raise Exception( "KBase group %s does not exist" % GOGroupPath)
        except:
            raise
        return self

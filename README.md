### Dependencies

* External Package

* Required Python libs (install using easy_install or pip)

    * certifi==0.0.8
    * chardet==1.0.1
    * distribute==0.6.24
    * oauthlib==0.1.3
    * pyasn1==0.1.3
    * requests==0.13.0
    * rsa==3.0.1
    * pyyaml==3.10
    * httplib2==0.7.1
    * oauth2==1.5.167
    * pymongo==2.3
    * django==1.4.1
    * django_piston==0.2.2

* Ports that need to be open

### Google Doc for API

   The initial documentation for the authorization service is here:

https://docs.google.com/document/d/1CTkthDUPwNzMF22maLyNIktI1sHdWPwtd3lJk0aFb20/edit

   Going to http://{authorization.host}/Roles?about will being up a JSON document that
gives a description of the service.
   The file authorization_service/authorization_service/handlers.py implements the
REST service, and had a largish comment at the top explaining how it works.
   Unittests for the authz service have been implemented using the Django unittest
framework, so they can be run with "manage.py test authorization_server"

### Setup using the kbase VMs
=======
0.  Start the VM and clone the git repo.
    nova boot .... (options will change over time)
    ssh ubuntu@<vm host>

1. Following an updated version of the directions
   from: https://trac.kbase.us/projects/kbase/wiki/IntegrationTargets
   sudo bash
   cd /kb
   git clone kbase@git.kbase.us:/dev_container.git
   cd dev_container/modules
   git clone kbase@git.kbase.us:/auth_service.git
   cd ..
   ./bootstrap /kb/runtime
   . user-env.sh

2. To configure the mongodb instance used to back the authorization service, create a
   file named local_settings.py in
   /kb/dev_container/modules/auth_service/authorization_server/authorization_server
   If there is no local_settings file the service will default to the instance on mongodb.kbase.us,
   however you will also need to set a salt value for the KBase session service, used to
calculate a unique hash value for the session ID.
   Here are recommended settings to put in the local_settings.py file:
KBASE_SESSION_SALT = "(African || European)?"

   If you want to use your own mongodb service running on localhost, you would add
an extra setting:
MONGODB_CONN = ['127.0.0.1:27017']

3. The make target deploy-services will install and configure the authorization service
   cd modules/auth_service
   make deploy-services

4. Run the internal unit tests
   make test   

5. If necessary, you can load the base/bootstrap authorization roles by using the "load-mongodb" target to initialize the mongodb service with a bare minimum set of roles. This is not necessary when working with the mongodb.kbase.us service.
   make load-mongodb

6. The django server is started/stopped by using the start_service and stop_service
scripts in /kb/deployment/services/authorization. Once you start the service, there
will be a listener at http://hostname:7039/ with the authorization service responding
under the /Roles/ url. You will need to access it with a KBase token to get any
real data back:

root@sychan-temp2:/kb/deployment/services/authorization_server# ./start_service 
root@sychan-temp2:/kb/deployment/services/authorization_server# curl http://localhost:7039/Roles
Forbidden request not from a member of kbase_users

   See the file README_authenticated_requests.txt for an example of querying the
service from the command line using a test account

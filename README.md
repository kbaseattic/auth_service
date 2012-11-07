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

   The original design documentation for the authorization service is here:

https://docs.google.com/document/d/1CTkthDUPwNzMF22maLyNIktI1sHdWPwtd3lJk0aFb20/edit

   The documentation for the actual implementation is here:
https://docs.google.com/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/edit

   Going to http://{authorization.host}/Roles?about will being up a JSON document that
gives a description of the service.
   The file authorization_service/authorization_service/handlers.py implements the
REST service, and had a largish comment at the top explaining how it works.
   Unittests for the authz service have been implemented using the Django unittest
framework, they are available in the Makefile target "test", so they can be run
by "make test" or you can go to the django site root and run it directly using
"manage.py test authorization_server"

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
   However you will also need to set a salt value for the KBase session service, used to
calculate a unique hash value for the session ID.
   There is also a PROXY_BASEURL setting that defines the entry URL that used to access this
django service. This is necessary to generate self-referring URL's when the front end
NGINX proxy is in operation - it needs to be disabled for local testing/development

   Here are recommended settings to put in the local_settings.py file:
KBASE_SESSION_SALT = "(African || European)?"
PROXY_BASEURL =	   None

   If you want to use your own mongodb service running on localhost, you would add
an extra setting:
MONGODB_CONN = ['127.0.0.1:27017']

3. The make target deploy-services will install and configure the authorization service
with an FCGI listener on port 7039 ( for production deployment )
   cd modules/auth_service
   make deploy-services

   The make target deploy-test-services will install and configure the service with an
nginx http listener on port 7039 so that you can directly query the service for testing
   cd modules/auth_service
   make deploy-test-services

4. Run the internal unit tests
   make test   

5. If necessary, you can load the base/bootstrap authorization roles by using the "load-mongodb" target to initialize the mongodb service with a bare minimum set of roles. This is not necessary when working with the mongodb.kbase.us service.
   make load-mongodb

6. The django server is started/stopped by using the start_service and stop_service
scripts in /kb/deployment/services/authorization. Once you start the service, there
will be an FCGI listener at hostname:7039 with the authorization service responding
under the /Roles/ url. Use the deploy-test-services make target to get an http
listener on that port instance (assumed for the examples that follow).
    You will need to access it with a KBase token to get any
real data back:

root@sychan-temp2:/kb/deployment/services/authorization_server# ./start_service 
root@sychan-temp2:/kb/deployment/services/authorization_server# curl http://localhost:7039/Roles
Forbidden request not from a member of kbase_users

   See the file README_authenticated_requests.txt for an example of querying the
service from the command line using a test account

TOP_DIR = ../..
include $(TOP_DIR)/tools/Makefile.common

SRC_PERL = $(wildcard scripts/*.pl)
BIN_PERL = $(addprefix $(BIN_DIR)/,$(basename $(notdir $(SRC_PERL))))

DEPLOY_PERL = $(addprefix $(TARGET)/bin/,$(basename $(notdir $(SRC_PERL))))

TARGET ?= /kb/deployment
KB_PERL_PATH = $(TARGET)

SERVICE = authorization_server
SERVICE_DIR = $(TARGET)/services/$(SERVICE)
NGINX_CONF = /etc/nginx/conf.d/

# The Google Doc is at the URL https://docs.google.com/a/lbl.gov/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/edit#
# So you can derive the download URL by replacing the /edit portion with /export and then a format specifier
DOCURL := https://docs.google.com/a/lbl.gov/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/export?format=html

all:

deploy: deploy-services

deploy-nginx:
	cp nginx.conf $(NGINX_CONF)/$(SERVICE).conf ; \
	service nginx restart || echo "Already Up"

deploy-services:
	mkdir -p $(SERVICE_DIR) ; \
	rsync -avz --exclude .git --cvs-exclude authorization_server start_service stop_service django.conf var $(SERVICE_DIR) ; \
	cd $(SERVICE_DIR)/$(SERVICE);echo no|python ./manage.py syncdb ; \
	cd $(SERVICE_DIR); ./stop_service ; ./start_service


deploy-test-services: deploy-nginx
	mkdir -p $(SERVICE_DIR) ; \
	rsync -avz --exclude .git --cvs-exclude authorization_server start_service stop_service django-localhost.conf var $(SERVICE_DIR) ; \
	cd $(SERVICE_DIR)/$(SERVICE);echo no|python ./manage.py syncdb ; \
	cd $(SERVICE_DIR); cp django-localhost.conf django.conf ; \
	./stop_service ; sleep 5; ./start_service

deploy-docs:
	# create docs here in docs directory and deploy them if needed
	mkdir -p $(SERVICE_DIR)
	mkdir -p $(SERVICE_DIR)/webroot
	cp docs/*html $(SERVICE_DIR)/webroot/.

deploy-client:
	echo "No clients.  Use auth."

build-docs:
	curl -o docs/auth_service.html $(DOCURL)


build-docs:
	# The Google Doc is at the URL https://docs.google.com/a/lbl.gov/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/edit#
	# So you can derive the download URL by replacing the /edit portion with /export and then a format specifier
	URL=https://docs.google.com/a/lbl.gov/document/d/1-43UvESzSYtLInqOouBE1s97a6-cRuPghbNJopYeU5Y/export?format=html
	curl -o docs/auth_service.html $(URL)


.PHONY: test

test: test_django

test_django:
	cd authorization_server; \
	./manage.py test authorization_server

load-mongodb:
	mongorestore -h mongodb.kbase.us --db authorization data/Roles-bootstrap/authorization


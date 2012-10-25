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

all: deploy-services

deploy:

deploy-nginx:
	cp nginx.conf $(NGINX_CONF)/$(SERVICE).conf ; \
	service nginx restart || echo "Already Up"

deploy-services: deploy-nginx
	mkdir -p $(SERVICE_DIR) ; \
	rsync -avz --exclude .git --cvs-exclude authorization_server start_service stop_service django.conf var $(SERVICE_DIR) ; \
	cd $(SERVICE_DIR)/$(SERVICE);echo no|python ./manage.py syncdb

load-mongodb:
	mongorestore -h mongodb.kbase.us --db authorization data/Roles-bootstrap/authorization


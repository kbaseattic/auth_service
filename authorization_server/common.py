"""
Module for code/data shared across django applications. Currently it includes the configs that are
to be read from the INI files.

The code that connections to mongodb should be migrated into here as well in a future refactor.

"""
from ConfigParser import ConfigParser
import os
from pprint import pformat

kb_config = os.environ.get('KB_DEPLOYMENT_CONFIG',os.environ['HOME']+"/.kbase_config")

# authdata stores the configuration key/values from any configuration file
auth_data = dict()

def LoadConfig():
    """
    Method to load configuration from INI style files from the file in kb_config
    """
    global auth_data

    kb_config = os.environ.get('KB_DEPLOYMENT_CONFIG',os.environ['HOME']+"/.kbase_config")

    if os.path.exists( kb_config):
        try:
            conf = ConfigParser()
            conf.read(kb_config)
            if conf.has_section('auth_service'):
                auth_data = { n : v  for n,v in conf.items('auth_service') }
        except Exception, e:
            print "Error while reading INI file %s: %s" % (kb_config, e)

LoadConfig()

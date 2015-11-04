# -*- coding: utf-8 -*-
"""
Created on Fri Oct 30 16:24:10 2015

@author: mints
"""
import os
import sys
from os import path
NAME = '%s/..' % path.dirname(__file__)
sys.path.insert(0, path.abspath(NAME))

import cherrypy
from lib.password_manager import PasswordManager
from lib.utils import ensure_dir, silentremove, verify
from server.icfrunner import ICFRunner
from glob import glob
from astropy import log
from cherrypy._cpcompat import random20
import time
from httplib import responses


LOCAL = '127.0.0.1:8001'

def error_page_404(status, message, traceback, version):
    return "Error %s - Page does not exist yet. It might appear later!" % status
cherrypy.config.update({'error_page.404': error_page_404})


class HelloWorld(object):

    def __init__(self):
        self.passwords = PasswordManager()
        self.runner = ICFRunner('xmatch')
        self.runner.override = True
        self.current_user = None
    
    @cherrypy.expose
    def index(self):
        return 'Duba-diba-du'

if __name__ == '__main__':
    cherrypy.quickstart(HelloWorld())

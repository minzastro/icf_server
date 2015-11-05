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
from server.globals import JINJA
from server.iidmanager import IIDmanager
from cherrypy.lib.reprconf import Config

LOCAL = '127.0.0.1:8001'
SESSION_KEY = '_cp_username'

def error_page_404(status, message, traceback, version):
    return "Error %s - Page does not exist yet. It might appear later!" % status
    
cherrypy.config.update({'error_page.404': error_page_404})
    
class ICFServer(object):

    def __init__(self):
        self.passwords = PasswordManager()
        self.runner = ICFRunner('xmatch')
        self.runner.override = True
        self.current_user = None
        self.config = Config('icfcherry.conf')
        self.iidmanager = IIDmanager(self)
    
    def check_auth(self):
        if self.current_user is None:
            raise cherrypy.HTTPRedirect('/pages/login_form.html')

    def start(self):
        cherrypy.config.update(self.config)
        cherrypy.tree.mount(self, '/', config = self.config)
        cherrypy.tree.mount(self.iidmanager, '/iid', config=self.config)
        cherrypy.engine.start()
        cherrypy.engine.block()
    
    def default(self):
        template = JINJA.get_template('root.template')
        return template.render({'username': self.current_user})

    @cherrypy.expose
    def index(self):
        if self.current_user is None:
            raise cherrypy.HTTPRedirect('/pages/login_form.html')
        else:
            return self.default()

    @cherrypy.expose
    def login(self, username=None, password=None):
        if username is None or password is None:
            raise cherrypy.HTTPRedirect('/pages/login_form.html')
        login_result = self.passwords.verify_password(username, password)
        if login_result == self.passwords.PASSWORD_FAILED:
            raise cherrypy.HTTPError(401, "Password failed!")
        elif login_result == self.passwords.USER_NOT_EXISTS:
            raise cherrypy.HTTPError(401, "User does not exist!")        
        else:
            self.current_user = username
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            raise cherrypy.HTTPRedirect("/")
    
    @cherrypy.expose
    def logout(self):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.current_user = None
        raise cherrypy.HTTPRedirect("/")


if __name__ == '__main__':
    #cherrypy.quickstart(ICFServer(), config='icfcherry.conf')
    server = ICFServer()
    server.start()

# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 16:20:53 2015

@author: mints
"""

from server.globals import JINJA
from cherrypy import expose
import cherrypy

class IIDmanager(object):
    def __init__(self, parent):
        self.parent = parent
    
    @expose
    def new_iid(self):
        self.parent.check_auth()
        template = JINJA.get_template('new_iid.template')
        return template.render({'username': self.parent.current_user})
        
    @expose
    def create_new_iid(self, iid, ra, de):
        self.parent.check_auth()
        self.parent.runner.create_iid(self.current_user, iid, ra, de)
        raise cherrypy.HTTPRedirect("/")
    
    @expose
    def restricted(self):
        self.parent.check_auth()
        return 'Tralala'


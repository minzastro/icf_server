# -*- coding: utf-8 -*-
"""
Created on Wed Nov  4 16:20:53 2015

@author: mints
"""

from server.globals import JINJA
from cherrypy import expose
import cherrypy
from server.prettiesttable import from_db_cursor

class IIDmanager(object):
    def __init__(self, parent):
        self.parent = parent
    
    def get_cursor(self, sql):
        return self.parent.runner.conn.get_cursor(sql)
        
    @expose
    def new_iid(self):
        self.parent.check_auth()
        template = JINJA.get_template('new_iid.template')
        return template.render(self.parent.get_basic())
        
    @expose
    def create_new_iid(self, iid, ra, de):
        self.parent.check_auth()
        self.parent.runner.create_iid(self.parent.current_user, iid, ra, de)
        raise cherrypy.HTTPRedirect("%s/iid/list_iids" % self.parent.ROOT)
    
    @expose
    def restricted(self):
        self.parent.check_auth()
        return 'Tralala'

    @expose
    def list_iids(self):
        self.parent.check_auth()
        template = JINJA.get_template('list_iids.template')
        table = from_db_cursor(self.get_cursor("""select local_iid as iid, ra, decl, 
                                                         string_agg(fs.set_id, ',') as sets,
                                                         string_agg(fp.catalog || '(' || cast(fp.objects_count as character varying) || ')', ',') as catalogs                                                         
                                                    from fields f 
                                                    left outer join fields_properties fp on fp.iid = f.iid
                                                    left outer join field_sets fs on fs.iid = f.iid
                                                   where user_id = '%s' 
                                                  group by 1,2,3
                                                  order by 2
                                                    """ % self.parent.current_user))
        data = self.parent.get_basic()
        data['iid_list'] = table.get_html_string(attributes={'border': 1,
                                                             'id': 'iid_table'})
        return template.render(data)

    @expose
    def crawl(self, **params):
        self.parent.check_auth()
        print params
        iids = params['iids[]']
        if isinstance(iids, basestring):
            iids = [iids]
        self.parent.runner.set_catalog(params['catalog'])
        for iid in iids:
            self.parent.runner.crawl(self.parent.current_user, int(iid))
        #global_iid = self.parent.runner.get_global_iid(self.parent.current_user, iid)
        #cur = self.get_cursor("select count(*) from data_xmatch where iid = %s" % global_iid)
        return None #str(cur.fetchall())
    
    @expose
    def run_icf(self, **params):
        self.parent.check_auth()
        print params
        iids = params['iids[]']
        if isinstance(iids, basestring):
            iids = [iids]
        self.parent.runner.set_catalog(params['catalog'])
        for iid in iids:
            self.parent.runner.run_icf(self.parent.current_user, int(iid))
        #global_iid = self.parent.runner.get_global_iid(self.parent.current_user, iid)
        #cur = self.get_cursor("select count(*) from data_xmatch where iid = %s" % global_iid)
        return None #str(cur.fetchall())
    
    @expose
    def single_iid(self, iid):
        self.parent.check_auth()
        global_iid = self.parent.runner.get_global_iid(self.parent.current_user, iid)
        cur = self.get_cursor("""select catalog, objects_count, peaks_count, loading_date
                                   from fields_properties
                                  where iid = %s""" % global_iid)
        data = self.parent.get_basic()
        data.update({'catalogs': [], 
                     'iid': iid})
        for row in cur.fetchall():
            data['catalogs'].append({'name': row[0],
                                     'objects_count': row[1],
                                     'peaks_count': row[2],
                                     'loading_date': row[3]})
        detections = from_db_cursor(self.get_cursor("""
            select detection_id, z, z_err, lambda, bcg_distance 
              from cluster_detections
             where iid = %s""" % global_iid))
        data['detections'] = detections.get_html_string()
        template = JINJA.get_template('single_iid.template')
        return template.render(data)
        

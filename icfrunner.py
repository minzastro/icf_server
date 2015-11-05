#!/usr/bin/python
"""
Created on Thu May 15 12:43:41 2014
@author: mints
"""
from lib.sqlconnection import SQLConnection
import logging
from lib.sql2file import sql_to_file
from lib.utils import to_str, get_logger
from os import path, unlink
import lib.sqllist as sqllist
from rs.dataloader import DataLoader
from lib.selector import get_catalog_and_finder


DEFAULT_SUFFIX = {
    'allwise': 'boss',
    'sdss': 'iterate',
    'cfhtls': 'model62',
    'xmatch': 'expand'
}


class ICFRunner(object):
    """
    Integrated cluster finder main component.
    Used to do all things with clusters.
    """
    def __init__(self, catalog, override=False, schema='public'):
        self.conn = SQLConnection('xmm', schema)
        self.conn.autocommit = True
        self.working_format = 'votable'
        self.logger = get_logger('ICFx', log_filename='/tmp/icfx.log')
        self.logger.setLevel(logging.DEBUG)
        self.set_catalog(catalog)
        self.override = override
        self.source_catalogs = self.conn.execute_set("""
        select distinct source_catalog from fields;""", quiet=False)
        self.source_catalogs = [x[0] for x in self.source_catalogs]
        sqllist.load_defaults()
        sqllist.GLOBALS['c'] = self.catalog.CATALOG

    def set_catalog(self, catalog):
        """
        Switch to another catalog.
        :param catalog: name of the catalog to be used.
        """
        catalog, cluster_finder = get_catalog_and_finder(catalog)
        self.catalog = catalog()
        self.cluster_finder = cluster_finder()
        self.cluster_finder.conn.set_schema(self.conn.schema)
        if catalog.CATALOG in DEFAULT_SUFFIX:
            self.suffix = DEFAULT_SUFFIX[catalog.CATALOG]
        if catalog == 'xmatch':
            self.catalog.reload_spectra = True

    def output_sql(self, sql, output_name, xformat=None):
        """
        Run SQL query and save its result to file.
        """
        if xformat is None:
            xformat = self.working_format
        if output_name is None:
            return sql_to_file(sql, output_name, write_format=xformat,
                               connection=self.conn, automatic_extention=False)
        else:
            if path.exists(output_name):
                if not self.override:
                    raise IOError('file %s exists' % output_name)
                else:
                    unlink(output_name)
            sql_to_file(sql, output_name, write_format=xformat,
                        connection=self.conn, automatic_extention=False)
            return True

    def get_members_iid(self, iid, output_name, xformat=None):
        """
        Get all possible cluster members.
        """
        self.logger.debug('Get members for %s', iid)
        sqllist.GLOBALS['i'] = iid
        if self.catalog.CATALOG == 'xmatch':
            sqlname = 'xmatch-members'
        else:
            sqlname = 'members'
        sql = sqllist.get_sql(sqlname,
                              to_str(self.catalog.magnitude_columns, ','),
                              to_str(self.catalog.error_columns, ','))
        return self.output_sql(sql, output_name, xformat)

    def get_members(self, user, iid, output_name, format=None):
        """
        Output memberships and per-source information.
        """
        self.logger.debug('Get members for %s of user %s', iid, user)
        sqllist.GLOBALS['i'] = self.get_global_iid(user, iid)
        sql = sqllist.get_sql('members',
                              to_str(self.catalog.error_columns, ','),
                              to_str(self.catalog.magnitude_columns, ','))
        return self.output_sql(sql, output_name, format)

    def get_detections(self, user, iid, output_name, format=None):
        """
        Get all cluster detections for a given field.
        """
        self.logger.debug('Get detections for %s of user %s', iid, user)
        sql = sqllist.get_sql('cluster-detections', user, iid,
                              self.catalog.CATALOG)
        return self.output_sql(sql, output_name, format)

    def get_cluster_catalog(self, cluster_catalog, output_name,
                            xformat=None,
                            compare_z=True,
                            export_all=False):
        """
        Get all cluster detections for the catalog.
        """
        self.logger.debug('Get cluster catalog for user %s', cluster_catalog)
        if compare_z:
            z_columns = """f.z as z_orig, c.z z_mine,
            abs(f.z - c.z) as dz, c.z_err,
            case when abs(c.z - f.z) < c.z_err then True
                                               else False end as is_good_z,
            """
        else:
            z_columns = "c.z z_mine, c.z_err,"
        if not export_all:
            extras = """and c.is_ok"""
        else:
            extras = ''
        sqllist.GLOBALS['s'] = cluster_catalog
        if cluster_catalog in self.source_catalogs:
            sql = sqllist.get_sql('cluster-catalog', z_columns, extras)
        else:
            sql = sqllist.get_sql('ext-cluster-catalog', z_columns, extras)
        return self.output_sql(sql, output_name, xformat)

    def create_iid(self, user, iid, ra, decl, field_set=None):
        """
        Create new field.
        """
        self.logger.debug('Create iid %s for user %s', iid, user)
        sql = """insert into fields (user_id, local_iid, ra, decl)
                 values ('%s', %s, %s, %s) returning iid"""
        cur = self.conn.get_cursor(sql % (user, iid, ra, decl))
        iid = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        if field_set is not None and len(field_set) < 20:
            sql = """insert into field_sets (iid, set_id)
                     values (%s, '%s')"""
            cur = self.conn.get_cursor(sql % (iid, field_set))
        self.conn.commit()
        cur.close()
        return iid

    def list_iids(self, user, output_name, format='votable'):
        """
        List all IID of the current user.
        """
        sql = """select local_iid as iid, ra, decl from fields
        where user_id = '%s'""" % user
        return self.output_sql(sql, output_name, format)

    def get_global_iid(self, user, iid):
        """
        Conver user + local iid into global iid.
        """
        global_iid = self.conn.exec_return("""
select iid from fields
where local_iid = %s and user_id = '%s'""" % (iid, user),
            single_column=True)
        return global_iid

    def delete_iid(self, user, iid):
        """
        Delete users iid.
        """
        self.logger.debug('Delete iid %s for user %s', iid, user)
        global_iid = self.get_global_iid(user, iid)
        catalogs = self.conn.execute_set(["""
select catalog from fields_properties
where iid = %s""" % global_iid], quiet=False)
        tmp_catalog = sqllist.GLOBALS['c']
        for catalog in catalogs:
            sqllist.GLOBALS['c'] = catalog[0]
            delete_sql = sqllist.get_sql('delete-from-catalog', global_iid)
            self.conn.execute(delete_sql)
        sqllist.GLOBALS['c'] = tmp_catalog
        self.conn.execute(sqllist.get_sql('delete-iid', global_iid, user))
        self.conn.commit()

    def crawl(self, user, iid):
        """
        Run data crawler.
        """
        self.logger.debug('Get data for iid %s for user %s', iid, user)
        global_iid = self.get_global_iid(user, iid)
        crawler = DataLoader()
        crawler.conn.set_schema(self.conn.schema)
        if self.catalog.CATALOG != 'xmatch':
            crawler.set_viz_catalog('spectra')
            crawler.run_viz_catalog(global_iid, query_vizier=True, reprocess=True)
        crawler.set_viz_catalog(self.catalog.CATALOG)
        crawler.run_viz_catalog(global_iid, query_vizier=True, reprocess=True)

    def run_icf(self, user, iid):
        """
        Run the Integrated cluster finder.
        """
        self.logger.debug('Run ICF for iid %s for user %s', iid, user)
        global_iid = self.get_global_iid(user, iid)
        self.cluster_finder.set_catalog(self.catalog.CATALOG,
                                        DEFAULT_SUFFIX[self.catalog.CATALOG])
        self.cluster_finder.run_method_all_z(global_iid,
                                             debug=False,
                                             quiet=True)
        return global_iid

    def plot_one(self, user, iid, filename):
        """
        Plot lambda(z) function.
        """
        import matplotlib.pyplot as plt
        global_iid = self.get_global_iid(user, iid)
        # The following lines are reserved for plotting sky projection.
        #sql0 = """select ra, decl from fields where iid = %s""" % global_iid
        #ra0, dec0  =  np.array(self.conn.execute_set(sql0, quiet=False))[0]
        self.cluster_finder.set_catalog(self.catalog.CATALOG,
                                        DEFAULT_SUFFIX[self.catalog.CATALOG])
        plt.xlabel('z', fontsize='large')
        plt.ylabel('Lambda', fontsize='large')
        x, y = [], []
        for iz, lambdas in enumerate(
            self.cluster_finder.run_method_all_z(global_iid,
                                                 debug=False,
                                                 save_detections=False,
                                                 quiet=True)[0]):
            x.append(self.cluster_finder.redshifts[iz])
            y.append(lambdas)
        plt.plot(x, y, 'k-o')
        plt.savefig(filename, format='png')
        plt.clf()
        return True

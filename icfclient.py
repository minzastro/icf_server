#!/usr/bin/python
"""
Created on Thu May 15 16:59:33 2014
@author: mints
"""
import requests as rq
import sys
import pickle
import os


def ensure_dir(directory):
    """
    Create directory if it does not exist.
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


class ICFClient(object):
    """
    Integrated cluster finder client class.
    """
    #HOST = 'http://serendib.unistra.fr/cgi-bin'
    HOST = 'http://serendib.unistra.fr/cgi-bin/icfserver.py'
    #HOST = 'http://127.0.0.1/cgi-bin/icfserver.py'

    def __init__(self):
        self.echo = True
        self.logged_in = False
        self.cookies = None
        ensure_dir('%s/.client_cookies' % os.environ['HOME'])
        if os.path.exists(self._get_cookie()):
            self.logged_in = True

    def _get_cookie(self):
        return '%s/.client_cookies/last.cookie' % os.environ['HOME']

    def _print_wrong(self, result):
        print 'Error %s (%s)' % (result.status_code,
                                 rq.status_codes._codes[result.status_code][0])
        print result.contents

    def run_command(self, cmd, data={}, use_cookies=True, return_result=True):
        """
        Send POST request and return the response.
        """
        url = '%s/%s' % (self.HOST, cmd)
        if use_cookies and self.cookies is None:
            with open(self._get_cookie(), 'r') as f:
                self.cookies = rq.utils.cookiejar_from_dict(pickle.load(f))
        result = rq.post(url, data, cookies=self.cookies)
        if return_result:
            return result
        else:
            if result.status_code == 200:
                print result.content
            else:
                self._print_wrong(result)

    def login(self, user, password):
        result = self.run_command('login',
                                  {'user': user,
                                   'password': password},
                                  use_cookies=False)
        if result.status_code == 200:
            self.cookies = result.cookies
            with open(self._get_cookie(), 'w') as f:
                pickle.dump(rq.utils.dict_from_cookiejar(self.cookies), f)
            self.logged_in = True
            print result.content
        else:
            self._print_wrong(result)
        return result

    def change_password(self, password):
        if self.logged_in:
            result = self.run_command('change_password',
                                      {'new_password': password})
            return result
        else:
            self._print_wrong(result)
            return -1

    def logout(self):
        if self.logged_in:
            result = self.run_command('logout')
            if result.status_code == 200:
                self.cookies = None
                self.logged_in = False
                print result.content
            else:
                self._print_wrong(result)
            return result
        else:
            print 'Not logged in!'
            return -1

    def create_iid(self, iid, ra, dec):
        data = {'iid': iid,
                'ra': ra,
                'dec': dec}
        self.run_command('create_iid', data, return_result=False)

    def delete_iid(self, iid):
        data = {'iid': iid}
        self.run_command('delete_iid', data, return_result=False)

    def ls(self):
        self.run_command('ls', return_result=False)

    def crawl(self, iid):
        self.run_command('crawl', {'iid': iid}, return_result=False)

    def run_icf(self, iid):
        self.run_command('run_icf', {'iid': iid}, return_result=False)

    def get_members(self, iid, filename, format='votable'):
        result = self.run_command('get_members', {'iid': iid,
                                                'filename': filename,
                                                'format': format})
        if result.status_code == 200:
            with open(filename, 'w') as output_file:
                output_file.write(result.contents)
            return filename
        else:
            self._print_wrong(result)
            return result

    def get_detections(self, iid, filename, format='votable'):
        result = self.run_command('get_detections', {'iid': iid,
                                                     'filename': filename,
                                                     'format': format})
        if result.status_code == 200:
            with open(filename, 'w') as output_file:
                output_file.write(result.content)
            return filename
        else:
            self._print_wrong(result)
            return result


    def download(self, filename, out_filename=None):
        result = self.run_command('download', {'filename': filename})
        if out_filename is None:
            out_name = filename
        else:
            out_name = out_filename
        if result.status_code == 200:
            with open(out_name, 'w') as output_file:
                output_file.write(result.text)
            return filename
        else:
            self._print_wrong(result)
            return result

    def plot_lambda(self, iid, filename='test.png'):
        result = self.run_command('plot_lambda', {'iid': iid,
                                                  'filename': filename})
        if result.status_code == 200:
            with open(filename, 'wb') as output_file:
                output_file.write(result.content)
            print 'Plot saved into %s' % filename
        else:
            self._print_wrong(result)
            return result

    def list_iids(self, filename='iids.votable'):
        result = self.run_command('list_iids', {'filename': filename})
        if result.status_code == 200:
            with open(filename, 'wb') as output_file:
                output_file.write(result.content)
            print 'IIDs data saved into %s' % filename
        else:
            self._print_wrong(result)
        return result

if __name__ == '__main__':
    client = ICFClient()
    try:
        method = getattr(client, sys.argv[1])
        result = method(*sys.argv[2:])
        if result is not None:
            print result
    except AttributeError as ex:
        print "Command %s is not available" % sys.argv[1]

#!/usr/bin/python2.7
"""
Created on Mon May 19 10:48:54 2014
@author: mints
"""
import cgi
import sys
sys.path.insert(0, '/home/mints/prog/XMM')
import os
if 'USER' not in os.environ or os.environ['USER'] != 'mints':
    # This is for the deployment version:
    os.environ['HOME'] = '/var/www/config'
    os.environ['PATH'] = '%s:/var/www/restricted/bin' % os.environ['PATH']
from lib.password_manager import PasswordManager
from lib.utils import ensure_dir, silentremove, verify
from server.icfrunner import ICFRunner
from glob import glob
from astropy import log
from cherrypy._cpcompat import random20
import time
from httplib import responses


def get_response(status, output=None):
    """
    Produce a response string with HTML status.
    """
    message = responses[status]
    if output is None:
        out_text = message
    else:
        out_text = output
    return """Status: %s %s

%s""" % (status, message, out_text)


def binary_method(func):
    func.is_binary = True
    return func


def text_method(func):
    func.is_binary = False
    return func


def print_method(func):
    func.is_print = True
    return func


def non_print_method(func):
    func.is_print = False
    return func


class MyCookie(object):
    """
    General class to manage session cookies.
    """
    SESSION_PATH = '%s/.sessions' % os.path.dirname(__file__)
    TIMEOUT = 1200

    @classmethod
    def get_cookie(cls, cookie):
        """
        Load a saved cookie from file.
        """
        cookie_name = '%s/%s.cookie' % (cls.SESSION_PATH, cookie)
        if os.path.exists(cookie_name):
            if time.time() - os.stat(cookie_name).st_mtime > cls.TIMEOUT:
                silentremove(cookie_name)
                return None
            else:
                # Update the access time
                os.utime(cookie_name, None)
                return open(cookie_name, 'r').readline()
        else:
            return None

    @classmethod
    def destroy_cookie(cls, cookie):
        """
        Delete cookie file.
        """
        cookie_name = '%s/%s.cookie' % (cls.SESSION_PATH, cookie)
        silentremove(cookie_name)

    @classmethod
    def create_cookie(cls, user):
        """
        Create a unique cookie value (20 symbols).
        """
        cookie = random20()
        cookie_name = '%s/%s.cookie' % (cls.SESSION_PATH, cookie)
        cookie_file = open(cookie_name, 'w')
        cookie_file.write(user)
        cookie_file.close()
        return cookie


class ICFServer(object):
    """
    Integrated cluster finder server class.
    """

    SESSION_PATH = '%s/.sessions' % os.path.dirname(__file__)

    VALID_COMMANDS = [
        'login', 'logout',
        'ls', 'remove', 'download',
        'get_detections', 'get_members',
        'create_iid', 'delete_iid',
        'crawl', 'run_icf', 'plot_lambda',
        'list_iids'
    ]

    """
    This code can be used to create a list of available formats:
    (not used directly for performance)
import  astropy.io.registry as reg
fmt = [ f[1] for f in reg.get_formats() ]
fmt
','.join(fmt)
    """
    VALID_FORMATS = 'ascii,ascii.aastex,ascii.basic,ascii.cds,ascii.commented_header,ascii.daophot,ascii.fixed_width,ascii.fixed_width_no_header,ascii.fixed_width_two_line,ascii.ipac,ascii.latex,ascii.no_header,ascii.rdb,ascii.sextractor,ascii.tab,fits,hdf5,votable,aastex,cds,daophot,ipac,latex,rdb'.split(',')

    def __init__(self):
        self.passwords = PasswordManager()
        self.runner = ICFRunner('xmatch')
        self.runner.override = True
        self.current_user = None

    def set_cookie(self, cookie):
        self.current_user = MyCookie.get_cookie(cookie)

    def _is_logged_in(self):
        return self.current_user is not None

    def get_user_dir(self):
        """
        Get a data folder for the current user.
        Creates folder if it does not exist.
        """
        user_dir = '%s/icfhome/%s' % (os.path.dirname(__file__),
                                      self.current_user)
        ensure_dir(user_dir)
        return user_dir

    def validate_path(self, path):
        """
        Check if a given path is in the user directory.
        """
        user_dir = self.get_user_dir()
        full_path = os.path.abspath('%s/%s' % (user_dir, path))
        return os.path.commonprefix((user_dir, full_path)) == user_dir

    @binary_method
    @print_method
    def login(self, user, password):
        log.info('%s loggin in...', user)
        login_result = self.passwords.verify_password(user, password)
        if login_result == self.passwords.PASSWORD_OK:
            self.current_user = user
            cookie = MyCookie.create_cookie(user)
            return """Content-Type: text/html
Set-Cookie: id=%s

Ok""" % cookie
        elif login_result == self.passwords.PASSWORD_FAILED:
            return get_response(401, "Password failed!")
        elif login_result == self.passwords.USER_NOT_EXISTS:
            return get_response(401, "User does not exist!")

    @text_method
    @print_method
    def logout(self):
        if self._is_logged_in():
            return get_response(200)
        else:
            return get_response(401, 'Not logged in')

    @text_method
    @print_method
    def change_password(self, new_password):
        if self._is_logged_in():
            self.passwords.create_user(self.current_user,
                                       new_password)
            return get_response(200, 'Ok for user %s' % self.current_user)
        else:
            return get_response(403, 'Not allowed')

    @text_method
    @print_method
    def create_iid(self, iid, ra, dec):
        if self._is_logged_in():
            value = self.runner.create_iid(self.current_user,
                                           iid, ra, dec)
            self.runner.conn.commit()
            return get_response(200, 'Ok for user %s, new iid = %s' %
                                (self.current_user, value))
        else:
            return get_response(403, 'Unable to create iid')

    @text_method
    @print_method
    def delete_iid(self, iid):
        if self._is_logged_in():
            value = self.runner.delete_iid(self.current_user,
                                           iid)
            self.runner.conn.commit()
            return get_response(200, 'Ok for user %s, iid %s deleted' %
                                (self.current_user, value))
        else:
            return get_response(403, 'Not logged in')

    @text_method
    @print_method
    def ls(self):
        if self._is_logged_in():
            user_dir = self.get_user_dir()
            cut_position = len(user_dir) + 1
            files = glob('%s/*' % user_dir)
            return get_response(200,
                                '\n'.join([f[cut_position:] for f in files]))
        else:
            return get_response(403, 'Not logged in')

    @binary_method
    @non_print_method
    def download(self, filename):
        """
        Download file from the server.
        """
        if self._is_logged_in():
            user_dir = self.get_user_dir()
            filepath = '%s/%s' % (user_dir, filename)
            if os.path.exists(filepath) and \
                self.validate_path(filepath):
                print """Content-Type:application/octet-stream; name="%s"
Content-Disposition: attachment; filename="%s"
""" % (filepath, filepath)

                # Actual File Content will go hear.
                result_file = open(filepath, "rb")
                print result_file.read()
                # Close opend file
                result_file.close()
                return None
            else:
                return get_response(403, "File not found: %s" % filepath)
        else:
            return get_response(403, 'Not logged in')

    @text_method
    @print_method
    def run_icf(self, iid):
        if self._is_logged_in():
            self.runner.run_icf(self.current_user, iid)
            return get_response(200, 'Cluster finder done')
        else:
            return get_response(403, 'Not logged in')

    @text_method
    @print_method
    def crawl(self, iid):
        if self._is_logged_in():
            self.runner.crawl(self.current_user, iid)
            return get_response(200)
        else:
            return get_response(403, 'Not logged in')

    @binary_method
    @print_method
    def get_detections(self, iid, filename=None, format='votable'):
        if self._is_logged_in():
            if format not in self.VALID_FORMATS:
                return get_response(400, """Invalid format %s!
valid formats are: %s""" % (format, self.VALID_FORMATS))
            user_dir = self.get_user_dir()
            if filename is None:
                out_file = 'detections_%s.%s' % (iid, format)
            else:
                out_file = filename
            self.runner.get_detections(self.current_user, iid,
                                       '%s/%s' % (user_dir, out_file),
                                       format)
            return self.download(out_file)
        else:
            return get_response(403, 'Not logged in')

    @binary_method
    @print_method
    def get_members(self, iid, filename=None, format='votable'):
        if self._is_logged_in():
            if format not in self.VALID_FORMATS:
                return get_response(400, """Invalid format %s!
valid formats are: %s""" % (format, self.VALID_FORMATS))
            user_dir = self.get_user_dir()
            if filename is None:
                out_file = 'members_%s.%s' % (iid, format)
            else:
                out_file = filename
            self.runner.get_members(self.current_user, iid,
                                    '%s/%s' % (user_dir, out_file), format)
            return self.download(out_file)
        else:
            return get_response(403, 'Not logged in')

    @binary_method
    @print_method
    def list_iids(self, filename=None, format='votable'):
        if self._is_logged_in():
            if format not in self.VALID_FORMATS:
                return get_response(400, """Invalid format %s!
valid formats are: %s""" % (format, self.VALID_FORMATS))
            user_dir = self.get_user_dir()
            if filename is None:
                out_file = 'iids.%s' % format
            else:
                out_file = filename
            self.runner.list_iids(self.current_user,
                                  '%s/%s' % (user_dir, out_file),
                                  format)
            return self.download(out_file)
        else:
            return get_response(403, 'Not logged in')

    @binary_method
    @print_method
    def plot_lambda(self, iid, filename=None):
        if self._is_logged_in():
            user_dir = self.get_user_dir()
            if filename is None:
                out_file = '%s/plot_%s.png' % (user_dir, iid)
            else:
                out_file = filename
            self.runner.plot_one(self.current_user, iid,
                                 '%s/%s' % (user_dir, out_file))
            return self.download(out_file)
        else:
            return get_response(403, 'Not logged in')

    @text_method
    @print_method
    def remove(self, filename):
        if self._is_logged_in():
            if self.validate_path(filename):
                user_dir = self.get_user_dir()
                silentremove('%s/%s' % (user_dir, filename))
                return get_response(200, 'File %s deleted' % filename)
            else:
                return get_response(403, 'No access to file %s' % filename)
        else:
            return get_response(403, 'Not logged in')


if __name__ == '__main__':
    server = ICFServer()
    if 'HTTP_COOKIE' in os.environ:
        server.set_cookie(os.environ['HTTP_COOKIE'][3:])
    if 'PATH_INFO' in os.environ:
        command = os.environ['PATH_INFO'][1:]
        if '/' in command:
            command = command.split('/')[-1]
    else:
        print """Content-Type: text/html

        Something went wrong: no PATH_INFO variable.
Please report this problem"""
        sys.exit()
    if '/' in command:
        command = command.split('/')[-1]
    try:
        method = getattr(server, command)
        if not method.is_binary:
            print """Content-Type: text/html

"""
        # Now check that all parameters are correct:
        form = cgi.FieldStorage()
        form_dict = {item: form[item].value for item in form}
        is_ok, wrong, args = verify(method, form_dict.keys())
        if is_ok:
            # Call the method if parameters are Ok.
            result = method(**form_dict)
            if method.is_print and result is not None:
                print result
        else:
            print get_response(400, 'Wrong arguments %s. Arguments are: %s' %
                               (wrong, args))
    except AttributeError as ex:
        print """Content-Type: text/html

%s""" % get_response(404, """Command %s is not available.
Available commands are: %s""" % (command, ','.join(server.VALID_COMMANDS)))
        sys.exit()

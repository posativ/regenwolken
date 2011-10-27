#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.3"

from os import urandom
from os.path import basename, splitext
from random import getrandbits
from base64 import standard_b64encode
import mimetypes

from werkzeug import Response
from wolken import conf
from wolken.mongonic import GridFS
from pymongo import Connection
from gridfs.errors import NoFile

from jinja2 import Environment, PackageLoader
jinenv = Environment(loader=PackageLoader('wolken', 'layouts'))

from wolken.REST import prove_auth, Item

db = Connection(conf.MONGODB_HOST, conf.MONGODB_PORT)[conf.MONGODB_NAME]
fs = GridFS(db)

from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

try:
    from pygments.lexers import get_lexer_for_filename, ClassNotFound
    def is_sourcecode(filename):
        try:
            get_lexer_for_filename(filename)
            return True
        except ClassNotFound:
            return False
except ImportError:
    def is_sourcecode(filename):
        whitelist = ['py', 'c'] # TODO: extend
        
        if splitext(filename)[1][1:] in whitelist:
            return True
        return False


class Drop:
    '''Drop class which renders item-specific layouts.'''
    
    def __init__(self, drop):
        
        def guess_type(url):
            try:
                m = mimetypes.guess_type(url)[0].split('/')[0]
                if m in ['image', 'text']:
                    return m
            except AttributeError:
                if self.markdown() or self.is_sourcecode():
                    return 'text'
            return 'other'
        
        self.__dict__.update(Item(drop))
        self.read = drop.read
        self.length = drop.length
        self.item_type = guess_type(self.name)
        self.url = self.__dict__['content_url']

    def __str__(self):
        
        if self.item_type == 'image':
            tt = jinenv.get_template('image.html')
            return tt.render(drop=self)
        
        elif self.item_type == 'text':
            tt = jinenv.get_template('text.html')
            if self.is_sourcecode() and self.length <= 2**18:
                html = highlight(self.read(), get_lexer_for_filename(self.url),
                                 HtmlFormatter(lineos=False, cssclass='highlight'))
                return tt.render(drop=self, textstream=html)
            return tt.render(drop=self, textstream=self.read())
        else:
            tt = jinenv.get_template('other.html')
            return tt.render(drop=self)
            
    def markdown(self):
        return True if splitext(self.url)[1][1:] in ['md', 'mdown', 'markdown'] else False
        
    def is_sourcecode(self):
        return is_sourcecode(self.url)


def private(f):
    """login decorator using HTTP Digest Authentication.  Pattern based on
    http://flask.pocoo.org/docs/patterns/viewdecorators/

    -- http://developer.getcloudapp.com/usage/#authentication"""

    def dec(env, req, *args, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Digest Auth failed."""

        item = db.items.find_one({'short_id': kwargs['short_id']})
        if item and not item['private']:
            return f(env, req, *args, **kwargs)

        if not req.authorization:
            response = Response('Unauthorized', 401, content_type='text/html; charset=utf-8')
            response.www_authenticate.set_digest('Application', nonce=standard_b64encode(urandom(32)),
                        qop=('auth', ), opaque='%x' % getrandbits(128), algorithm='MD5')
            return response
        elif prove_auth(req) != req.authorization.response:
            return Response('Unauthorized.', 403)
        return f(env, req, *args, **kwargs)
    return dec


def index(environ, response):
    """my.cl.ly/"""

    return Response("Not Implemented", 501, content_type='text/html')

def login_page(environ, response):

    tt = jinenv.get_template('login.html')
    return Response(tt.render(), 200, content_type='text/html')


def login(environ, response):

    return Response('See there', 301, headers={'Location': '/'})
    

def drop(environ, response, short_id):
    
    tt = jinenv.get_template('layout.html')    
    try:
        drop = Drop(fs.get(short_id=short_id))
    except NoFile:
        return Response('Not Found', 404)
    
    return Response(tt.render(drop=drop), 200, content_type='text/html')


@private
def show(environ, request, short_id, name):
    """returns bookmark or file either as direct download with human-readable,
    original filename or inline display using whitelisting"""

    try:
        f = fs.get(short_id=short_id)
        fs.inc_count(f._id)
    except NoFile:
        return Response('Not Found', 404)

    if f.item_type == 'bookmark':
        return Response('Moved Temporarily', 302,
                    headers={'Location': f.redirect_url})
    elif not f.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.3"

import sys
from os import urandom
from os.path import basename, splitext
from random import getrandbits
from base64 import standard_b64decode, standard_b64encode
import mimetypes

from werkzeug import Response
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache(30*60)

from wolken import conf
from wolken.mongonic import GridFS
from wolken.REST import prove_auth, Item
from pymongo import Connection
from gridfs.errors import NoFile

from jinja2 import Environment, PackageLoader
jinenv = Environment(loader=PackageLoader('wolken', 'layouts'))

db = Connection(conf.MONGODB_HOST, conf.MONGODB_PORT)[conf.MONGODB_NAME]
fs = GridFS(db)

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    if conf.SYNTAX_HIGHLIGHTING:
        print >> sys.stderr, "'pygments' not found, syntax highlighting disabled"
    conf.SYNTAX_HIGHLIGHTING = False

try:
    import markdown
except ImportError:
    if conf.MARKDOWN_FORMATTING:
        print >> sys.stderr, "'markdown' not found, markdown formatting disabled"
    conf.MARKDOWN_FORMATTING = False

try:
    from PIL import Image, ImageFile
except ImportError:
    if conf.THUMBNAILS:
        print >> sys.stderr, "'PIL' not found, thumbnailing disabled"
    conf.THUMBNAILS = False

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO


class ThumbnailException(Exception): pass


class Drop:
    '''Drop class which renders item-specific layouts.'''
    
    def __init__(self, drop):
        
        def guess_type(url):
            try:
                m = mimetypes.guess_type(url)[0].split('/')[0]
                if m in ['image', 'text']:
                    return m
            except AttributeError:
                print self.markdown
                if self.markdown or self.sourcecode:
                    return 'text'
            return 'other'
        
        self.__dict__.update(Item(drop))
        self.read, self.length = drop.read, drop.length
        self.filename, self.short_id = drop.filename, drop.short_id
        self.item_type = guess_type(self.name)
        self.url = self.__dict__['content_url']

    def __str__(self):
        
        if self.item_type == 'image':
            tt = jinenv.get_template('image.html')
            return tt.render(drop=self)
        
        elif self.item_type == 'text':
            tt = jinenv.get_template('text.html')
            rv = cache.get('text-'+self.short_id)
            if rv:
                return tt.render(drop=self, textstream=rv)
            if self.markdown and conf.MARKDOWN_FORMATTING:
                md = markdown.markdown(self.read())
                cache.set('text-'+self.short_id, md)
                return tt.render(drop=self, textstream=md)
            elif self.sourcecode and conf.SYNTAX_HIGHLIGHTING:
                html = highlight(self.read(), get_lexer_for_filename(self.url),
                                 HtmlFormatter(lineos=False, cssclass='highlight'))
                cache.set('text-'+self.short_id, html)
                return tt.render(drop=self, textstream=html)
            return tt.render(drop=self, textstream=self.read())
        else:
            tt = jinenv.get_template('other.html')
            return tt.render(drop=self)
    
    @property
    def markdown(self):
        return True if splitext(self.filename)[1][1:] in ['md', 'mdown', 'markdown'] else False
    
    @property
    def sourcecode(self):
        try: ClassNotFound
        except NameError: return False
        
        try:
            get_lexer_for_filename(self.filename)
            return True
        except ClassNotFound:
            return False


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
        drop = fs.get(short_id=short_id)
    except NoFile:
        return Response('Not Found', 404)
        
    if drop.item_type == 'bookmark':
        return Response('Moved Temporarily', 302, headers={'Location': drop.redirect_url})
    
    return Response(tt.render(drop=Drop(drop)), 200, content_type='text/html')
    

def thumbnail(fp, size=128, bs=2048):
    """generate png thumbnails"""

    p = ImageFile.Parser()
    
    try:
        while True:
            s = fp.read(bs)
            if not s:
                break
            p.feed(s)

        img = p.close()
        img.thumbnail((size, size))
        op = StringIO.StringIO()
        img.save(op, 'PNG')
        op.seek(0)
        return op.read().encode('base64')
    except IOError:
        raise ThumbnailException


@private
def show(environ, request, short_id, filename):
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


@private
def thumb(environ, request, short_id):
    """returns 128px thumbnail, when possible and cached for 30 minutes,
    otherwise item_type icons."""
    
    th = cache.get('thumb-'+short_id)
    if th: return Response(standard_b64decode(th), 200, content_type='image/png')
    
    try:
        rv = fs.get(short_id=short_id)
    except NoFile:
        return Response('Not Found', 404)

    if rv.item_type == 'image' and conf.THUMBNAILS:
        try:
            th = thumbnail(rv)
            cache.set('thumb-'+short_id, th)
            return Response(standard_b64decode(th), 200, content_type='image/png')
        except ThumbnailException:
            pass
    return Response(open('wolken/static/images/item_types/%s.png' % rv.item_type),
                    200, content_type='image/png')

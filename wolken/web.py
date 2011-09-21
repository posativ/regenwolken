#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.3"

from os import urandom
from os.path import basename
from random import getrandbits
from base64 import standard_b64encode

from werkzeug import Response
from wolken import conf
from wolken.mongonic import GridFS
from pymongo import Connection
from gridfs.errors import NoFile

from jinja2 import Environment, PackageLoader
jinenv = Environment(loader=PackageLoader('wolken', 'layouts'))

from wolken.REST import prove_auth

db = Connection(conf.MONGODB_HOST, conf.MONGODB_PORT)[conf.MONGODB_NAME]
fs = GridFS(db)


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


    tt = jinenv.get_template('index.html')

    return Response(tt.render(), 200, content_type='text/html')

def login_page(environ, response):

    tt = jinenv.get_template('login.html')
    return Response(tt.render(), 200, content_type='text/html')


def login(environ, response):

    return Response('See there', 301, headers={'Location': '/'})


@private
def show(environ, request, short_id):
    """returns bookmark or file either as direct download with human-readable,
    original filename or inline display using whitelisting"""

    try:
        f = fs.get(short_id=short_id)
        fs.inc_count(f._id)
    except NoFile:
        return Response('Not Found', 404)

    if f.item_type == 'bookmark':
        return Response('Moved Permanently', 301,
                    headers={'Location': f.redirect_url})
    elif not f.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)

#!/usr/bin/env python
# -*- encoding: utf-8 -*-

__version__ = "0.2"

from os.path import basename
from random import getrandbits

from werkzeug import Response
from wolken import conf
from wolken.mongonic import GridFS
from pymongo import Connection
from gridfs.errors import NoFile

from wolken.REST import prove_auth

db = Connection(conf.MONGODB_HOST, conf.MONGODB_PORT)['cloudapp']
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
            response = Response(status=401)
            response.www_authenticate.set_digest('Application', nonce='%x' % getrandbits(128),
                        qop=('auth', ), opaque='%x' % getrandbits(128), algorithm='MD5')
            return response
        elif prove_auth(req) != req.authorization.response:
            return Response('Unauthorized.', 403)
        return f(env, req, *args, **kwargs)
    return dec


def index(environ, response):
    """my.cl.ly/"""
    
    body = '<h1>Hallo Welt</h1>'
    
    return Response(body, 200, content_type='text/html')


@private
def show(environ, request, short_id):
    """returns file either as direct download with human-readable, original
    filename or inline display using whitelisting"""
    
    try:
        f = fs.get(short_id=short_id)
        cnt = f.view_counter
        fs.update(f._id, view_counter=cnt+1)
    except NoFile:
        return Response('File not found!', 404)
    if not f.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)


@private
def redirect(environ, request, short_id):
    """find short id and redirect to this url"""
    
    cur = db.items.find_one({'short_id': '-'+short_id})
    if not cur:
        return Response('Not found.', 404)
        
    return Response('Moved Permanently', 301,
                    headers={'Location': cur['redirect_url']})

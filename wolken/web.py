#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from os.path import basename

from werkzeug import Response
from wolken import SETTINGS
from wolken.mongonic import GridFS
from pymongo import Connection
from gridfs.errors import NoFile

db = Connection(SETTINGS.MONGODB_HOST, SETTINGS.MONGODB_PORT)['cloudapp']
fs = GridFS(db)

def index(environ, response):
    """my.cl.ly/"""
    
    body = '<h1>Hallo Welt</h1>'
    
    return Response(body, 200, content_type='text/html')

def show(environ, request, short):
    """returns file either as direct download with human-readable, original
    filename or inline display using whitelisting"""
    
    try:
        f = fs.get(url=short)
        cnt = f.view_counter
        fs.update(f._id, view_counter=cnt+1)
    except NoFile:
        return Response('File not found!', 404)
    if not f.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)
    

def redirect(environ, request, short):
    """find short id and redirect to this url"""
    
    cur = db.items.find_one({'url': 'http://%s/-%s' % (SETTINGS.HOSTNAME, short)})
    if not cur:
        return Response('Not found.', 404)
        
    return Response('Moved Permanently', 301,
                    headers={'Location': cur['redirect_url']})
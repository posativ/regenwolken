#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

# TODO: hashing passwords + salt

__version__ = "0.1.2-alpha"

from functools import wraps
from random import random, getrandbits
from urlparse import urlparse
from os.path import basename
from time import strftime, time, gmtime
from datetime import datetime
import hashlib
import string

try:
    import json
except ImportError:
    import simplejson as json

from werkzeug.wrappers import Request, Response
from wolken import Sessions
from wolken import MONGODB_HOST, MONGODB_PORT

from pymongo import Connection
import gridfs
from bson.objectid import ObjectId

sessions = Sessions(timeout=3600)

db = Connection(MONGODB_HOST, MONGODB_PORT)['cloudapp']
fs = gridfs.GridFS(db)

class Item:
    
    def __init__(self, name, hash):
        
        self.href = "http://my.cl.ly/items/%x" % hash
        self.name = name
        self.private = True
        self.subscribed = False
        self.url = "http://my.cl.ly/items/%x" % hash
        self.content_url = "http://my.cl.ly/items/%x" % hash
        self.item_type = "bookmark"
        self.view_counter = 0
        self.icon = "http://my.cl.ly/images/item_types/bookmark.png"
        self.remote_url = "http://my.cl.ly/items/%x" % hash
        self.redirect_url = "http://my.cl.ly"
        self.source = "Regenwolke/%s LeaveTheCloud/Now" % __version__
        self.created_at = strftime('%Y-%m-%dT%H:%M:%SZ')
        self.updated_at = strftime('%Y-%m-%dT%H:%M:%SZ')
        self.deleted_at = None


def Account(email, passwd, **kw):
    
    __dict__ = {
        'domain': None,
        'domain_home_page': None,
        'private_items': True,
        'subscribed': False,
        'alpha': False,
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ'),
        'activated_at': None,
        "items": [],
        'email': email,
        'passwd': passwd
    }
    
    __dict__.update(kw)
    return __dict__


def login(f):
    """login decorator using HTTP Digest Authentication.  Pattern based on
    http://flask.pocoo.org/docs/patterns/viewdecorators/"""
    
    def md5(data):
        return hashlib.md5(data).hexdigest()
    
    def prove(auth):
        """calculates  digest response (MD5 and qop)"""
        
        def A1(auth):
            query = db.accounts.find({'email': auth.username})
            if query.count() == 1:
                passwd = query[0]['passwd']
            else:
                passwd = '%x' % getrandbits(256)
            return md5(auth.username + ':' + auth.realm + ':' + passwd)
        
        b = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth', md5('GET:' + auth.uri)])
        
        return md5(A1(auth) + ':' + b)
    
    def dec(env, req, **kwargs):
        if not req.authorization:
            response = Response(status=401)
            response.www_authenticate.set_digest('Application', nonce='%x' % getrandbits(128),
                        qop=('auth', ), opaque='%x' % getrandbits(128), algorithm='MD5')
            return response
        elif prove(req.authorization) != req.authorization.response:
            return Response('Unauthorized.', 403)
        return f(env, req, **kwargs)
    return dec


def index(environ, request):
    """NotImplemented -- only used in text/html"""
    response = Response('It works!', 200)
    return response


@login
def account(environ, request):
    """returns account details"""
    
    rnd_time = gmtime(time() - 1000*random())
    ts = strftime('%Y-%m-%dT%H:%M:%SZ', rnd_time)
    d = { "created_at": ts, "activated_at": ts,
          "subscription_expires_at": None,
          "updated_at": ts, "subscribed": False,
          "domain": environ['host'], "id": 12345,
          "private_items": True,
          "domain_home_page": None,
          "email": "info@example.org",
          "alpha": False,
          "items": []
         }
    
    return Response(json.dumps(d), 200, content_type='application/json; charset=utf-8')
    

@login
def items(environ, request):
    '''list items from user'''
    
    ParseResult = urlparse(request.url)
    if ParseResult.query == '':
        return Response('Nothing to see here', 200)
    
    params = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
    List = []
    try:
        ipp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        return Response('Bad Request.', 400)
    
    print db.accounts.find({'email': email})[0]
    items = db.accounts.find({'email': email})[0]['items']
    # if query.count() != 1:
    #     return Response(json.dumps([]), 200, content_type='application/json; charset=utf-8')
    # for i, mem in enumerate([entry_list[x*ipp:(x+1)*ipp]
    #                             for x in range(len(entry_list)/ipp+1)] ):
    for item in items[ipp*(page-1):ipp*page]:
        print item
        List.append(Item('name', getrandbits(12)).__dict__)
    
    return Response(json.dumps(List), 200, content_type='application/json; charset=utf-8')
    

@login
def items_new(environ, request):
    '''generates a new key for upload process'''
    
    id = sessions.new(request.authorization.username)
    
    d = { "url": "http://my.cl.ly",
          "params": { "acl":"public-read",
                      "key": id
                    },
        }
    
    return Response(json.dumps(d), 200, content_type='application/json; charset=utf-8')


def upload_file(environ, request):
    '''upload file, when authorized with `key`'''
    
    if not request.form.get('key') in sessions:
        return Response('Unauthorized.', 403)
    
    account = sessions.get(request.form.get('key'))['account']
    ts = strftime('%Y-%m-%dT%H:%M:%SZ')
    obj = request.files.get('file')
    if not obj:
        return Response('Bad Request.', 400)
    
    id = fs.put(obj, filename=obj.filename, upload_date=ts, content_type=obj.mimetype,
                account=account)
    
    query = db.accounts.find({'email': account})[:]
    acc = query[:][0]
    items = acc['items']
    items.append(id)
    db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)
    
    obj = fs.get(id)
    
    d = { "name": obj.name,
          "href": 'http://' + environ['host'] + "/items/" + str(id),
          "content_url": 'http://' + environ['host'] + "/items/"+ str(id),
          "created_at": obj.upload_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
          "redirect_url": None,
          "deleted_at": None,
          "private": False,
          "updated_at": obj.upload_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
          #"remote_url": "http://f.cl.ly/items/070c0T2I0y3p0p3P053c/Bildschirmfoto%202011-08-26%20um%2022.14.39.png",
          "view_counter": 1,
          "url": 'http://' + environ['host'] + "/items/"+ str(id),
          "id": 8793473, "icon": "http://my.cl.ly/images/new/item-types/image.png",
          "thumbnail_url": 'http://' + environ['host'] + '/thumb/' + str(id),
          "subscribed": False, "source": "Cloud/1.5.1 CFNetwork/520.0.13 Darwin/11.1.0 (x86_64) (MacBookPro6,2)",
          "item_type": "image"}
         
    return Response(json.dumps(d), content_type='application/json')


def show(environ, request, id):
    """returns file either as direct download with human-readable, original
    filename or inline display using whitelisting"""
    
    id = ObjectId(id)
    f = fs.get(id)
    print f.content_type
    if not f.content_type in ['image/png', 'image/jpg', ]:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)


def bookmarks(environ, request):
    raise NotImplementedError
 

def register(environ, request):
    """Allows (instant) registration of new users."""
    
    if len(request.data) > 200:
        return Response('Bad Request.', 400)
    try:
        d = json.loads(request.data)
        email = d['user']['email']
        passwd = d['user']['password']
    except (ValueError, KeyError):
        return Response('Bad Request.', 400)
    
    # TODO: allow more characters, unicode -> ascii, before filter
    allowed_chars = string.digits + string.ascii_letters + '.- @'
    if filter(lambda c: not c in allowed_chars, email):
        return Response('Bad Request.', 400)
    
    if db.accounts.find({'email': email}).count() > 0:
        return Response('Not Acceptable.', 406)
    
    acc = Account(email=email, passwd=passwd, activated_at=strftime('%Y-%m-%dT%H:%M:%SZ'))
    db.accounts.insert(acc)
    
    acc['id'] = db.accounts.count()+1; del acc['_id']
    return Response(json.dumps(acc), 201)
    
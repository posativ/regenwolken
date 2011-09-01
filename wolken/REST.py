#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

# TODO: hashing passwords + salt

__version__ = "0.1.2-alpha"

from functools import wraps
from random import random, getrandbits, choice
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
from wolken import Sessions, SETTINGS

from pymongo import Connection
from pymongo.errors import DuplicateKeyError
import gridfs
from gridfs.errors import NoFile
from bson.objectid import ObjectId

sessions = Sessions(timeout=3600)

db = Connection(SETTINGS.MONGODB_HOST, SETTINGS.MONGODB_PORT)['cloudapp']
fs = gridfs.GridFS(db)
#fs = wolken.Grid('fsdb')

def Item(name, _id, **kw):
    """JSON-compatible dict representing Item"""
        
    __dict__ = {
        "href": "http://my.cl.ly/items/%s" % _id,
        "name": name,
        "private": True,
        "subscribed": False,
        "url": "http://my.cl.ly/items/%s" % _id,
        "content_url": "http://my.cl.ly/items/%s" % _id,
        "item_type": "bookmark",
        "view_counter": 0,
        "icon": "http://my.cl.ly/images/item_types/bookmark.png",
        "remote_url": "http://my.cl.ly/items/%s" % _id,
        "redirect_url": "http://my.cl.ly",
        "source": "Regenwolke/%s LeaveTheCloud/Now" % __version__,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ'),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ'),
        "deleted_at": None }
        
    __dict__.update(kw)
    return __dict__
        


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
        
        if str(auth.qop) == 'auth':# and auth.nc and auth.cnonce:
            A2 = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth', md5('GET:' + auth.uri)])
            return md5(A1(auth) + ':' + A2)
        else:
            # compatibility with RFC 2069: https://tools.ietf.org/html/rfc2069
            A2 = ':'.join([auth.nonce, md5('GET:' + auth.uri)])
            return md5(A1(auth) + ':' + A2)

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


@login
def account(environ, request):
    """returns account details"""
    
    rnd_time = gmtime(time() - 1000*random())
    ts = strftime('%Y-%m-%dT%H:%M:%SZ', rnd_time)
    d = { "created_at": ts, "activated_at": ts,
          "subscription_expires_at": None,
          "updated_at": ts, "subscribed": False,
          "domain": conf.HOSTNAME, "id": 12345,
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
    
    items = db.accounts.find({'email': email})[0]['items'][::-1]
    for item in items[ipp*(page-1):ipp*page]:
        obj = fs.get(item)
        List.append(Item(obj.filename, obj._id))
    
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
    
    def genId(length=8, charset=string.ascii_lowercase+string.digits):
        """generates a pseudorandom string of a-z0-9 of given length"""
        return ''.join([choice(charset) for x in xrange(length)])
    
    if not request.form.get('key') in sessions:
        return Response('Unauthorized.', 403)
    
    account = sessions.get(request.form.get('key'))['account']
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    obj = request.files.get('file')
    if not obj:
        return Response('Bad Request.', 400)
    
    while True:
        _id = genId(8)
        try:
            fs.put(obj, _id=_id ,filename=obj.filename.replace('\u0000', ''),
                   upload_date=timestamp, content_type=obj.mimetype,
                   account=account)
            break
        except DuplicateKeyError:
            pass
    
    query = db.accounts.find({'email': account})[:]
    acc = query[:][0]
    items = acc['items']
    items.append(_id)
    db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)
    
    obj = fs.get(_id)
    url = 'http://' + SETTINGS.HOSTNAME + "/items/" + _id
        
    d = { "name": obj.filename,
          "href": url,
          "content_url": url,
          "created_at": timestamp,
          "redirect_url": None,
          "deleted_at": None,
          "private": False,
          "updated_at": timestamp,
          #"remote_url": "http://f.cl.ly/items/070c0T2I0y3p0p3P053c/Bildschirmfoto%202011-08-26%20um%2022.14.39.png",
          "view_counter": 1,
          "url": url,
          "id": _id, "icon": "http://my.cl.ly/images/new/item-types/image.png",
          "thumbnail_url": 'http://' + SETTINGS.HOSTNAME + '/thumbs/' + obj._id,
          "subscribed": False, "source": "Cloud/1.5.1 CFNetwork/520.0.13 Darwin/11.1.0 (x86_64) (MacBookPro6,2)",
          "item_type": "image"}
         
    return Response(json.dumps(d), content_type='application/json')


def show(environ, request, id):
    """returns file either as direct download with human-readable, original
    filename or inline display using whitelisting"""
    
    try:
        f = fs.get(id)
    except NoFile:
        return Response('File not found!', 404)
    if not f.content_type in ['image/png', 'image/jpg', ]:
        return Response(f, content_type=f.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(f.filename)})
    return Response(f, content_type=f.content_type)


def bookmarks(environ, request):
    raise NotImplementedError
 

def register(environ, request):
    """Allows (instant) registration of new users."""
    
    if len(request.data) > 200:
        return Response('Request Entity Too Large', 413)
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
    
    acc['id'] = db.accounts.count()+1; del acc['_id'] # JSONEncoder can't handle ObjectId
    return Response(json.dumps(acc), 201)
    
@login
def account_stats(environ, request):

    d = {'items': 42, 'views': 1337}
    return Response(json.dumps(d), 200)

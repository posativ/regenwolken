#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

# TODO: hashing passwords + salt
# TODO: rework json Item generation and feature updated_at timestamp

__version__ = "0.1.2-alpha"

from random import getrandbits, choice, randint
from urlparse import urlparse
from time import strftime, gmtime
from datetime import datetime
import hashlib
import string

try:
    import json
except ImportError:
    import simplejson as json

from werkzeug.wrappers import Response
from wolken import Sessions, SETTINGS, Struct

from pymongo import Connection
from pymongo.errors import DuplicateKeyError
from gridfs.errors import NoFile

sessions = Sessions(timeout=3600)

db = Connection(SETTINGS.MONGODB_HOST, SETTINGS.MONGODB_PORT)['cloudapp']

from wolken.mongonic import GridFS
fs = GridFS(db)
#fs = wolken.Grid('fsdb')

HOSTNAME = SETTINGS.HOSTNAME


def Item(obj, **kw):
    """JSON-compatible dict representing Item.  
    
        href:           used for renaming -> http://developer.getcloudapp.com/rename-item
        name:           item's name, taken from filename
        private:        returns in longer hash (not needed imho)
        subscribed:     true or false, when paid for “Pro”
        url:            url to this file
        content_url:    <unknown>
        item_type:      image, bookmark, ... there are more
        view_counter:   obviously
        icon:           some picture to display `item_type`
        remote_url:     <unknown>
        thumbnail_url:  <url to thumbnail, when used?>
        redirect_url:   <unknown>
        source:         client referrer
        created_at:     timestamp created – '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:     timestamp updated – '%Y-%m-%dT%H:%M:%SZ' UTC
        deleted_at:     timestamp deleted – '%Y-%m-%dT%H:%M:%SZ' UTC
    """
    
    x = {}
    if isinstance(obj, dict):
        obj = Struct(**obj)
    
    __dict__ = {
        "href": "http://%s/items/%s" % (HOSTNAME, obj._id),
        "private": True,
        "subscribed": True,
        "item_type": obj.item_type,
        "view_counter": obj.view_counter,
        "icon": "http://%s/images/item_types/%s.png" % (HOSTNAME, obj.item_type),
        "source": "Regenwolken/%s LeaveTheCloud/Now" % __version__,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "deleted_at": None }
    
    if obj.item_type == 'bookmark':
        x['name'] = obj.name
        x['url'] = 'http://' + HOSTNAME + '/' + obj.short_id
        x['content_url'] = x['url']
        x['remote_url'] = None
        x['redirect_url'] = obj.redirect_url
    else:
        x['name'] = obj.filename
        x['url'] = 'http://' + HOSTNAME + '/' + obj.short_id
        x['content_url'] = x['url'] + '/' + obj.filename
        x['remote_url'] = x['url']
        x['thumbnail_url'] = x['url'] # TODO: thumbails
        x['redirect_url'] = None
    
    __dict__.update(x)    
    __dict__.update(kw)
    return __dict__
        


def Account(email, passwd, **kw):
    """JSON-compatible dict representing cloudapp's account
    
        domain:           custom domain, only in Pro available
        domain_home_page: http://developer.getcloudapp.com/view-domain-details
        private_items:    <unknown>
        subscribed:       Pro feature, custom domain... we don't need this.
        alpha:            <unkown> wtf?
        created_at:       timestamp created – '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:       timestamp updated – '%Y-%m-%dT%H:%M:%SZ' UTC
        activated_at:     timestamp account activated, per default None
        items:            (not official) list of items by this account
        email:            username of this account, characters can be any
                          of "a-zA-Z0-9.- @"
        password:         cleartext password TODO: hashing
    """
    
    __dict__ = {
        'domain': None,
        'domain_home_page': None,
        'private_items': True,
        'subscribed': False,
        'alpha': False,
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'activated_at': None,
        "items": [],
        'email': email,
        'passwd': passwd
    }
    
    __dict__.update(kw)
    return __dict__
    

def gen(length=8, charset=string.ascii_lowercase+string.digits):
    """generates a pseudorandom string of a-z0-9 of given length"""
    return ''.join([choice(charset) for x in xrange(length)])


def login(f):
    """login decorator using HTTP Digest Authentication.  Pattern based on
    http://flask.pocoo.org/docs/patterns/viewdecorators/"""
    
    def md5(data):
        return hashlib.md5(data).hexdigest()
    
    def prove(req):
        """calculates  digest response (MD5 and qop)"""
        
        def A1(auth):
            query = db.accounts.find({'email': auth.username})
            if query.count() == 1:
                passwd = query[0]['passwd']
            else:
                passwd = '%x' % getrandbits(256)
            return md5(auth.username + ':' + auth.realm + ':' + passwd)
            
        auth = req.authorization
        if str(auth.get('qop', '')) == 'auth':
            A2 = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth',
                           md5(req.method + ':' + auth.uri)])
            return md5(A1(auth) + ':' + A2)
        else:
            # compatibility with RFC 2069: https://tools.ietf.org/html/rfc2069
            A2 = ':'.join([auth.nonce, md5(req.method + ':' + auth.uri)])
            return md5(A1(auth) + ':' + A2)

    def dec(env, req, *args, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Digest Auth failed."""
        if not req.authorization:
            response = Response(status=401)
            response.www_authenticate.set_digest('Application', nonce='%x' % getrandbits(128),
                        qop=('auth', ), opaque='%x' % getrandbits(128), algorithm='MD5')
            return response
        elif prove(req) != req.authorization.response:
            return Response('Unauthorized.', 403)
        return f(env, req, *args, **kwargs)
    return dec


@login
def account(environ, request):
    """returns account details, see Account for furhter details.  Also see
    http://developer.getcloudapp.com/view-account-details"""
    
    email = request.authorization.username
    acc = db.accounts.find({'email': email})[0]
    acc['id'] = int(str(acc['_id']), 16)
    acc['subscribed'] = True
    acc['subscription_expires_at'] = '2012-12-21'
    acc['domain'] = HOSTNAME
    
    del acc['_id']; del acc['items']
    return Response(json.dumps(acc), 200, content_type='application/json; charset=utf-8')


@login
def account_stats(environ, request):
    
    email = request.authorization.username
    items = db.accounts.find_one({'email': email})['items']
    views = 0
    for item in items:
        views += db.items.find_one({'_id': item})['view_counter']
    
    d = {'items': len(items), 'views': views}
    return Response(json.dumps(d), 200)
    

@login
def items(environ, request):
    '''list items from user
    
        Options Hash (opts):

        :page (Integer) — default: 1 —

        Page number starting at 1
        :per_page (Integer) — default: 5 —

        Number of items per page
        :type (String) — default: 'image' —

        Filter items by type (image, bookmark, text, archive, audio, video, or unknown)
        :deleted (Boolean) — default: true —

        Show trashed drops
    '''
    
    ParseResult = urlparse(request.url)
    params = {'per_page': '5', 'page': '1', 'type': 'image', 'deleted': True}
    
    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        params.update(query)
    
    listing = []
    try:
        ipp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        return Response('Bad Request.', 400)
    
    # TODO: filter by type and deleted
    items = db.accounts.find_one({'email': email})['items']
    for item in items[ipp*(page-1):ipp*page]:
        cur = Struct(**db.items.find_one({'_id': item}))
        if cur.item_type == 'bookmark':
            x = Item(cur)
        else:
            x = Item(fs.get(item))
        listing.append(x)
    
    return Response(json.dumps(listing), 200, content_type='application/json; charset=utf-8')
    

@login
def items_new(environ, request):
    '''generates a new key for upload process.  Timeout after 60 minutes!'''
    
    key = sessions.new(request.authorization.username)
    d = { "url": "http://my.cl.ly",
          "params": { "acl":"public-read",
                      "key": key
                    },
        }
    
    return Response(json.dumps(d), 200, content_type='application/json; charset=utf-8')


def upload_file(environ, request):
    '''upload file, when authorized with `key`'''
    
    if not request.form.get('key') in sessions:
        return Response('Unauthorized.', 403)
    
    account = sessions.get(request.form.get('key'))['account']
    timestamp = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    obj = request.files.get('file')
    if not obj:
        return Response('Bad Request.', 400)
    
    while True:
        _id = gen(12, charset=string.digits)
        if obj.filename.find(u'\x00') > 0:
            filename = obj.filename[:-1]
        else:
            filename = obj.filename
        
        try:
            fs.put(obj, _id=_id ,filename=filename, created_at=timestamp,
                   content_type=obj.mimetype, account=account, view_counter=0,
                   short_id=gen(randint(3,8)), updated_at=timestamp)
            break
        except DuplicateKeyError:
            pass
    
    acc = db.accounts.find_one({'email': account})
    items = acc['items']
    items.append(_id)
    db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)
    
    obj = fs.get(_id)
    return Response(json.dumps(Item(obj)), content_type='application/json')


#@login
def view_item(environ, request, short_id):
    '''Implements: View Item.  http://developer.getcloudapp.com/view-item.
    Only via `Accept: application/json` accessible, returns 404 Not Found, if
    URL does not exist.'''
    
    if short_id.startswith('-'):
        cur = db.items.find_one({'short_id': short_id})
        if not cur:
            return Response('Item not found!', 404)
        x = Item(cur)
    else:
        try:
            obj = fs.get(short_id=short_id)
        except NoFile:
            return Response('File not found!', 404)
        x = Item(obj)
             
    return Response(json.dumps(x), 200)


@login
def bookmark(environ, request):
    
    def insert(name, redirect_url):
        
        _id = gen(12, charset=string.digits)
        short_id = '-' + gen(randint(3,6))
        
        x = {
            'name': name,
            '_id': _id,
            'short_id': short_id,
            'redirect_url': redirect_url,
            'item_type': 'bookmark',
            'view_counter': 0
        }
        
        item = Item(x)
        
        db.items.insert(x)
        
        print request.authorization
        acc = db.accounts.find_one({'email': request.authorization.username})
        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)
        
        return item
    
    try:
        data = json.loads(request.data)
        data = data['item']
    except (ValueError, KeyError):
        return Response('Unprocessable Entity.', 422)
        
    if isinstance(data, list):
        L = [insert(d['name'], d['redirect_url']) for d in data]
        return Response(json.dumps(L), 200)
    else:
        I = insert(data['name'], data['redirect_url'])
        return Response(json.dumps(I), 200)


def register(environ, request):
    """Allows (instant) registration of new users.  Invokes Account() and
    is saved directly into database."""
    
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
    
    acc = Account(email=email, passwd=passwd,
                  activated_at=strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()))
    db.accounts.insert(acc)
    
    acc['id'] = db.accounts.count()+1; del acc['_id'] # JSONEncoder can't handle ObjectId
    return Response(json.dumps(acc), 201)

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
from time import strftime
from datetime import datetime
import hashlib
import string

try:
    import json
except ImportError:
    import simplejson as json

from werkzeug.wrappers import Response
from wolken import Sessions, SETTINGS

from pymongo import Connection
from pymongo.errors import DuplicateKeyError
from gridfs.errors import NoFile

sessions = Sessions(timeout=3600)

db = Connection(SETTINGS.MONGODB_HOST, SETTINGS.MONGODB_PORT)['cloudapp']

from wolken.mongonic import GridFS
fs = GridFS(db)
#fs = wolken.Grid('fsdb')

HOSTNAME = SETTINGS.HOSTNAME


def Item(_id, name, short, **kw):
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
        created_at:     timestamp created – '%Y-%m-%dT%H:%M:%SZ'
        updated_at:     timestamp updated – '%Y-%m-%dT%H:%M:%SZ'
        deleted_at:     timestamp deleted – '%Y-%m-%dT%H:%M:%SZ'
    """
        
    __dict__ = {
        "href": "http://%s/items/%s" % (HOSTNAME, _id),
        "name": name,
        "private": True,
        "subscribed": False,
        "url": "http://%s/%s" % (HOSTNAME, short),
        "content_url": "http://%s/%s/%s" % (HOSTNAME, short, name),
        "item_type": "bookmark",
        "view_counter": 0,
        "icon": "http://%s/images/item_types/bookmark.png" % HOSTNAME,
        "remote_url": "http://%s/%s/%s" % (HOSTNAME, short, name),
        "redirect_url": None, #"http://%s" % HOSTNAME,
        "source": "Regenwolken/%s LeaveTheCloud/Now" % __version__,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ'),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ'),
        "deleted_at": None }
        
    __dict__.update(kw)
    return __dict__
        


def Account(email, passwd, **kw):
    """JSON-compatible dict representing cloudapp's account
    
        domain:           custom domain, only in Pro available
        domain_home_page: http://developer.getcloudapp.com/view-domain-details
        private_items:    <unknown>
        subscribed:       Pro feature, custom domain... we don't need this.
        alpha:            <unkown> wtf?
        created_at:       timestamp created – '%Y-%m-%dT%H:%M:%SZ'
        updated_at:       timestamp updated – '%Y-%m-%dT%H:%M:%SZ'
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
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ'),
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
    
    def prove(auth):
        """calculates  digest response (MD5 and qop)"""
        
        def A1(auth):
            query = db.accounts.find({'email': auth.username})
            if query.count() == 1:
                passwd = query[0]['passwd']
            else:
                passwd = '%x' % getrandbits(256)
            return md5(auth.username + ':' + auth.realm + ':' + passwd)
        
        if str(auth.qop) == 'auth':
            A2 = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth', md5('GET:' + auth.uri)])
            return md5(A1(auth) + ':' + A2)
        else:
            # compatibility with RFC 2069: https://tools.ietf.org/html/rfc2069
            A2 = ':'.join([auth.nonce, md5('GET:' + auth.uri)])
            return md5(A1(auth) + ':' + A2)

    def dec(env, req, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Digest Auth failed."""
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
    items = db.accounts.find({'email': email})[0]['items']
    views = 0
    for item in items:
        views += fs.get(item).view_counter
    
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
    
    List = []
    try:
        ipp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        return Response('Bad Request.', 400)
    
    # TODO: filter by type and deleted
    items = db.accounts.find({'email': email})[0]['items'][::-1]
    for item in items[ipp*(page-1):ipp*page]:
        obj = fs.get(item)
        item_type = obj.content_type.split('/', 1)[0]
        ts = obj.upload_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        x = Item(name=obj.filename, _id=item, short=obj.url, created_at=ts,
                 updated_at=ts, view_counter=obj.view_counter, item_type=item_type)
        List.append(x)
    
    return Response(json.dumps(List), 200, content_type='application/json; charset=utf-8')
    

@login
def items_new(environ, request):
    '''generates a new key for upload process.  Timeout after 60 minutes!'''
    
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
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
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
            fs.put(obj, _id=_id ,filename=filename.replace(r'\x00', ''),
                   created_at=timestamp, content_type=obj.mimetype,
                   account=account, view_counter=0, url=gen(randint(3,8)),
                   updated_at=timestamp)
            break
        except DuplicateKeyError:
            pass
    
    acc = db.accounts.find_one({'email': account})
    items = acc['items']
    items.append(_id)
    db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)
    
    obj = fs.get(_id)
    item_type = obj.content_type.split('/', 1)[0]
    
    new = Item(name=obj.filename, _id=_id, short=obj.url,
               created_at=timestamp, updated_at=timestamp,
               view_counter=0, item_type=item_type)
         
    return Response(json.dumps(new), content_type='application/json')


def view_item(environ, request, short):
    '''Implements: View Item.  http://developer.getcloudapp.com/view-item.
    Only via `Accept: application/json` accessible, returns 404 Not Found, if
    URL does not exist.'''
    
    try:
        f = fs.get(url=short)
    except NoFile:
        return Response('File not found!', 404)
        
    i = Item(_id=f._id, name=f.filename, short=f.url,
             item_type=f.content_type, created_at=f.created_at,
             updated_at=f.updated_at, view_counter=f.view_counter)
             
    return Response(json.dumps(i), 200)


def bookmark(environ, request):
    
    def insert(name, redirect_url):
        
        _id = gen(randint(3,12), charset=string.digits)
        short = '-' + gen(randint(3,6))
        item = Item(_id=_id, name=name, short=short, redirect_url=redirect_url)
        item['name'] = name
        item['content_url'] = item['url']
        item['remote_url'] = None
        
        item['_id'] = _id
        db.items.insert(item)
        
        del item['_id']
        return item
    
    try:
        data = json.loads(request.data)
        data = data['item']
    except (ValueError, KeyError):
        return Response('Bad Request.', 400)
        
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
    
    acc = Account(email=email, passwd=passwd, activated_at=strftime('%Y-%m-%dT%H:%M:%SZ'))
    db.accounts.insert(acc)
    
    acc['id'] = db.accounts.count()+1; del acc['_id'] # JSONEncoder can't handle ObjectId
    return Response(json.dumps(acc), 201)

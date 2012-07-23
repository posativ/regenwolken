#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.4"

from os import urandom
from random import choice, getrandbits
from base64 import standard_b64encode
from urlparse import urlparse
from urllib import quote, unquote
from time import strftime, gmtime
import hashlib
import string

try:
    import json
except ImportError:
    import simplejson as json

from werkzeug.wrappers import Response
from werkzeug.utils import secure_filename
from regenwolken import Sessions, conf, Struct

from pymongo import Connection, DESCENDING
from pymongo.errors import DuplicateKeyError
from gridfs.errors import NoFile

sessions = Sessions(timeout=3600)

db = Connection(conf.MONGODB_HOST, conf.MONGODB_PORT)[conf.MONGODB_NAME]
db.items.create_index('short_id')
db.accounts.create_index('email')

from regenwolken.mongonic import GridFS
fs = GridFS(db)

def Item(obj, **kw):
    """JSON-compatible dict representing Item.

        href:           used for renaming -> http://developer.getcloudapp.com/rename-item
        name:           item's name, taken from filename
        private:        requires auth when viewing
        subscribed:     true or false, when paid for “Pro”
        url:            url to this file
        content_url:    <unknown>
        item_type:      image, bookmark, ... there are more
        view_counter:   obviously
        icon:           some picture to display `item_type`
        remote_url:     <unknown>, href + quoted name
        thumbnail_url:  <url to thumbnail, when used?>
        redirect_url:   redirection url in bookmark items
        source:         client name
        created_at:     timestamp created – '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:     timestamp updated – '%Y-%m-%dT%H:%M:%SZ' UTC
        deleted_at:     timestamp deleted – '%Y-%m-%dT%H:%M:%SZ' UTC
    """

    x = {}
    if isinstance(obj, dict):
        obj = Struct(**obj)


    __dict__ = {
        "href": "http://%s/items/%s" % (conf.HOSTNAME, obj._id),
        "private": obj.private,
        "subscribed": True,
        "item_type": obj.item_type,
        "view_counter": obj.view_counter,
        "icon": "http://%s/images/item_types/%s.png" % (conf.HOSTNAME, obj.item_type),
        "source": obj.source,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "deleted_at": None }

    if obj.item_type == 'bookmark':
        x['name'] = obj.name
        x['url'] = 'http://' + conf.HOSTNAME + '/' + obj.short_id
        x['content_url'] = x['url'] + '/content'
        x['remote_url'] = None
        x['redirect_url'] = obj.redirect_url
    else:
        x['name'] = obj.filename
        x['url'] = 'http://' + conf.HOSTNAME + '/' + obj.short_id
        x['content_url'] = x['url'] + '/' + secure_filename(obj.filename)
        x['remote_url'] = x['url'] + '/' + quote(obj.filename)
        x['thumbnail_url'] = x['url'] # TODO: thumbails
        x['redirect_url'] = None

    try:
        x['created_at'] = obj.created_at
        x['updated_at'] = obj.updated_at
        x['deleted_at'] = obj.deleted_at
        if obj.deleted_at:
            x['icon'] = "http://%s/images/item_types/trash.png" % conf.HOSTNAME
    except AttributeError:
        pass

    __dict__.update(x)
    __dict__.update(kw)
    return __dict__


def Account(account, **kw):
    """JSON-compatible dict representing cloudapp's account

        domain:           custom domain, only in Pro available
        domain_home_page: http://developer.getcloudapp.com/view-domain-details
        private_items:    http://developer.getcloudapp.com/change-default-security
        subscribed:       Pro feature, custom domain... we don't need this.
        alpha:            <unkown> wtf?
        created_at:       timestamp created – '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:       timestamp updated – '%Y-%m-%dT%H:%M:%SZ' UTC
        activated_at:     timestamp account activated, per default None
        items:            (not official) list of items by this account
        email:            username of this account, characters can be any
                          of "a-zA-Z0-9.- @" and no digit-only name is allowed
        password:         password, md5(username + ':' + realm + ':' + passwd)
    """

    x = {
        'id': account['id'],
        'domain': conf.HOSTNAME,
        'domain_home_page': None,
        'private_items': False,
        'subscribed': True,
        'subscription_expires_at': '2112-12-21',
        'alpha': False,
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'activated_at': None,
        "items": [],
        'email': account['email'],
        'passwd': A1(account['email'], account['passwd'])
    }

    x.update(kw)
    return x


def md5(data):
    """returns md5 of data has hexdigest"""
    return hashlib.md5(data).hexdigest()

def A1(username, passwd, realm='Application'):
    """A1 HTTP Digest Authentication"""
    return md5(username + ':' + realm + ':' + passwd)


def prove_auth(req):
    """calculates digest response (MD5 and qop)"""
    auth = req.authorization

    account = db.accounts.find_one({'email': auth.username})
    _A1 = account['passwd'] if account else standard_b64encode(urandom(16))

    if str(auth.get('qop', '')) == 'auth':
        A2 = ':'.join([auth.nonce, auth.nc, auth.cnonce, 'auth',
                       md5(req.method + ':' + auth.uri)])
        return md5(_A1 + ':' + A2)
    else:
        # compatibility with RFC 2069: https://tools.ietf.org/html/rfc2069
        A2 = ':'.join([auth.nonce, md5(req.method + ':' + auth.uri)])
        return md5(_A1 + ':' + A2)


def gen(length=8, charset=string.ascii_lowercase+string.digits):
    """generates a pseudorandom string of a-z0-9 of given length"""
    return ''.join([choice(charset) for x in xrange(length)])


def login(f):
    """login decorator using HTTP Digest Authentication.  Pattern based on
    http://flask.pocoo.org/docs/patterns/viewdecorators/

    -- http://developer.getcloudapp.com/usage/#authentication"""

    def dec(env, req, *args, **kwargs):
        """This decorater function will send an authenticate header, if none
        is present and denies access, if HTTP Digest Auth failed."""
        if not req.authorization:
            response = Response('Unauthorized', 401, content_type='application/json; charset=utf-8')
            response.www_authenticate.set_digest('Application', nonce=standard_b64encode(urandom(32)),
                        qop=('auth', ), opaque='%x' % getrandbits(128), algorithm='MD5')
            return response
        else:
            account = db.accounts.find_one({'email': req.authorization.username})
            if account and account['activated_at'] == None:
                return Response('[ "Your account hasn\'t been activated. Please ' \
                                + 'check your email and activate your account." ]', 409)
            elif prove_auth(req) != req.authorization.response:
                return Response('Forbidden', 403)
        return f(env, req, *args, **kwargs)
    return dec


@login
def account(environ, request):
    """returns account details, and update given keys.

    -- http://developer.getcloudapp.com/view-account-details
    -- http://developer.getcloudapp.com/change-default-security
    -- http://developer.getcloudapp.com/change-email
    -- http://developer.getcloudapp.com/change-password

    PUT: accepts every new password (stored in plaintext) and like /register
    no digit-only "email" address is allowed."""

    account = db.accounts.find_one({'email': request.authorization.username})

    if request.method == 'GET':
        pass
    elif request.method == 'PUT':
        try:
            _id = account['_id']
            data = json.loads(request.data)['user']
        except ValueError:
            return Response('Unprocessable Entity', 422)

        if len(data.keys()) == 1 and 'private_items' in data:
            db.accounts.update({'_id': _id}, {'$set': {'private_items': data['private_items']}})
            account['private_items'] = data['private_items']
        elif len(data.keys()) == 2 and 'current_password' in data:
            if not account['passwd'] == A1(account['email'], data['current_password']):
                return Response('Forbidden', 403)

            if data.has_key('email'):
                if filter(lambda c: not c in conf.ALLOWED_CHARS, data['email']) \
                or data['email'].isdigit(): # no numbers allowed
                    return Response('Bad Request', 400)
                if db.accounts.find_one({'email': data['email']}) and \
                account['email'] != data['email']:
                    return Response('User already exists', 406)

                new = {'email': data['email'],
                       'passwd': A1(data['email'], data['current_password'])}
                db.accounts.update({'_id': _id}, {'$set': new})
                account['email'] = new['email']
                account['passwd'] = new['passwd']

            elif data.has_key('password'):
                passwd = A1(account['email'], data['password'])
                db.accounts.update({'_id': _id}, {'$set': {'passwd': passwd}})
                account['passwd'] = passwd

            else:
                return Response('Bad Request', 400)

    db.accounts.update({'_id': account['_id']}, {'$set':
            {'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())}})
    del account['_id']; del account['items']; del account['passwd']
    return Response(json.dumps(account), 200, content_type='application/json; charset=utf-8')


@login
def account_stats(environ, request):
    '''view account's item count and overall views.

    -- http://developer.getcloudapp.com/view-account-stats'''

    email = request.authorization.username
    items = db.accounts.find_one({'email': email})['items']
    views = 0
    for item in items:
        views += db.items.find_one({'_id': item})['view_counter']

    d = {'items': len(items), 'views': views}
    return Response(json.dumps(d), 200, content_type='application/json; charset=utf-8')


def view_domain(environ, request, domain):
    '''returns conf.HOSTNAME. Always.'''

    return Response('{"home_page": "http://%s"}' % conf.HOSTNAME,
                     200, content_type='application/json; charset=utf-8')


@login
def items(environ, request):
    '''list items from user.  Optional query parameters:

            - page (int)     — default: 1
            - per_page (int) – default: 5
            - type (str)     – default: None, filter by image, bookmark, text,
                                             archive, audio, video, or unknown
            - deleted (bool) – default: False, show trashed items

    -- http://developer.getcloudapp.com/list-items'''

    ParseResult = urlparse(request.url)
    params = {'per_page': '5', 'page': '1', 'type': None, 'deleted': False,
              'source': None}

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        params.update(query)

    listing = []
    try:
        ipp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        return Response('Bad Request', 400)

    query = {'account': email}
    if params['type'] != None:
        query['item_type'] = params['type']
    if params['deleted'] == False:
        query['deleted_at'] = None
    if params['source'] != None:
        query['source'] = {'$regex': '^' + unquote(params['source'])}

    items = db.items.find(query)
    for item in items.sort('updated_at', DESCENDING)[ipp*(page-1):ipp*page]:
        listing.append(Item(fs.get(_id=item['_id'])))

    return Response(json.dumps(listing[::-1]), 200, content_type='application/json; charset=utf-8')


@login
def items_new(environ, request):
    '''generates a new key for upload process.  Timeout after 60 minutes!

    -- http://developer.getcloudapp.com/upload-file
    -- http://developer.getcloudapp.com/upload-file-with-specific-privacy'''

    acc = db.accounts.find_one({'email': request.authorization.username})
    ParseResult = urlparse(request.url)
    privacy = 'private' if acc['private_items'] else 'public-read'

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        privacy = 'private' if query['item[private]'] else 'public-read'


    key = sessions.new(request.authorization.username)
    d = { "url": "http://my.cl.ly",
          "max_upload_size": conf.MAX_CONTENT_LENGTH,
          "params": { "acl": privacy,
                      "key": key
                    },
        }

    return Response(json.dumps(d), 200, content_type='application/json; charset=utf-8')


def upload_file(environ, request):
    '''upload file, when authorized with `key`

    -- http://developer.getcloudapp.com/upload-file'''

    if not request.form.get('key') in sessions:
        return Response('Forbidden', 403)

    account = sessions.get(request.form.get('key'))['account']
    acc = db.accounts.find_one({'email': account})
    source = request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0]
    privacy = request.form.get('acl', acc['private_items'])
    if isinstance(privacy, (str, unicode)):
        privacy = True if privacy == 'private' else False
    timestamp = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    obj = request.files.get('file')
    if not obj:
        return Response('Bad Request', 400)

    if obj.filename.find(u'\x00') == len(obj.filename)-1:
        filename = obj.filename[:-1]
    else:
        filename = obj.filename

    _id = str(getrandbits(32))
    retry_count = 3
    short_id_length = conf.SHORT_ID_MIN_LENGTH
    while True:
        try:
            fs.put(obj, _id=_id ,filename=filename, created_at=timestamp,
                   content_type=obj.mimetype, account=account, view_counter=0,
                   short_id=gen(short_id_length), updated_at=timestamp,
                   source=source, private=privacy)
            break
        except DuplicateKeyError:
            retry_count += 1
            if retry_count > 3:
                short_id_length += 1
                retry_count = 1

    items = acc['items']
    items.append(_id)
    db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

    obj = fs.get(_id)
    return Response(json.dumps(Item(obj)), content_type='application/json; charset=utf-8')


def view_item(environ, request, short_id):
    '''Implements: View Item.  http://developer.getcloudapp.com/view-item.
    Only via `Accept: application/json` accessible, returns 404 Not Found, if
    URL does not exist.

    -- http://developer.getcloudapp.com/view-item'''

    if short_id.startswith('-'):
        cur = db.items.find_one({'short_id': short_id})
        if not cur:
            return Response('Not Found', 404)
        x = Item(cur)
    else:
        try:
            obj = fs.get(short_id=short_id)
        except NoFile:
            return Response('Not Found', 404)
        x = Item(obj)

    return Response(json.dumps(x), 200, content_type='application/json; charset=utf-8')


@login
def modify_item(environ, request, objectid):
    '''rename/delete/change privacy of an item.

    -- http://developer.getcloudapp.com/rename-item
    -- http://developer.getcloudapp.com/delete-item
    -- http://developer.getcloudapp.com/change-security-of-item'''

    item = db.items.find_one({'account': request.authorization.username,
                              '_id': objectid})
    if not item:
        return Response('Not Found', 404)

    if request.method == 'DELETE':
        item['deleted_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    elif request.method == 'PUT':
        try:
            data = json.loads(request.data)['item']
            key, value = data.items()[0]
            if not key in ['private', 'name', 'deleted_at']: raise ValueError
        except ValueError:
            return Response('Unprocessable Entity', 422)

        if key == 'name' and item['item_type'] != 'bookmark':
            item['filename'] = value
        elif key == 'private' and item['item_type'] == 'bookmark' and value \
        and not conf.ALLOW_PRIVATE_BOOKMARKS:
            pass
        else:
            item[key] = value

        item['updated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    db.items.save(item)
    item = fs.get(item['_id'])
    return Response(json.dumps(Item(item)), 200, content_type='application/json; charset=utf-8')


@login
def trash_items(environ, request):
    '''no official API call yet.  Trash items marked as deleted. Usage:
    curl -u user:pw --digest -H "Accept: application/json" -X POST http://my.cl.ly/items/trash'''

    empty = db.items.find({'account': request.authorization.username,
                          'deleted_at': {'$ne': None}})
    for item in empty:
        fs.delete(item)

    return Response(status=200)


@login
def bookmark(environ, request):
    """url shortening.

    -- http://developer.getcloudapp.com/bookmark-link"""

    def insert(name, redirect_url):

        acc = db.accounts.find_one({'email': request.authorization.username})

        _id = str(getrandbits(32))
        retry_count = 1
        short_id_length = conf.SHORT_ID_MIN_LENGTH

        while True:
            short_id = gen(short_id_length)
            if not db.items.find_one({'short_id': short_id}):
                break
            else:
                retry_count += 1
                if retry_count > 3:
                    short_id_length += 1
                    retry_count = 1

        x = {
            'account': request.authorization.username,
            'name': name,
            '_id': _id,
            'short_id': gen(short_id_length),
            'redirect_url': redirect_url,
            'item_type': 'bookmark',
            'view_counter': 0,
            'private': request.form.get('acl', acc['private_items'])
                if conf.ALLOW_PRIVATE_BOOKMARKS else False,
            'source': request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0],
            'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
            'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        }

        item = Item(x)
        db.items.insert(x)

        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

        return item

    try:
        data = json.loads(request.data)
        data = data['item']
    except (ValueError, KeyError):
        return Response('Unprocessable Entity', 422)

    if isinstance(data, list):
        L = [insert(d['name'], d['redirect_url']) for d in data]
        return Response(json.dumps(L), 200, content_type='application/json; charset=utf-8')
    else:
        I = insert(data['name'], data['redirect_url'])
        return Response(json.dumps(I), 200, content_type='application/json; charset=utf-8')


def register(environ, request):
    """Allows (instant) registration of new users.  Invokes Account() and
    is saved directly into database. No digits-only usernames are allowed.

    -- http://developer.getcloudapp.com/register"""

    if len(request.data) > 200:
        return Response('Request Entity Too Large', 413)
    try:
        d = json.loads(request.data)
        email = d['user']['email']
        if email.isdigit(): raise ValueError # no numbers as username allowed
        passwd = d['user']['password']
    except (ValueError, KeyError):
        return Response('Bad Request', 422)

    # TODO: allow more characters, unicode -> ascii, before filter
    if filter(lambda c: not c in conf.ALLOWED_CHARS, email):
        return Response('Bad Request', 422)

    if db.accounts.find_one({'email': email}) != None:
        return Response('User already exists', 406)

    if not db.accounts.find_one({"_id":"autoinc"}):
        db.accounts.insert({"_id":"_inc", "seq": 1})

    account = Account({'email': email, 'passwd': passwd,
                       'id': db.accounts.find_one({'_id': '_inc'})['seq']})
    db.accounts.update({'_id': '_inc'}, {'$inc': {'seq': 1}})
    if conf.PUBLIC_REGISTRATION:
        account['activated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    account['_id'] = account['id']
    db.accounts.insert(account)
    del account['_id']; del account['items']; del account['passwd']

    return Response(json.dumps(account), 201, content_type='application/json; charset=utf-8')

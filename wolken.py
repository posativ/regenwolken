#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.
#
#
# Wolken is a Cloud.app clone, with leave the cloud in mind.
#
# `srv/wolken.py` is a simple webserver, allows you to POST and GET files.

__version__ = "0.1.1-alpha"

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

from bottle import route, run, post, request, response
from bottle import HTTPResponse, HTTPError

import hashlib
import mimetypes
import time
import random
from urlparse import urlparse

try:
    import json
except ImportError:
    import simplejson as json

from pymongo import Connection
import gridfs
from bson.objectid import ObjectId
from uuid import uuid4

from optparse import OptionParser, make_option

class Item(dict):
    """a basic item placeholder"""
    
    def __init__(self, **kw):
        
        h = random.getrandbits(128)
        __dict__ = {
            "href": "http://my.cl.ly/items/%x" % h,
            "name": "Item Dummy",
            "private": True,
            "subscribed": False,
            "url": "http://my.cl.ly/items/%x" % h,
            "content_url": "http://my.cl.ly/items/%x" % h,
            "item_type": "bookmark",
            "view_counter": 0,
            "icon": "http://my.cl.ly/images/item_types/bookmark.png",
            "remote_url": "http://my.cl.ly/items/%x" % h,
            "redirect_url": "http://my.cl.ly",
            "source": "Regenwolke/%s LeaveTheCloud/Now Darwin/11.0.0 (x86_64) (MacBookPro5,5)" % __version__,
            "created_at": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "updated_at": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "deleted_at": None
        }
        for k,v in __dict__.iteritems():
            self[k] = v
        self.update(**kw)
    
    def to_dict(self):
        return self.dict

class Sessions:
    '''A simple in-memory session handler.  Uses dict[session_id] = (timestamp, value)
    sheme, automatic timout after 15 minutes.
    
    session_id -- uuid.uuid4().hex
    timestamp -- time.time()
    value -- sha1 hash
    '''
    
    def __init__(self):
        self.db = {}
    
    def __repr__(self):
        L = []
        for item in sorted(self.db.keys(), key=lambda k: k[0]):
            L.append('%s\t%s, %s' % (item, self.db[item][0], self.db[item][1]))
        return '\n'.join(L)
    
    def __contains__(self, item):
        self._outdated()
        return True if self.db.has_key(item) else False
    
    def _outdated(self):
        '''automatic cleanup of outdated sessions, 15 min time-to-live'''
        self.db = dict([(k, v) for k,v in self.db.items() if (time.time() - v[0]) <= 60])
    
    def get(self, session_id):
        '''returns session id'''
        self._outdated()
        for item in self.db:
            if item == session_id:
                return self.db[session_id][1]
        else:
            raise KeyError(session_id)
    
    def new(self):
        '''returns new session id'''
        
        self._outdated()
        session_id = uuid4().hex
        self.db[session_id] = (time.time(), random.getrandbits(128))
        
        return session_id

def hash(f, bs=128, length=12, encode=lambda x: x):
    """returns a truncated md5 hash of given file."""
    
    md5 = hashlib.md5()
    while True:
        data = f.read(bs)
        if not data:
            break
        md5.update(data)
    return encode(md5.hexdigest()).strip('=').lower()[:length]


# @route('/:mode#raw|inline#/:hash')
# def get(mode, hash):
#     """maps to /raw|inline/md5hash and returns the file either in download
#     mode or inline."""
#
#     filename = Storage.get(hash)
#     if filename:
#         header = dict()
#         mimetype, encoding = mimetypes.guess_type(filename)
#         if mimetype: header['Content-Type'] = mimetype
#         if encoding: header['Content-Encoding'] = encoding
#
#         if mode == 'raw':
#             name = basename(filename)
#             header['Content-Disposition'] = 'attachment; filename="%s"' % name
#
#         stats = os.stat(filename)
#         header['Content-Length'] = stats.st_size
#         lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
#         header['Last-Modified'] = lm
#
#         body = '' if request.method == 'HEAD' else open(filename, 'rb')
#         return HTTPResponse(body, header=header)

def authenticate(uri):
    
    users = {'leave@thecloud': 'now'}
    
    def md5(data):
        return hashlib.md5(data).hexdigest()
    
    def htdigest():
        '''beginning HTTP Digest Authentication'''
        
        realm = 'Application'
        nonce = md5("%d:%s" % (time.time(), realm))
        qop = 'auth'
        return {'nonce': nonce, 'realm': realm, 'auth': qop}
    
    def result(auth, digest, uri):
        """calculates  digest response (MD5 and qop)"""
        
        def A1(auth, digest):
            passwd = users.get(auth['username'], '')
            return md5(auth['username'] + ':' + digest['realm'] + ':' + passwd)
        
        def A2(request, uri):
            return request.method + ':' + uri
        
        b = ':'.join([auth['nonce'], auth['nc'], auth['cnonce'],
                      auth['qop'], md5(A2(request, uri))])
        return md5(A1(auth, digest) + ':' + b)
    
    digest = htdigest()
    HTTPAuth = HTTPError(401, "Unauthorized.", header={'WWW-Authenticate':
                    ('Digest realm="%(realm)s", nonce="%(nonce)s", '
                     'algorithm="MD5", qop=%(auth)s' % digest)})
    
    if 'Authorization' in request.header:
        
        auth = request.header['Authorization'].replace('Digest ', '').split(',')
        auth = dict([x.strip().replace('"', '').split('=') for x in auth])
        
        if filter(lambda k: not k in auth, ['qop', 'username', 'nonce', 'response', 'uri']):
            print >> sys.stderr, 'only `qop` authentication is implemented'
            print >> sys.stderr, 'see', 'http://code.activestate.com/recipes/302378-digest-authentication/'
            return HTTPError(403, 'Unauthorized')
        
        if result(auth, digest, uri) == auth['response']:
            session_id = sessions.new()
            if sys.version_info[0] == 2 and sys.version_info[1] < 6:
                response.set_cookie('_engine_session', session_id, path='/')
            else:
                response.set_cookie('_engine_session', session_id, path='/', httponly=True)
            return True
    
    return HTTPAuth


@post('/')
def upload():
    
    if not request.forms.get('key') in sessions:
        return HTTPError(403, 'Unauthorized')
    
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    obj = request.files.get('file')
    mt, enc = mimetypes.guess_type(obj.filename.strip('\x00'))
    id = fs.put(obj.file, filename=obj.filename, upload_date=ts, content_type=mt)
    
    obj = fs.get(id)
    
    d = { "name": obj.name,
          "href": 'http://' + host + "/items/" + str(id),
          "content_url": 'http://' + host + "/items/"+ str(id),
          "created_at": obj.upload_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
          "redirect_url": None,
          "deleted_at": None,
          "private": False,
          "updated_at": obj.upload_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
          #"remote_url": "http://f.cl.ly/items/070c0T2I0y3p0p3P053c/Bildschirmfoto%202011-08-26%20um%2022.14.39.png",
          "view_counter": 1,
          "url": 'http://' + host + "/items/"+ str(id),
          "id": 8793473, "icon": "http://my.cl.ly/images/new/item-types/image.png",
          "thumbnail_url": 'http://' + host + '/thumb/' + str(id),
          "subscribed": False, "source": "Cloud/1.5.1 CFNetwork/520.0.13 Darwin/11.1.0 (x86_64) (MacBookPro6,2)",
          "item_type": "image"}
    return HTTPResponse(json.dumps(d), header={'Content-Type': 'application/json; charset=utf-8'})


@route('/raindrops/com.linebreak.Raindrop.Screenshots')
def screenshots():
    return HTTPResponse(json.dump(
                { "bundle_id": "com.linebreak.Raindrop.Screenshots",
                  "version": "1.0", "creator": "Line,  break S.L.",
                  "url": "http://getcloudapp.com/",
                  "name": "Screenshots",
                  "description": "Automatically uploads screenshot files."}),
                  header={'Content-Type': 'application/json'})

@route('/items')
def items():
    
    cookie = request.get_cookie('_engine_session')
    if not cookie:
        HTTPAuth = authenticate('/items')
        if HTTPAuth != True:
            return HTTPAuth
    
    params = dict([part.split('=') for part in urlparse(request.url).query.split('&')])
    
    List = []
    for x in range(int(params['per_page'])):
        List.append(Item(name="Item Dummy %s" % (x+1)))
    
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.set_cookie('_engine_session', cookie)
    
    return json.dumps(List)


@route('/items/new')
def new():
    
    # c = request.get_cookie('_engine_session')
    # if not c in sessions:
    
    HTTPAuth = authenticate('/items/new')
    if HTTPAuth != True:
        return HTTPAuth
    
    id = sessions.new()
    print id
    
    d = { "url": "http://my.cl.ly",
          #"params": { "acl":"public-read", 'signature': sessions.get(c) },
          "params": { "acl":"public-read",
                      "key": id
                    },
        }
    return HTTPResponse(json.dumps(d),
                header={'Content-Type': 'application/json; charset=utf-8'})

@route('/items/:id')
def get(id):
    
    id = ObjectId(id)
    f = fs.get(id)
    return HTTPResponse(f, header={'Content-Type': f.content_type})


@route('/account')
def account():
    
    HTTPAuth = authenticate('/account')
    if HTTPAuth != True:
        return HTTPAuth
    
    rnd_time = time.gmtime(time.time() - 1000*random.random())
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ', rnd_time)
    d = { "created_at": ts, "activated_at": ts,
          "subscription_expires_at": None,
          "updated_at": ts, "subscribed": False,
          "domain": host, "id": 12345,
          "private_items": True,
          "domain_home_page": None,
          "email": "info@example.org",
          "alpha": False
         }
    
    body = json.dumps(d)
    
    
    response.headers['Content-Length'] = len(body)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    
    return body

if __name__ == '__main__':
    
    import bottle; bottle.debug(True)
    
    options = [
        # make_option('--proxy', dest='proxy', default=False, action='store_true',
        #              help="proxy non-matching my.cl.ly-links"),
        make_option('--bind', dest='bind', default='0.0.0.0', type=str, metavar='IP',
                     help="binding address, e.g. localhost [default: %default]"),
        make_option('--port', dest='port', default=9000, type=int, metavar='PORT',
                     help="port, e.g. 80 [default: %default]"),
        make_option('--mdb-host', dest='mongodb_host', default='localhost',
                    type=str, metavar='HOST', help="mongoDB host [default: %default]"),
        make_option('--mdb-port', dest='mongodb_port', default=27017,
                    type=int, metavar='PORT', help="mongoDB port [default: %default]"),
        ]
    
    parser = OptionParser(option_list=options, usage="usage: %prog [options] [Hostname]")
    options, args = parser.parse_args()
    
    if len(args) == 1:
        host = args[0]
    else:
        host = 'localhost'
    
    db = Connection(options.mongodb_host, options.mongodb_port)['cloudapp']
    fs = gridfs.GridFS(db)
    sessions = Sessions()
    
    run(host=options.bind, port=options.port, reloader=True)
    
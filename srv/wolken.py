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

import sys; reload(sys)
sys.setdefaultencoding('utf-8')
from datetime import timedelta

from bottle import route, run, post, request, response
from bottle import HTTPResponse, HTTPError

import hashlib
import mimetypes
import time
import random

import json

from pymongo import Connection
import gridfs
from bson.objectid import ObjectId
from uuid import uuid4

from optparse import OptionParser, make_option


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
        self.db = dict([(k, v) for k,v in self.db.items() if (time.time() - v[0]) <= 60*15])
        
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
        

def ttl2timedelta(s):
    """converts :digit:[m|h|d|w] into their equivalent datetime objects"""
    
    if not filter(lambda c: c in s, 'mhdw'):
        print >> sys.stderr, 'only m, h, d and w is supported in ttl'
        sys.exit(1)
    
    try:
        i, s = int(s[:-1]), s[-1]
    except ValueError:
        print >> sys.stderr, 'unable to convert timedelta'
    if s == 'm':
        return timedelta(minutes=i)
    elif s == 'h':
        return timedelta(hours=i)
    elif s == 'd':
        return timedelta(days=i)
    else:
        timedelta(weeks=i)

def hash(f, bs=128, length=12, encode=lambda x: x):
    """returns a truncated md5 hash of given file."""
    
    md5 = hashlib.md5()
    while True:
        data = f.read(bs)
        if not data:
            break
        md5.update(data)
    return encode(md5.hexdigest()).strip('=').lower()[:length]

# @post('/file/')
# def upload():
#     #response.headers['Content-Type'] = 'application/json'
#     response.headers['Content-Type'] = 'text/plain'
#
#     # TODO:
#     passwd = request.forms.get('passwd', None)
#     if passwd == None or not hashlib.sha1(passwd).hexdigest() == HASH:
#         return HTTPError(403, "Access denied.")
#
#     data = request.files.get('data', None)
#     if data != None:
#         data.file.seek(0, 2)
#         size = data.file.tell()
#         if size > FS_LIMIT: # 1 MiB file limit
#             return 'file too big'
#         data.file.seek(0)
#
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

@post('/')
def upload():
    
    for key in request.header.keys():
        print key + ':', request.header[key]
    
    for key in ['acl', 'signature', 'key', 'AWSAccessKeyId', 'success_action_redirect', 'policy']:
        print key, request.forms.get(key)
    
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    obj = request.files.get('file')
    mt, enc = mimetypes.guess_type(obj.filename.strip('\x00'))
    id = fs.put(obj.file, filename=obj.filename, upload_date=ts, content_type=mt)
    
    d = { "name": obj.filename,
          "href": 'http://' + host + "/items/" + str(id),
          "content_url": 'http://' + host + "/items/"+ str(id),
          "created_at": ts,
          "redirect_url": None,
          "deleted_at": None,
          "private":True,
          "updated_at": ts,
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

@route('/items/new')
def new():
    
    # for key in request.header:
    #     print key+':', request.header[key]
    c = request.get_cookie('_engine_session')
    
    if c in sessions or True:
    
        d = { "uploads_remaining": 5,
              "url": "http://f.cl.ly",
              "max_upload_size": 26214400,
              #"params": { "acl":"public-read", 'signature': sessions.get(c) },
              "params": { "acl":"public-read" },
            }
        return HTTPResponse(json.dumps(d),
                    header={'Content-Type': 'application/json; charset=utf-8'})
    else:
        return HTTPError(403, 'Unauthorized.')

@route('items/:id')
def get(id):
    
    id = ObjectId(id)
    f = fs.get(id)
    return HTTPResponse(f, header={'Content-Type': f.content_type})


@route('/account')
def auth():
    
    users = {'leave@thecloud': 'now'}
    
    def md5(data):
        return hashlib.md5(data).hexdigest()
    
    def htdigest():
        '''beginning HTTP Digest Authentication'''
        
        realm = 'Application'
        nonce = md5("%d:%s" % (time.time(), realm))
        qop = 'auth'
        return {'nonce': nonce, 'realm': realm, 'auth': qop}
    
    def result(auth, digest):
        """calculates  digest response (MD5 and qop)"""
        
        def A1(auth, digest):
            passwd = users.get(auth['username'], '')
            return md5(auth['username'] + ':' + digest['realm'] + ':' + passwd)
        
        def A2(request):
            return request.method + ':' + '/account'
        
        b = ':'.join([auth['nonce'], auth['nc'], auth['cnonce'],
                      auth['qop'], md5(A2(request))])
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
        
        if result(auth, digest) == auth['response']:
            
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
            
            session_id = sessions.new()
            response.set_cookie('_engine_session', session_id, path='/', httponly=True)
            response.headers['Content-Length'] = len(body)
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
            
            return body
        
        else:
            return HTTPAuth
    
    else:
        return HTTPAuth


if __name__ == '__main__':
    
    options = [
        ]
        
    parser = OptionParser(option_list=options, usage="usage: %prog [options] FILE")
    options, args = parser.parse_args()
    
    if len(args) == 1:
        host = args[0]
    else:
        host = 'localhost'
    
    db = Connection('localhost', 27017)['cloud']
    fs = gridfs.GridFS(db)
    sessions = Sessions()
    
    run(host='localhost', port=80)
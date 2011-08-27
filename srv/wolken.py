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
import os
from os.path import join, isdir, getmtime, basename
from datetime import timedelta, datetime

from bottle import route, run, post, request, response
from bottle import HTTPResponse, HTTPError

import hashlib
import mimetypes
import time

import json
import base64

from pymongo import Connection
import gridfs
from bson.objectid import ObjectId

FS_LIMIT = 100*2**20 # 100 Megabyte
HASH = '24efc4e1d8d7c2deedb8dbd6fb701ae1a7876775' # =~ "HalloWelt

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
        print request.forms.get(key)
    
    ts = time.strftime('%Y-%m-%dT%H:%M:%SZ')
    obj = request.files.get('file')
    mt, enc = mimetypes.guess_type(obj.filename.strip('\x00'))
    id = fs.put(obj.file, filename=obj.filename, upload_date=ts, content_type=mt)
    
    d = { "name": obj.filename,
          "href": "http://localhost/items/" + str(id),
          "content_url": "http://localhost/items/"+ str(id),
          "created_at": ts,
          "redirect_url": None,
          "deleted_at": None,
          "private":True,
          "updated_at": ts,
          "remote_url": "http://f.cl.ly/items/070c0T2I0y3p0p3P053c/Bildschirmfoto%202011-08-26%20um%2022.14.39.png",
          "view_counter": 1,
          "url": "http://localhost/items/"+ str(id),
          "id": 8793473, "icon": "http://my.cl.ly/images/new/item-types/image.png",
          "thumbnail_url": "http://thumbs.cl.ly/2r3h0z2r3z2c1S2z2S3a",
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
    d = { "uploads_remaining": 5,
          "url": "http://f.cl.ly",
          "max_upload_size": 26214400,
          "params": { "acl":"public-read" },
        }
    return HTTPResponse(json.dumps(d),
                header={'Content-Type': 'application/json; charset=utf-8'})
                
@route('items/:id')
def get(id):
    
    id = ObjectId(id)
    f = fs.get(id)
    return HTTPResponse(f, header={'Content-Type': f.content_type})
    

@route('/:identifier')
def index(identifier):
    
    if identifier == 'account':
        
        d = { "created_at":"2011-07-26T14:26:51Z",
              "activated_at":"2011-07-26T14:32:48Z",
              "subscription_expires_at": None,
              "updated_at":"2011-07-26T14:32:48Z",
              "domain": 'localhost', "id": 12345,
              "subscribed": True,
              "private_items": True,
              "domain_home_page": None,
              "email": "info@example.org",
              "alpha": False }
              
        body = json.dumps(d)
        
        header = {}
        header['Content-Length'] = len(body)
        header['Content-Type'] = 'application/json; charset=utf-8'
        
        return HTTPResponse(body, header=header)

if __name__ == '__main__':
    
    import bottle; bottle.debug(True)
    
    db = Connection('localhost', 27017)['cloud']
    fs = gridfs.GridFS(db)
    
    run(host='localhost', port=80)
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

import sys
import os
from os.path import join, isdir, getmtime, basename
from datetime import timedelta, datetime

from bottle import route, run, post, request, response
from bottle import HTTPResponse, HTTPError

import hashlib
import mimetypes
import time

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

def walk(path):
    """recursive filelisting"""
    filelist = []
    for root, dirs, files in os.walk(path):
        for file in files:
            filelist.append(join(root, file))
    return filelist


class FileStorage:
    """Wrapper class for all file access related things."""
    
    def __init__(self, datadir, ttl='3d'):
        """datadir is required, time-to-live defaults to 3 days and can be
        overwritten by single POSTs"""
        
        if not isdir(datadir):
            try:
                os.makedirs(datadir)
            except OSError:
                print >> sys.stderr, 'unable to create \'' + datadir + '\''
                sys.exit(1)
        
        self.datadir = datadir
        self.ttl = ttl2timedelta(ttl)
        
        self.db = {}
        
        self.cleanup()
        self.resume()
        
    def add(self, name, data):
        pass
        
    def get(self, hash):
        
        if hash in self.db:
            return self.db[hash]
        
    def resume(self):
        
        for path in walk(self.datadir):
            f = open(path, 'r')
            md5 = hash(f)
            self.db[md5] = path
            f.close()
    
    def cleanup(self):
        
        now = datetime.now()
        for path in walk(self.datadir):
            ts = datetime.fromtimestamp(getmtime(path))
            if ts + self.ttl < now:
                print '\'', path, '\'', 'is more than', self.ttl, 'old'

Storage = FileStorage('data')
print Storage.db.keys()

@post('/file/')
def upload():
    #response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Type'] = 'text/plain'
    
    # TODO: 
    passwd = request.forms.get('passwd', None)
    if passwd == None or not hashlib.sha1(passwd).hexdigest() == HASH:
        return HTTPError(403, "Access denied.")
    
    data = request.files.get('data', None)
    if data != None:
        data.file.seek(0, 2)
        size = data.file.tell()
        if size > FS_LIMIT: # 1 MiB file limit
            return 'file too big'
        data.file.seek(0)

@route('/:mode#raw|inline#/:hash')
def get(mode, hash):
    """maps to /raw|inline/md5hash and returns the file either in download
    mode or inline."""
    
    filename = Storage.get(hash)
    if filename:
        header = dict()
        mimetype, encoding = mimetypes.guess_type(filename)
        if mimetype: header['Content-Type'] = mimetype
        if encoding: header['Content-Encoding'] = encoding
        
        if mode == 'raw':
            name = basename(filename)
            header['Content-Disposition'] = 'attachment; filename="%s"' % name
            
        stats = os.stat(filename)
        header['Content-Length'] = stats.st_size
        lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
        header['Last-Modified'] = lm
        
        body = '' if request.method == 'HEAD' else open(filename, 'rb')
        return HTTPResponse(body, header=header)
    

if __name__ == '__main__':
    
    DEBUG = True
    
    if DEBUG:
        import bottle
        bottle.debug(True)
        
    run(host='localhost', port=8000)
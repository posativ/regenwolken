#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.1.2-alpha"

import sys
import os
from os.path import isdir, exists, join, dirname
import time
from uuid import uuid4
import random
import json
import hashlib


class Config():
    """stores conf.yaml"""
    
    def __init__(self):

        for line in open('conf.yaml'):
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    key, value = line.split(':')
                    key, value = key.strip(), value.strip()
                except ValueError:
                    print >> sys.stderr, 'line is wrong `%s`' % line
                    sys.exit(1)
    
                if value.isdigit():
                    value = int(value)
                self.__dict__[key.upper()] = value
            
SETTINGS = Config()

class NoFile(Exception): pass
class DuplicateKeyError(Exception): pass


class File(file):
    """A wrapper for the file class, extended to act like GridOut"""
    
    def __init__(self, *args, **kwargs):
        file.__init__(self, *args, **kwargs)
        
    def update(self, **entries):
        self.__dict__.update(entries)


class Grid:
    '''Abstraction layer to save files in filesystem instead of GridFS.
    
    It stores every file as truncated md5 hash (8 characters long) to
    `datadir`/`md5 of $year$month$day`/ and updates the index file of this
    day (.index, js object notation).
    
    It is intended as a leightweight MongoDB alternative using a json-based
    database storage as well. MongoDB+Grid is not planned.'''
    
    def __init__(self, datadir):
        '''sets/creates data dir and builds a shortcut for the .index-files.'''
        
        if not isdir(datadir):
            try:
                os.makedirs(datadir)
            except OSError, e:
                print e
                print >> sys.stderr, 'could not create %s' % datadir
                sys.exit(1)
                
        self.index = join(datadir, '%s' ,'.index')
        self.datadir = datadir

    def put(self, obj, _id, filename, upload_date, content_type, account):
        """save file to Grid.  This is currently hard-coded and represents
        the implementation in wolken/REST.py:upload_file."""
        
        try:
            self.get(_id)
            raise DuplicateKeyError
        except NoFile:
            pass
        
        hdir = hashlib.sha1(time.strftime('%Y%m%d')).hexdigest()[:8] # hash dir
        path = join(self.datadir, hdir, _id)
        if not isdir(dirname(path)):
            os.mkdir(dirname(path))
        # save file
        obj.save(path)
        
        if not exists(self.index % hdir):
            f = open(self.index % hdir, 'w')
            f.close()
            index = {}
        else:
            f = open(self.index % hdir, 'r')
            index = json.load(f)
            f.close()
        
        index[_id] = {'filename': filename, 'upload_date': upload_date,
                      'content_type': content_type, 'account': account,
                      'name': obj.name}
        
        f = open(self.index % hdir, 'w')
        json.dump(index, f)
        f.close()
        
        return _id
        
    def get(self, _id):
        """traverse datadir and returns File (GridOut-like) if found else None"""
        
        dirs = [ts for ts in os.listdir(self.datadir)
                    if isdir(join(self.datadir, ts))]
        for ts in dirs:
            f = open(self.index % ts, 'r')
            index = json.load(f)
            f.close()
            if _id in index:
                f = File(join(self.datadir, ts, _id))
                f.update(_id=_id, **index[_id])
                return f
        else:
            raise NoFile
            

class Sessions:
    '''A simple in-memory session handler.  Uses dict[session_id] = (timestamp, value)
    scheme, automatic timout after 15 minutes.
    
    session_id -- uuid.uuid4().hex
    timestamp -- time.time()
    value -- sha1 hash
    '''
    
    def __init__(self, timeout):
        self.db = {}
        self.timeout = timeout
    
    def __repr__(self):
        L = []
        for item in sorted(self.db.keys(), key=lambda k: k[0]):
            L.append('%s\t%s, %s' % (item, self.db[item][0], self.db[item][1]))
        return '\n'.join(L)
    
    def __contains__(self, item):
        self._outdated()
        return True if self.db.has_key(item) else False
    
    def _outdated(self):
        '''automatic cleanup of outdated sessions, 60sec time-to-live'''
        #FIXME: interferes with authentication
        self.db = dict([(k, v) for k,v in self.db.items()
                            if (time.time() - v[0]) <= self.timeout])
    
    def get(self, session_id):
        '''returns session id'''
        self._outdated()
        for item in self.db:
            if item == session_id:
                return self.db[session_id][1]
        else:
            raise KeyError(session_id)
    
    def new(self, account):
        '''returns new session id'''
        
        self._outdated()
        session_id = uuid4().hex
        self.db[session_id] = (time.time(), {'key': random.getrandbits(128),
                'account': account})
        
        return session_id

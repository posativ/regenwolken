#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.1.2-alpha"

import time
from uuid import uuid4
import random

HOSTNAME = 'localhost'
BIND_ADDRESS = '0.0.0.'
PORT = 9000
MONGODB_HOST = '127.0.0.1'
MONGODB_PORT = 27017

ALLOW_REGISTRATION = True

class Sessions:
    '''A simple in-memory session handler.  Uses dict[session_id] = (timestamp, value)
    sheme, automatic timout after 15 minutes.
    
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
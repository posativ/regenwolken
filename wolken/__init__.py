#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

import time
from uuid import uuid4
import random

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
        '''automatic cleanup of outdated sessions, 60sec time-to-live'''
        #FIXME: interferes with authentication
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
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

__version__ = "0.3"

import sys
import time
from uuid import uuid4
import random
import string


class Config():
    """stores conf.yaml, regenwolken has these config values:
        - HOSTNAME
        - BIND_ADDRESS
        - PORT
        - MONGODB_HOST
        - MONGODB_PORT

        - ALLOWED_CHARS: characters allowed in username
        - MAX_CONTENT_LENGTH: maximum content length before raising 413
        - ALLOW_PRIVATE_BOOKMARKS: True | False
        - PUBLIC_REGISTRATION: instant registration, True | False
        
        - CACHE_BACKEND: SimpleCache
        - CACHE_TIMEOUT: 15*60
        
        - THUMBNAILS: True
        - SYNTAX_HIGHLIGHTING: True
        - MARKDOWN_FORMATTING: True
        """

    def __init__(self):

        self.HOSTNAME = "localhost"
        self.BIND_ADDRESS = "0.0.0.0"
        self.PORT = 80
        self.MONGODB_HOST = "127.0.0.1"
        self.MONGODB_PORT = 27017
        self.MONGODB_NAME = 'cloudapp'
        
        self.ALLOWED_CHARS = string.digits + string.ascii_letters + '.- @'
        self.MAX_CONTENT_LENGTH = 1024*1024*64
        self.ALLOW_PRIVATE_BOOKMARKS = False
        self.PUBLIC_REGISTRATION = False
        self.SHORT_ID_MIN_LENGTH = 3
        
        self.CACHE_BACKEND = 'SimpleCache'
        self.CACHE_TIMEOUT = 15*60
        
        self.THUMBNAILS = True
        self.SYNTAX_HIGHLIGHTING = True
        self.MARKDOWN_FORMATTING = True
        
        for line in open('conf.yaml'):
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    key, value = line.split(':', 1)
                    key, value = key.strip(), value.strip()
                except ValueError:
                    print >> sys.stderr, 'line is wrong `%s`' % line
                    sys.exit(1)

                if value.isdigit():
                    value = int(value)
                elif value.lower() in ['true', 'false']:
                    value = True if value.capitalize() == 'True' else False
                self.__dict__[key.upper()] = value

conf = Config()


class Struct:
    """dict -> class, http://stackoverflow.com/questions/1305532/convert-python-dict-to-object"""
    def __init__(self, **entries):
        self.__dict__.update(entries)


class NoFile(Exception): pass
class DuplicateKeyError(Exception): pass


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

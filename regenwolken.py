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

__version__ = "0.1.2-alpha"

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule, Submount
from werkzeug.wsgi import responder
from werkzeug.datastructures import WWWAuthenticate

# may changed via conf.yaml
HOSTNAME = "localhost"
BIND_ADDRESS = "0.0.0.0"
PORT = 80
MONGODB_HOST = "127.0.0.1"
MONGODB_PORT = 27017

# inits global variables HOSTNAME, PORT and so on #FIXME!!
from wolken import REST, web

class LimitedRequest(Request):
    # FIXME: Cloud.app can not handle 413 Request Entity Too Large
    max_content_length = 1024 * 1024 * 64 # max. 64 mb request size

HTML_map = Map([
    Rule('/', endpoint=web.index),
#    Rule('/account', endpoint='web.account'),
 #   Submount('/items', [
 #       Rule('/', endpoint='web.items.index'),
 #   ]),
])

REST_map = Map([
    Rule('/', endpoint=REST.upload_file, methods=['POST', ]),
    Rule('/account', endpoint=REST.account),
    Rule('/items', endpoint=REST.items),
    Rule('/items', endpoint=REST.bookmarks, methods=['POST', ]),
    Rule('/items/new', endpoint=REST.items_new),
    Rule('/items/<id>', endpoint=REST.show),
    Rule('/register', endpoint=REST.register, methods=['POST', ]),
])


@responder
def application(environ, start_response):
    
    request = LimitedRequest(environ)
    
    if request.headers.get('Accept', 'application/json') == 'application/json':
        urls = REST_map.bind_to_environ(environ)
    else:
        urls = REST_map.bind_to_environ(environ)
        # urls = HTML_map.bind_to_environ(environ)

    return urls.dispatch(lambda f, v: f(environ, request, **v),
                         catch_http_exceptions=True)

if __name__ == '__main__':
    from werkzeug.serving import run_simple    
    run_simple(BIND_ADDRESS, PORT, application, use_reloader=True)

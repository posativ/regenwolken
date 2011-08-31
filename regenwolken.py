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

from wolken import REST
from wolken import HOSTNAME, BIND_ADDRESS, PORT, MONGODB_HOST, MONGODB_PORT

class LimitedRequest(Request):
    # FIXME: Cloud.app can not handle 413 Request Entity Too Large
    max_content_length = 1024 * 1024 * 64 # max. 64 mb request size

HTML_map = Map([
    Rule('/', endpoint='web.index'),
    Rule('/account', endpoint='web.account'),
    Submount('/items', [
        Rule('/', endpoint='web.items.index'),
    ]),
])

REST_map = Map([
    Rule('/', endpoint=REST.index, methods=['GET', 'HEAD']),
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
    
    environ['host'] = 'localhost'
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
    from optparse import OptionParser, make_option
    
    options = [
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
    
    HOSTNAME = args[0] if len(args) == 1 else 'localhost'
    BIND_ADDRESS = options.bind
    PORT = options.port
    
    MONGODB_HOST = options.mongodb_host
    MONGODB_PORT = options.mongodb_port
    
    run_simple(BIND_ADDRESS, PORT, application, use_reloader=True)
    
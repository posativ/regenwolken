#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.
#
#
# Wolken is a Cloud.app clone, with leave the cloud in mind.

__version__ = "0.1.2-alpha"

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule
from werkzeug.wsgi import responder
from werkzeug.http import parse_dict_header
from werkzeug.datastructures import Authorization
from werkzeug.utils import cached_property

from wolken import SETTINGS, REST, web


def parse_authorization_header(value):
    """make nc and cnonce optional, see https://github.com/mitsuhiko/werkzeug/pull/100"""
    if not value:
        return
    try:
        auth_type, auth_info = value.split(None, 1)
        auth_type = auth_type.lower()
    except ValueError:
        return
    if auth_type == 'basic':
        try:
            username, password = auth_info.decode('base64').split(':', 1)
        except Exception:
            return
        return Authorization('basic', {'username': username,
                                       'password': password})
    elif auth_type == 'digest':
        auth_map = parse_dict_header(auth_info)
        for key in 'username', 'realm', 'nonce', 'uri', 'response':
            if not key in auth_map:
                return
        if 'qop' in auth_map:
            if not auth_map.get('nc') or not auth_map.get('cnonce'):
                return
        return Authorization('digest', auth_map)

class Wolkenrequest(Request):
    """fixing HTTP Digest Auth fallback"""
    # FIXME: Cloud.app can not handle 413 Request Entity Too Large
    max_content_length = 1024 * 1024 * 64 # max. 64 mb request size
    
    @cached_property
    def authorization(self):
        """The `Authorization` object in parsed form."""
        header = self.environ.get('HTTP_AUTHORIZATION')
        return parse_authorization_header(header)

HTML_map = Map([
    Rule('/', endpoint=web.index),
    Rule('/<short>', endpoint=web.show),
#    Rule('/account', endpoint='web.account'),
 #   Submount('/items', [
 #       Rule('/', endpoint='web.items.index'),
 #   ]),
])

REST_map = Map([
    Rule('/', endpoint=REST.upload_file, methods=['POST', ]),
    Rule('/items', endpoint=REST.bookmarks, methods=['POST', ]),
    Rule('/register', endpoint=REST.register, methods=['POST', ]),
    Rule('/<short>', endpoint=REST.view_item, methods=['GET', ]),
    Rule('/account', endpoint=REST.account),
    Rule('/account/stats', endpoint=REST.account_stats),
    Rule('/items', endpoint=REST.items),
    Rule('/items/new', endpoint=REST.items_new),
#    Rule('/items/<short>', endpoint=REST.view_item)
])


@responder
def application(environ, start_response):
    
    request = Wolkenrequest(environ)
    
    if request.headers.get('Accept', 'application/json') == 'application/json':
        urls = REST_map.bind_to_environ(environ)
    else:
        #urls = REST_map.bind_to_environ(environ)
        urls = HTML_map.bind_to_environ(environ)

    return urls.dispatch(lambda f, v: f(environ, request, **v),
                         catch_http_exceptions=True)

if __name__ == '__main__':
    from werkzeug.serving import run_simple    
    run_simple(SETTINGS.BIND_ADDRESS, SETTINGS.PORT,
               application, use_reloader=True)

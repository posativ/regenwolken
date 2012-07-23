#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of posativ <info@posativ.org>.
#
# regenwolken is a CloudApp clone, with leave the cloud in mind.

__version__ = '0.4'

import sys; reload(sys)
from os.path import join, dirname
sys.setdefaultencoding('utf-8')

from werkzeug.wrappers import Request
from werkzeug.routing import Map, Rule
from werkzeug.wsgi import responder
from werkzeug.http import parse_dict_header
from werkzeug.datastructures import Authorization
from werkzeug.utils import cached_property
from werkzeug import SharedDataMiddleware

from wolken import conf, REST, web


class Wolkenrequest(Request):
    """fixing HTTP Digest Auth fallback"""
    # FIXME: Cloud.app can not handle 413 Request Entity Too Large
    max_content_length = conf.MAX_CONTENT_LENGTH


HTML_map = Map([
    Rule('/', endpoint=web.index),
#    Rule('/login', endpoint=web.login_page, methods=['GET', 'HEAD']),
#    Rule('/login', endpoint=web.login, methods=['POST']),
    Rule('/<short_id>', endpoint=web.drop),
    Rule('/<short_id>/<filename>', endpoint=web.show),
    Rule('/items/<short_id>/<filename>', endpoint=web.show),
    Rule('/thumb/<short_id>', endpoint=web.thumb),
])

REST_map = Map([
    Rule('/', endpoint=REST.upload_file, methods=['POST', ]),
    Rule('/items', endpoint=REST.bookmark, methods=['POST', ]),
    Rule('/register', endpoint=REST.register, methods=['POST', ]),
    Rule('/<short_id>', endpoint=REST.view_item, methods=['GET', ]),
    Rule('/account', endpoint=REST.account),
    Rule('/account/stats', endpoint=REST.account_stats),
    Rule('/domains/<domain>', endpoint=REST.view_domain),
    Rule('/items', endpoint=REST.items),
    Rule('/items/new', endpoint=REST.items_new),
    Rule('/items/<objectid>', endpoint=REST.modify_item, methods=['HEAD', 'PUT', 'DELETE']),
    Rule('/items/trash', endpoint=REST.trash_items, methods=['POST', ]),
])


@responder
def application(environ, start_response):

    environ['SERVER_SOFTWARE'] = "regenwolken/%s" % __version__ # FIXME doesn't work
    request = Wolkenrequest(environ)

    if request.accept_mimetypes.accept_html:
        urls = HTML_map.bind_to_environ(environ)
    else:
        urls = REST_map.bind_to_environ(environ)

    return urls.dispatch(lambda f, v: f(environ, request, **v),
                         catch_http_exceptions=True)

app = SharedDataMiddleware(application, {
         '/static/': join(dirname(__file__), 'wolken/static'),
         '/images/': join(dirname(__file__), 'wolken/static/images')
})

if __name__ == '__main__':
    from werkzeug.serving import run_simple

    run_simple(conf.BIND_ADDRESS, conf.PORT,
               app, use_reloader=True)

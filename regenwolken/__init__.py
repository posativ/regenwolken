#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
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
# regenwolken is a CloudApp clone that works on your very own server.

__version__ = '0.5'

import sys

import flask
import pymongo

from regenwolken import views, mongonic


class Regenwolken(flask.Flask):

    def __init__(self):

        flask.Flask.__init__(self, __name__)
        self.config.from_object('regenwolken.utils.conf')
        self.config.from_envvar('REGENWOLKEN_SETTINGS', silent=True)

        self.setup_routes()
        self.setup_mongodb()
        self.setup_extensions()

    def setup_routes(self):

        for endpoint, rule, methods in [
            ('index', '/', ['GET', 'POST']),
            ('items_view', '/<short_id>', ['GET']),

            ('account', '/account', ['PUT', 'GET']),
            ('account_stats', '/account/stats', ['GET', ]),

            ('register', '/register', ['POST', ]),
            ('domains', '/domains/<domain>', ['GET', ]),

            ('items', '/items', ['GET', ]),
            ('bookmark', '/items', ['POST', ]),
            ('items_new', '/items/new', ['HEAD', 'GET']),
            ('items_edit', '/items/<object_id>', ['HEAD', 'PUT', 'DELETE']),

            ('trash', '/items/trash', ['POST', ]),

            ('blob', '/items/<short_id>/<filename>', ['GET']),
            ('blob', '/<short_id>/<filename>', ['GET']),

            ('thumb', '/thumb/<short_id>', ['GET', ])

        ]:
            self.add_url_rule(rule, endpoint, view_func=getattr(views, endpoint), methods=methods)

    def setup_mongodb(self):

        con = pymongo.Connection(
            self.config['MONGODB_HOST'],
            self.config['MONGODB_PORT']
        )[self.config['MONGODB_NAME']]

        con.items.create_index('short_id')
        con.accounts.create_index('email')

        self.db = con
        self.fs = mongonic.GridFS(con)
        self.sessions = mongonic.Sessions(con, size=self.config['MONGODB_SESSION_SIZE'])

    def setup_extensions(self):

        try:
            import pygments
        except ImportError:
            if self.config['SYNTAX_HIGHLIGHTING']:
                print >> sys.stderr, "'pygments' not found, syntax highlighting disabled"
                self.config['SYNTAX_HIGHLIGHTING'] = False
        try:
            import markdown
        except ImportError:
            if self.config['MARKDOWN_FORMATTING']:
                print >> sys.stderr, "'markdown' not found, markdown formatting disabled"
                self.config['MARKDOWN_FORMATTING'] = False

        try:
            import ImageFile
        except ImportError:
            if self.config['THUMBNAILS']:
                print >> sys.stderr, "'PIL' not found, thumbnailing disabled"
                self.config['THUMBNAILS'] = False


def main():

    app = Regenwolken()

    if '--debug' in sys.argv:
        app.debug = True

    app.run(host=app.config.get('HOST', '0.0.0.0'), port=app.config.get('PORT', 1234))

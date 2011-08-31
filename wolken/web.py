#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from werkzeug import Response

def index(environ, response):
    """my.cl.ly/"""
    
    body = '<h1>Hallo Welt</h1>'
    
    return Response(body, 200, content_type='text/html')
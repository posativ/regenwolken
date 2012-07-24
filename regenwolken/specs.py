# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from __future__ import unicode_literals

import mimetypes

from time import strftime, gmtime
from os.path import splitext

from werkzeug.urls import url_quote
from werkzeug.utils import secure_filename
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache(30*60)  # XXX use redis!

from regenwolken.utils import A1, Struct

try:
    import pygments
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename, ClassNotFound
    from pygments.formatters import HtmlFormatter
except ImportError:
    pygments = None

try:
    import markdown
except ImportError:
    markdown = None


def Item(obj, conf, **kw):
    """JSON-compatible dict representing Item.

        href:           used for renaming -> http://developer.getcloudapp.com/rename-item
        name:           item's name, taken from filename
        private:        requires auth when viewing
        subscribed:     true or false, when paid for "Pro"
        url:            url to this file
        content_url:    <unknown>
        item_type:      image, bookmark, ... there are more
        view_counter:   obviously
        icon:           some picture to display `item_type`
        remote_url:     <unknown>, href + quoted name
        thumbnail_url:  <url to thumbnail, when used?>
        redirect_url:   redirection url in bookmark items
        source:         client name
        created_at:     timestamp created - '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:     timestamp updated - '%Y-%m-%dT%H:%M:%SZ' UTC
        deleted_at:     timestamp deleted - '%Y-%m-%dT%H:%M:%SZ' UTC
    """

    x = {}
    if isinstance(obj, dict):
        obj = Struct(**obj)

    result = {
        "href": "http://%s/items/%s" % (conf['HOSTNAME'], obj._id),
        "private": obj.private,
        "subscribed": True,
        "item_type": obj.item_type,
        "view_counter": obj.view_counter,
        "icon": "http://%s/images/item_types/%s.png" % (conf['HOSTNAME'], obj.item_type),
        "source": obj.source,
        "created_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "updated_at": strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        "deleted_at": None }

    if obj.item_type == 'bookmark':
        x['name'] = obj.name
        x['url'] = 'http://' + conf['HOSTNAME'] + '/' + obj.short_id
        x['content_url'] = x['url'] + '/content'
        x['remote_url'] = None
        x['redirect_url'] = obj.redirect_url
    else:
        x['name'] = obj.filename
        x['url'] = 'http://' + conf['HOSTNAME'] + '/' + obj.short_id
        x['content_url'] = x['url'] + '/' + secure_filename(obj.filename)
        x['remote_url'] = x['url'] + '/' + url_quote(obj.filename)
        x['thumbnail_url'] = x['url'] # TODO: thumbails
        x['redirect_url'] = None

    try:
        x['created_at'] = obj.created_at
        x['updated_at'] = obj.updated_at
        x['deleted_at'] = obj.deleted_at
        if obj.deleted_at:
            x['icon'] = "http://%s/images/item_types/trash.png" % conf['HOSTNAME']
    except AttributeError:
        pass

    result.update(x)
    result.update(kw)
    return result


def Account(account, conf, **kw):
    """JSON-compatible dict representing cloudapp's account

        domain:           custom domain, only in Pro available
        domain_home_page: http://developer.getcloudapp.com/view-domain-details
        private_items:    http://developer.getcloudapp.com/change-default-security
        subscribed:       Pro feature, custom domain... we don't need this.
        alpha:            <unkown> wtf?
        created_at:       timestamp created - '%Y-%m-%dT%H:%M:%SZ' UTC
        updated_at:       timestamp updated - '%Y-%m-%dT%H:%M:%SZ' UTC
        activated_at:     timestamp account activated, per default None
        items:            (not official) list of items by this account
        email:            username of this account, characters can be any
                          of "a-zA-Z0-9.- @" and no digit-only name is allowed
        password:         password, md5(username + ':' + realm + ':' + passwd)
    """

    result = {
        'id': account['id'],
        'domain': conf['HOSTNAME'],
        'domain_home_page': None,
        'private_items': False,
        'subscribed': True,
        'subscription_expires_at': '2112-12-21',
        'alpha': False,
        'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        'activated_at': None,
        "items": [],
        'email': account['email'],
        'passwd': A1(account['email'], account['passwd'])
    }

    result.update(kw)
    return result


class Drop:
    """Drop class which renders item-specific layouts."""

    def __init__(self, drop, conf):

        def guess_type(url):
            try:
                m = mimetypes.guess_type(url)[0].split('/')[0]
                if m in ['image', 'text']:
                    return m
            except AttributeError:
                if self.ismarkdown or self.iscode or self.text:
                    return 'text'
            return 'other'

        self.__dict__.update(Item(drop, conf))
        self.read, self.length = drop.read, drop.length
        self.filename, self.short_id = drop.filename, drop.short_id
        self.item_type = guess_type(self.name)
        self.url = self.__dict__['content_url']

    @property
    def ismarkdown(self):
        return True if splitext(self.filename)[1][1:] in ['md', 'mkdown', 'markdown'] else False

    @property
    def iscode(self):

        if pygments is None:
            return False

        try:
            get_lexer_for_filename(self.filename)
            return True
        except ClassNotFound:
            return False

    @property
    def istext(self):
        if splitext(self.filename)[1][1:] in ['conf', 'txt'] or self.ismarkdown or self.iscode:
            return True
        return False

    @property
    def markdown(self):
        rv = cache.get('text-'+self.short_id)
        if rv is None:
            rv = markdown.markdown(self.read().decode('utf-8'))
            cache.set('text-'+self.short_id, rv)
        return rv

    @property
    def code(self):
        rv = cache.get('text-'+self.short_id)
        if rv is None:
            rv = highlight(
                self.read(),
                get_lexer_for_filename(self.url),
                HtmlFormatter(lineos=False, cssclass='highlight')
            )

            cache.set('text-'+self.short_id, rv)
        return rv

# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from time import gmtime, strftime
from random import getrandbits
from os.path import basename

from base64 import standard_b64decode

from urllib import unquote
from urlparse import urlparse

from werkzeug import Response
from pymongo import DESCENDING
from flask import request, abort, jsonify, json, current_app, render_template, redirect

from regenwolken.utils import login, private, A1, slug, thumbnail, clear, urlscheme
from regenwolken.specs import Item, Account, Drop


def index():
    """Upload a file, when the client has a valid session key.

    -- http://developer.getcloudapp.com/upload-file"""

    if request.method == 'POST' and not request.accept_mimetypes.accept_html:

        try:
            account = current_app.sessions.pop(request.form.get('key'))['account']
        except KeyError:
            abort(401)

        db, fs = current_app.db, current_app.fs
        config, sessions = current_app.config, current_app.sessions

        acc = db.accounts.find_one({'email': account})
        source = request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0]
        privacy = request.form.get('acl', acc['private_items'])

        _id = fs.upload_file(config, account, request.files.get('file'), source, privacy)

        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

        obj = fs.get(_id)

        if obj is None:
            abort(400)
        else:
            return jsonify(Item(obj, config, urlscheme(request)))
    else:
        return Response(status=501, content_type='text/html', response=(
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">'
            '<title>501 Not Implemented</title>'
            '<h1>Nope. Web Interface still not implemented.</h1>'
            '<p>The server does not support the action requested by the browser.</p>'))


@login
def account():
    """Return account details and/or update given keys.

    -- http://developer.getcloudapp.com/view-account-details
    -- http://developer.getcloudapp.com/change-default-security
    -- http://developer.getcloudapp.com/change-email
    -- http://developer.getcloudapp.com/change-password

    PUT: accepts every new password (stored in plaintext) and similar to /register
    no digit-only "email" address is allowed."""

    conf, db = current_app.config, current_app.db
    account = db.accounts.find_one({'email': request.authorization.username})

    if request.method == 'GET':
        return jsonify(clear(account))

    try:
        _id = account['_id']
        data = json.loads(request.data)['user']
    except ValueError:
        return ('Unprocessable Entity', 422)

    if len(data.keys()) == 1 and 'private_items' in data:
        db.accounts.update({'_id': _id}, {'$set': {'private_items': data['private_items']}})
        account['private_items'] = data['private_items']
    elif len(data.keys()) == 2 and 'current_password' in data:
        if not account['passwd'] == A1(account['email'], data['current_password']):
            return abort(403)

        if 'email' in data:
            if filter(lambda c: not c in conf['ALLOWED_CHARS'], data['email']) \
            or data['email'].isdigit(): # no numbers allowed
                abort(400)
            if db.accounts.find_one({'email': data['email']}) and \
            account['email'] != data['email']:
                return ('User already exists', 406)

            new = {'email': data['email'],
                   'passwd': A1(data['email'], data['current_password'])}
            db.accounts.update({'_id': _id}, {'$set': new})
            account['email'] = new['email']
            account['passwd'] = new['passwd']

        elif 'password' in data:
            passwd = A1(account['email'], data['password'])
            db.accounts.update({'_id': _id}, {'$set': {'passwd': passwd}})
            account['passwd'] = passwd

        else:
            abort(400)

    db.accounts.update({'_id': account['_id']}, {'$set':
            {'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())}})

    return jsonify(clear(account))


@login
def account_stats():
    """Show current item count and other statistics.

    -- http://developer.getcloudapp.com/view-account-stats"""

    email = request.authorization.username
    items = current_app.db.accounts.find_one({'email': email})['items']
    views = 0
    for item in items:
        views += current_app.db.items.find_one({'_id': item})['view_counter']

    return jsonify({'items': len(items), 'views': views})


@login
def items():
    """Show items from user.  Optional query parameters:

            - page (int)     - default: 1
            - per_page (int) - default: 5
            - type (str)     - default: None, filter by image, bookmark, text,
                                             archive, audio, video, or unknown
            - deleted (bool) - default: False, show trashed items

    -- http://developer.getcloudapp.com/list-items"""

    db, fs = current_app.db, current_app.fs

    ParseResult = urlparse(request.url)
    params = {'per_page': '5', 'page': '1', 'type': None, 'deleted': False,
              'source': None}

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        params.update(query)

    listing = []
    try:
        pp = int(params['per_page'])
        page = int(params['page'])
        email = request.authorization.username
    except (ValueError, KeyError):
        abort(400)

    query = {'account': email}
    if params['type'] != None:
        query['item_type'] = params['type']
    if params['deleted'] == False:
        query['deleted_at'] = None
    if params['source'] != None:
        query['source'] = {'$regex': '^' + unquote(params['source'])}

    items = db.items.find(query)
    for item in items.sort('updated_at', DESCENDING)[pp*(page-1):pp*page]:
        listing.append(Item(fs.get(_id=item['_id']),
                            current_app.config, urlscheme(request)))
    return json.dumps(listing[::-1])


@login
def items_new():
    """Generates a new key for the upload process.  Timeout after 60 minutes!

    -- http://developer.getcloudapp.com/upload-file
    -- http://developer.getcloudapp.com/upload-file-with-specific-privacy"""

    acc = current_app.db.accounts.find_one({'email': request.authorization.username})
    ParseResult = urlparse(request.url)
    privacy = 'private' if acc['private_items'] else 'public-read'

    if not ParseResult.query == '':
        query = dict([part.split('=', 1) for part in ParseResult.query.split('&')])
        privacy = 'private' if query.get('item[private]', None) else 'public-read'


    key = current_app.sessions.new(request.authorization.username)
    res = { "url": urlscheme(request) + '://' + current_app.config['HOSTNAME'],
          "max_upload_size": current_app.config['MAX_CONTENT_LENGTH'],
          "params": { "acl": privacy,
                      "key": key
                    },
        }

    return jsonify(res)


@private(lambda req: req.accept_mimetypes.accept_html)
def items_view(short_id):
    """View item details or show them in the web interface based on Accept-Header or
    returns 404 if the requested short_id does not exist.

    -- http://developer.getcloudapp.com/view-item"""

    db, fs = current_app.db, current_app.fs
    obj = fs.get(short_id=short_id)

    if obj is None:
        abort(404)

    if request.accept_mimetypes.accept_html:

        if obj.deleted_at:
            abort(404)

        if obj.item_type != 'image':
            # the browser always loads the blob, so we don't want count it twice
            fs.inc_count(obj._id)

        if obj.item_type == 'bookmark':
            return redirect(obj.redirect_url)

        drop = Drop(obj, current_app.config, urlscheme(request))
        if drop.item_type == 'image':
            return render_template('image.html', drop=drop)
        elif drop.item_type == 'text':
            return render_template('text.html', drop=drop)
        else:
            return render_template('other.html', drop=drop)
    return jsonify(Item(obj, current_app.config, urlscheme(request)))


@login
def items_edit(object_id):
    """rename/delete/change privacy of an item.

    -- http://developer.getcloudapp.com/rename-item
    -- http://developer.getcloudapp.com/delete-item
    -- http://developer.getcloudapp.com/change-security-of-item"""

    conf, db, fs = current_app.config, current_app.db, current_app.fs
    item = db.items.find_one({'account': request.authorization.username,
                              '_id': object_id})
    if not item:
        abort(404)

    if request.method == 'DELETE':
        item['deleted_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())
    elif request.method == 'PUT':
        try:
            data = json.loads(request.data)['item']
            key, value = data.items()[0]
            if not key in ['private', 'name', 'deleted_at']: raise ValueError
        except ValueError:
            return ('Unprocessable Entity', 422)

        if key == 'name' and item['item_type'] != 'bookmark':
            item['filename'] = value
        elif key == 'private' and item['item_type'] == 'bookmark' and value \
        and not conf['ALLOW_PRIVATE_BOOKMARKS']:
            pass
        else:
            item[key] = value

        item['updated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    db.items.save(item)
    item = fs.get(item['_id'])
    return jsonify(Item(item, conf, urlscheme(request)))


@private(lambda req: True)
def blob(short_id, filename):
    """returns bookmark or file either as direct download with human-readable,
    original filename or inline display using whitelisting"""

    fs = current_app.fs

    obj = fs.get(short_id=short_id)
    if obj is None or obj.deleted_at:
        abort(404)

    # views++
    fs.inc_count(obj._id)

    if obj.item_type == 'bookmark':
        return redirect(obj.redirect_url)
    elif not obj.content_type.split('/', 1)[0] in ['image', 'text']:
        return Response(obj, content_type=obj.content_type, headers={'Content-Disposition':
                    'attachment; filename="%s"' % basename(obj.filename)})
    return Response(obj, content_type=obj.content_type)


@login
def trash():
    """No official API call yet.  Trash items marked as deleted. Usage:
    curl -u user:pw --digest -H "Accept: application/json" -X POST http://my.cl.ly/items/trash"""

    empty = current_app.db.items.find(
        {'account': request.authorization.username, 'deleted_at': {'$ne': None}})

    for item in empty:
        current_app.fs.delete(item)

    return '', 200


def register():
    """Registration of new users (no digits-only usernames are allowed), if
    PUBLIC_REGISTRATION is set to True new accounts are instantly activated. Otherwise
    you have to do it manually via `manage.py activate $USER`.

    -- http://developer.getcloudapp.com/register"""

    conf, db = current_app.config, current_app.db

    if len(request.data) > 200:
        return ('Request Entity Too Large', 413)
    try:
        d = json.loads(request.data)
        email = d['user']['email']
        if email.isdigit(): raise ValueError # no numbers as username allowed
        passwd = d['user']['password']
    except (ValueError, KeyError):
        return ('Bad Request', 422)

    # TODO: allow more characters, unicode -> ascii, before filter
    if filter(lambda c: not c in conf['ALLOWED_CHARS'], email):
        return ('Bad Request', 422)

    if db.accounts.find_one({'email': email}) != None:
        return ('User already exists', 406)

    if not db.accounts.find_one({"_id":"autoinc"}):
        db.accounts.insert({"_id":"_inc", "seq": 1})

    account = Account({'email': email, 'passwd': passwd,
                       'id': db.accounts.find_one({'_id': '_inc'})['seq']}, conf)
    db.accounts.update({'_id': '_inc'}, {'$inc': {'seq': 1}})
    if conf['PUBLIC_REGISTRATION']:
        account['activated_at'] = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

    account['_id'] = account['id']
    db.accounts.insert(account)

    return (jsonify(clear(account)), 201)


@login
def bookmark():
    """Yet another URL shortener. This implementation prefixes bookmarks with
    a dash (-) so

    -- http://developer.getcloudapp.com/bookmark-link"""

    conf, db = current_app.config, current_app.db

    # XXX move logic into mongonic.py
    def insert(name, redirect_url):

        acc = db.accounts.find_one({'email': request.authorization.username})

        _id = str(getrandbits(32))
        retry_count = 1
        short_id_length = conf['SHORT_ID_MIN_LENGTH']

        while True:
            short_id = slug(short_id_length)
            if not db.items.find_one({'short_id': short_id}):
                break
            else:
                retry_count += 1
                if retry_count > 3:
                    short_id_length += 1
                    retry_count = 1

        x = {
            'account': request.authorization.username,
            'name': name,
            '_id': _id,
            'short_id': slug(short_id_length),
            'redirect_url': redirect_url,
            'item_type': 'bookmark',
            'view_counter': 0,
            'private': request.form.get('acl', acc['private_items'])
                if conf['ALLOW_PRIVATE_BOOKMARKS'] else False,
            'source': request.headers.get('User-Agent', 'Regenschirm++/1.0').split(' ', 1)[0],
            'created_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
            'updated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()),
        }

        item = Item(x, conf, urlscheme(request))
        db.items.insert(x)

        items = acc['items']
        items.append(_id)
        db.accounts.update({'_id': acc['_id']}, {'$set': {'items': items}}, upsert=False)

        return item

    try:
        data = json.loads(request.data)
        data = data['item']
    except (ValueError, KeyError):
        return ('Unprocessable Entity', 422)

    if isinstance(data, list):
        return json.dumps([insert(d['name'], d['redirect_url']) for d in data])
    else:
        return jsonify(insert(data['name'], data['redirect_url']))


@private(lambda req: True)
def thumb(short_id):
    """returns 128px thumbnail, when possible and cached for 30 minutes,
    otherwise item_type icons."""

    # th = cache.get('thumb-'+short_id)
    # if th: return Response(standard_b64decode(th), 200, content_type='image/png')

    rv = current_app.fs.get(short_id=short_id)
    if rv is None or rv.deleted_at:
        abort(404)

    if rv.item_type == 'image' and current_app.config['THUMBNAILS']:
        try:
            th = thumbnail(rv)
            # cache.set('thumb-'+short_id, th)
            return Response(standard_b64decode(th), 200, content_type='image/png')
        except IOError:
            pass
    return Response(open('wolken/static/images/item_types/%s.png' % rv.item_type),
                    200, content_type='image/png')


def domains(domain):
    """Returns HOSTNAME. Always."""
    return jsonify({"home_page": "http://%s" % current_app.config['HOSTNAME']})

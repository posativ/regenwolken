#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

from time import gmtime, strftime
from random import getrandbits

from gridfs import GridFS as Grid
from pymongo.errors import DuplicateKeyError

from regenwolken.utils import Struct, gen


class GridFS:
    """An extended GridFS (+MongoDB) backend to update metadata in a separate
    MongoDB but handle them in one GridOut object.

    As it is not documented: every attribute in GridOut is read-only. You
    can only write these `metadata` once. This extended GridFS will keep
    GridIn's _id, content_type, filename and upload_date and so on intact
    and read-only!"""

    def __init__(self, database, collection='fs'):
        """shortcuts to gridFS(db) and db.items"""

        self.mdb = database.items
        self.gfs = Grid(database, collection)

    def put(self, data, _id, content_type, filename, **kw):
        """upload file-only. Can not handle bookmarks."""

        if _id in ['thumb', 'items', 'login']:
            raise DuplicateKeyError

        item_type, subtype = content_type.split('/', 1)
        if item_type in ['image', 'text', 'audio', 'video']:
            pass
        elif item_type == 'application' and \
        filter(lambda k: subtype.find(k) > -1, ['compress', 'zip', 'tar']):
                item_type = 'archive'
        else:
            item_type = 'unknown'

        if self.mdb.find_one({'short_id': kw['short_id']}):
            raise DuplicateKeyError('short_id already exists')

        _id = self.gfs.put(data, _id=_id, content_type=content_type,
                               filename=filename)

        kw.update({'_id': _id, 'item_type': item_type})
        self.mdb.insert(kw)

        return _id

    def get(self, _id=None, short_id=None):
        """if url is given, we need a reverse lookup in metadata.  Returns
        a GridOut/bookmark with additional metadata added."""

        if _id:
            cur = self.mdb.find_one({'_id': _id})
        else:
            cur = self.mdb.find_one({'short_id': short_id})
            if not cur:
                return None
            _id = cur['_id']

        if cur.get('item_type', '') == 'bookmark':
            return Struct(**cur)
        else:
            obj = self.gfs.get(_id)
            obj.__dict__.update(cur)
            return obj

    def update(self, _id, **kw):
        '''update **kw'''
        self.mdb.update({'_id': _id}, {'$set': kw}, upsert=False)

    def inc_count(self, _id):
        '''find and increase view_counter'''
        self.mdb.update({'_id': _id}, {'$inc': {'view_counter': 1}})

    def delete(self, item):
        '''remove item from gridfs and db.items'''

        if item['item_type'] != 'bookmark':
            self.gfs.delete(item['_id'])
        self.mdb.remove(item['_id'])

    def upload_file(self, conf, account, obj, useragent, privacy):

        if obj is None:
            return None

        # XXX what's this?
        if isinstance(privacy, (str, unicode)):
            privacy = True if privacy == 'private' else False

        timestamp = strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())

        if obj.filename.find(u'\x00') == len(obj.filename)-1:
            filename = obj.filename[:-1]
        else:
            filename = obj.filename

        _id = str(getrandbits(32))
        retry_count = 3
        short_id_length = conf['SHORT_ID_MIN_LENGTH']
        while True:
            try:
                self.put(obj, _id=_id ,filename=filename, created_at=timestamp,
                       content_type=obj.mimetype, account=account, view_counter=0,
                       short_id=gen(short_id_length), updated_at=timestamp,
                       source=useragent, private=privacy)
                break
            except DuplicateKeyError:
                retry_count += 1
                if retry_count > 3:
                    short_id_length += 1
                    retry_count = 1

        return _id

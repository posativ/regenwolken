#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright 2011 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

import gridfs

class GridFS:
    '''an extended GridFS (+MongoDB) backend to update metadata in a separate
    MongoDB but handle them in one GridOut object.
    
    As it is not documented: every attribute in GridOut is read-only. You
    can only write these `metadata` once. This extended GridFS will keep
    GridIn's _id, content_type, filename and upload_date and so on intact
    and read-only!'''
    
    def __init__(self, database, collection='fs'):
        
        self.mdb = database['%s_metadata' % collection]
        self.gfs = gridfs.GridFS(database, collection)
        
    def put(self, data, _id, content_type, filename, upload_date, **kw):
        
        _id = self.gfs.put(data, _id=_id, content_type=content_type,
                           filename=filename, upload_date=upload_date)
        if kw:
            kw.update({'_id': _id})
            self.mdb.insert(kw)
            
        return _id
            
    def get(self, _id=None, url=None):
        '''if url is given, we need a reverse lookup in metadata.  Returns
        a GridOut with additional metadata added.'''
        
        if _id:
            obj = self.gfs.get(_id)
        else:
            _id = self.mdb.find_one({'url': url})['_id']
            obj = self.gfs.get(_id)
        
        cur = self.mdb.find_one({'_id': _id})
        if cur:
            obj.__dict__.update(cur)
            
        return obj
            
    def update(self, _id, **kw):
        '''update **kw'''
        self.mdb.update({'_id': _id}, {'$set': kw}, upsert=False)
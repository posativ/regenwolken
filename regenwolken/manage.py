# -*- encoding: utf-8 -*-
#
# Copyright 2012 posativ <info@posativ.org>. All rights reserved.
# License: BSD Style, 2 clauses.

import sys; reload(sys)
sys.setdefaultencoding('utf-8')

import logging
import string
import re

from datetime import timedelta, datetime
from time import strftime, gmtime

from flask import Flask

from pymongo import Connection
from gridfs import GridFS
from gridfs.errors import NoFile


def ppsize(num):
    '''pretty-print filesize.
    http://blogmag.net/blog/read/38/Print_human_readable_file_size'''
    for x in ['bytes','KiB','MiB','GiB','TB']:
        if num < 1024.0:
            return "%3.2f %s" % (num, x)
        num /= 1024.0


def tdelta(input):
    """converts human-readable time deltas to datetime.timedelta.
    >>> tdelta(3w 12m) == datetime.timedelta(weeks=3, minutes=12)"""

    keys = ['weeks', 'days', 'hours', 'minutes']
    regex = ''.join(['((?P<%s>\d+)%s ?)?' % (k, k[0]) for k in keys])
    kwargs = {}
    for k,v in re.match(regex, input).groupdict(default='0').items():
        kwargs[k] = int(v)
    return timedelta(**kwargs)


def account(conf, options, args):
    '''View details or summary of all accounts.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    if options.all:
        query = None
    elif len(args) == 2:
        query = {'_id': int(args[1])} if args[1].isdigit() else {'email': args[1]}
    else:
        log.error('account <email or _id> requires a valid email or _id')
        sys.exit(1)

    for acc in db.accounts.find(query):
        if str(acc['_id']).startswith('_'):
            continue
        print '%s [id:%s]' % (acc['email'], acc['id'])
        for key in acc:
            if key in ['email', '_id', 'id']:
                continue
            if key == 'items':
                try:
                    size = sum([fs.get(_id).length for _id in acc['items']])
                except NoFile:
                    log.warn('Account `%s` has some files missing:', _id)
                    # fail safe counting
                    size = 0
                    missing = []
                    for i in acc['items']:
                        if not fs.exists(i):
                            missing.append(i)
                        else:
                            size += fs.get(i).length
                print'    size: %s' % ppsize(size)
            print '    %s: %s' % (key, acc[key])
    if options.all:  print db.accounts.count()-1, 'accounts total' # -1 for _autoinc

    con.disconnect()


def activate(conf, options, args):
    '''When PUBLIC_REGISTRATION is set to false, you have to activate
    registered accounts manually by invoking "activate $email"'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    accounts = con[conf['MONGODB_NAME']].accounts

    if len(args) == 2:
        acc = accounts.find_one({'email': args[1]})
        if not acc:
            print '`%s` does not exist' % args[1]
            sys.exit(1)
        elif acc['activated_at'] != None:
            print '`%s` already activated' % args[1]
        else:
            act = {'activated_at': strftime('%Y-%m-%dT%H:%M:%SZ', gmtime())}
            accounts.update({'_id': acc['_id']}, {'$set': act})
            print '`%s` activated' % args[1]
    else:
        inactivated = [acc for acc in accounts.find() if not acc.get('activated_at', True)]
        if not inactivated:
            print 'no pending non-activated accounts'
        for acc in inactivated:
            print '%s [%s]' % (acc['email'].ljust(16), acc['created_at'])

    con.disconnect()

def info(conf):
    '''A basic, incomplete short info.  Displays overall file size and
    account counts.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    overall_file_size = sum([f['length'] for f in fs._GridFS__files.find()])
    inactivated = [acc for acc in db.accounts.find() if not acc.get('activated_at', True)]
    print fs._GridFS__files.count(), 'files [%s]' % ppsize(overall_file_size)
    print db.accounts.count()-1, 'accounts total,', len(inactivated) , 'not activated'

    con.disconnect()

def purge(conf, options, args):
    '''Purges files or accounts.

    With GNU Opts -a and/or --all a given account/all accounts are removed
    including metadata and files.

    Given a crontab-like timedelta e.g. `3d` will remove every file older
    than 3 days including its metadata. To delete all files write `0d` or --all.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    def delete_account(_id):
        """deletes account with _id and all his files"""

        items = db.accounts.find_one({'_id': _id})['items']
        db.accounts.remove(_id)

        for item in items:
            fs.delete(item)
            db.items.remove(item)
        return True

    if options.account and not options.all and len(args) < 2:
        log.error('purge -a <_id> requires an account _id or email')
        sys.exit(1)
    elif not options.account and not options.all and len(args) < 2:
        log.error('purge <timedelta> requires a time delta')
        sys.exit(1)

    if options.account:
        if options.all:
            yn = raw_input('delete all accounts? [y/n] ')
            if yn != 'y':
                sys.exit(0)
            print 'deleting %s accounts' % (db.accounts.count() - 1)
            for acc in db.accounts.find():
                if str(acc['_id']).startswith('_'):
                    continue
                delete_account(acc['_id'])
        else:
            query = {'_id': int(args[1])} if args[1].isdigit() else {'email': args[1]}
            query = db.accounts.find_one(query)

            if not query:
                log.error('no such _id or email `%s`', args[1])
                sys.exit(1)
            print 'deleting account `%s`' % args[1]
            delete_account(query['_id'])
    else:
        delta = timedelta(0) if options.all else tdelta(args[1])
        if delta == timedelta(0):
            yn = raw_input('delete all files? [y/n] ')
            if yn != 'y':
                sys.exit(0)
        else:
            print 'purging files older than %s' % str(delta)[:-3]

        now = datetime.utcnow()
        delete = []
        for obj in fs._GridFS__files.find():
            if now - delta > obj['uploadDate']:
                delete.append(obj)

        for cur in db.accounts.find():
            # FIXME bookmarks survive
            if str(cur['_id']).startswith('_'):
                continue
            _id, items = cur['_id'], cur['items']
            for obj in delete:
                try:
                    items.remove(obj['_id'])
                except ValueError:
                    pass
            db.accounts.update({'_id': _id}, {'$set': {'items': items}})

        for obj in delete:
            fs.delete(obj['_id'])
            db.items.remove(obj['_id'])

    con.disconnect()


def repair(conf, options):
    '''fixes issues created by myself.  Currently, only orphan files and
    item links are detected and automatically removed.'''

    con = Connection(conf['MONGODB_HOST'], conf['MONGODB_PORT'])
    db = con[conf['MONGODB_NAME']]
    fs = GridFS(db)

    objs = [obj['_id'] for obj in fs._GridFS__files.find()]
    meta = [cur['_id'] for cur in db.items.find()]

    if objs != meta:
        # 1. metadata has some files missing, no repair possible
        diff1 = filter(lambda i: not i in objs, meta)
        diff2 = filter(lambda i: not i in meta, objs)
        for item in diff1:
            print 'removing metadata for `%s`' % item
            db.items.remove(item)

        # 2. metadata is missing, but file is there. Recover possible, but not implemented #win
        for item in diff2:
            print 'removing GridFS-File `%s`' % item
            objs.remove(item)

    # rebuild accounts items, when something changed
    for cur in db.accounts.find():
        if str(cur['_id']).startswith('_'):
            continue
        _id, items = cur['_id'], cur['items']
        items = filter(lambda i: i in objs, items)
        db.accounts.update({'_id': _id}, {'$set': {'items': items}})

    con.disconnect()


def main():

    from optparse import OptionParser, make_option

    usage = "usage: %prog [options] info|account|activate|purge|repair\n" + '\n' \
            + "  info     – provides basic information of regenwolken's MongoDB\n" \
            + "  activate – lists inactive accounts or activates given email\n" \
            + "  account  – details of given (email or _id) or --all accounts\n" \
            + "  files    – summary of uploaded files --all works, too\n" \
            + "  purge    – purge -a account or files. --all works, too\n" \
            + "  repair   – repair broken account-file relations in MongoDB"

    options = [
        make_option('-a', '--account', dest='account', action='store_true',
                    default=False, help='purge account and its files'),
        make_option('--all', dest='all', action='store_true',
                    default=False, help='select ALL'),
        make_option('--conf', dest="conf", default="regenwolken.cfg", metavar="FILE",
                    help="regenwolken configuration")
    ]

    parser = OptionParser(option_list=options, usage=usage)
    (options, args) = parser.parse_args()

    log = logging.getLogger('regenwolken')
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

    app = Flask(__name__)
    app.config.from_object('regenwolken.utils.conf')
    app.config.from_envvar('REGENWOLKEN_SETTINGS', silent=True)

    path = options.conf if options.conf.startswith('/') else '../' + options.conf
    app.config.from_pyfile(path, silent=True)

    if 'info' in args:
        info(app.config)
    elif 'account' in args:
        account(app.config, options, args)
    elif 'activate' in args:
        activate(app.config, options, args)
    elif 'purge' in args:
        purge(app.config, options, args)
    elif 'repair' in args:
        repair(app.config, options)
    elif 'files' in args:
        pass
    else:
        parser.print_help()

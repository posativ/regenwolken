conf.yaml
=========

It is *no* real YAML, just enough to configure Regenwolken. This is the
current default conf.yaml:

::

    # conf.yaml for Regenwolken

    hostname: localhost
    bind_address: 0.0.0.0
    port: 80

    mongodb_host: 127.0.0.1
    mongodb_port: 27017
    mongodb_name: cloudapp

    max_content_length: 62914560
    allowed_chars: 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.- @
    allow_private_bookmarks: false
    public_registration: false

hostname
    only used (and important) for URL generation to point to your own server
    instead of *cl.ly*.
bind_address
    ip address to bind to: 0.0.0.0 binds to all interfaces, 127.0.0.1 to
    localhost only.
port
    port to listen. Note: ports < 1024 require regenwolken to run as root.

mongodb_host
    MongoDB host, defaults to local server.
mongodb_port
    MongoDB port, defaults to default port.
mongodb_name
    MongoDB database name to use.

max_content_length
    global maximum request size before 413 Request Entity Too Large is returned.
allowed_chars
    allowed chars in email address.
allow_private_bookmarks
    mark bookmarks as private (requires authentication on redirect)
public_registration
    allow instant registration of accounts. If set to false, you have to
    manually activate accounts using ``bin/manage.py activate $email``


bin/manage.py
=============

``manage.py`` is a small python script to provide some basic maintenance and
administration. Usage: ``python bin/manage.py``.

::

    $ python bin/manage.py --help
    Usage: manage.py [options] info|account|activate|purge|repair

      info     – provides basic information of Regenwolken's MongoDB
      activate – lists inactive accounts or activates given email
      account  – details of given (email or _id) or --all accounts
      files    – summary of uploaded files --all works, too
      purge    – purge -a account or files. --all works, too
      repair   – repair broken account-file relations in MongoDB

    Options:
      -a, --account  purge account and its files
      --all          select ALL
      -h, --help     show this help message and exit

The interface is currently not really user-friendly but at least works. You
must invoke with at least one positional keyword like *info* and [options]
and/or an argument.

info
    Provides basic information of Regenwolken's MongoDB. Just a short summary.
activate
    When PUBLIC_REGISTRATION is set to false, you can activate a given account
    using ``python bin/manage.py activate myaccount`` or ommit the argument to
    get a list of inactive accounts.
account
    View details or summary of all accounts. Do ``python bin/manage.py account --all``
    to get all accounts. ``python bin/manage.py myAccountId (or -Name)``.
files
    Not implemented yet. Details about stored files.
purge
    Command to delete a given file, all files (updates account relations as well)
    or account(s). ``python bin/manage.py purge --all`` deletes everything.
    ``python bin/manage.py purge 2d`` removes all files older than 2 days (works
    for (m)inutes, (h)ours and (w)eeks as well. Even combined like "3d 5h").
    
    ``python bin/manage.py -a --all`` deletes all accounts and
    ``python bin/manage.py -a myAccount`` a given accountname/id
repair
    Removes unassociated metadata or files and repairs accounts with missing
    files. Useful in developing progress.
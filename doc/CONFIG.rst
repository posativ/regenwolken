Configuration
=============

Regenwolken uses a python file for configuration that you can set in your environment
variables  via ``REGENWOLKEN_SETTINGS`` like so::

    $ export REGENWOLKEN_SETTINGS=/path/to/regenwolken.cfg
    $ regenwolken &

Here is a listing of all possible values::

    HOSTNAME = "localhost"
    BIND_ADDRESS = "0.0.0.0"
    PORT = 80
    MONGODB_HOST = "127.0.0.1"
    MONGODB_PORT = 27017
    MONGODB_NAME = 'cloudapp'
    MONGODB_SESSION_SIZE = 100*1024

    ALLOWED_CHARS = string.digits + string.ascii_letters + '.- @'
    MAX_CONTENT_LENGTH = 64*1024*1024
    ALLOW_PRIVATE_BOOKMARKS = False
    PUBLIC_REGISTRATION = False
    SHORT_ID_MIN_LENGTH = 3

    CACHE_BACKEND = 'SimpleCache'
    CACHE_TIMEOUT = 15*60

    THUMBNAILS = True
    SYNTAX_HIGHLIGHTING = True
    MARKDOWN_FORMATTING = True

HOSTNAME
    only used (and important) for URL generation to point to your own server
    instead of *cl.ly*.
BIND_ADDRESS
    ip address to bind to: 0.0.0.0 binds to all interfaces, 127.0.0.1 to
    localhost. Only needed when run via ``regenwolken``.
PORT
    port to listen. Note: ports < 1024 require regenwolken to run as root. Only
    needed when run via ``regenwolken``.
LOGFILE
    destination where exception and other important events will be logged to.

MONGODB_SESSION_SIZE
    Set collection size for sessions to N bytes. Increase if you experience 401
    when uploading files.

ALLOWED_CHARS
    Allowed chars in email address.
MAX_CONTENT_LENGTH
    Global maximum request size before 413 Request Entity Too Large is
    raised, default is 64 megabytes.
ALLOW_PRIVATE_BOOKMARKS
    Allows bookmarks upload or marked as private. Only affects new uploaded
    bookmarks. Private bookmarks requires authentication on redirect, as well.
PUBLIC_REGISTRATION
    Allows instant registration of new accounts. If set to false, you have to
    manually activate accounts by invoking ``bin/manage.py activate $email``
SHORT_ID_MIN_LENGTH
    Minimum length of the short_id link (e.g. http://example.org/af3d). Retries
    three times to generate a non-existing random id before length
    is incremented by 1.

THUMBNAILS
    dis/enables thumbnail creation of (by PIL) known images.
SYNTAX_HIGHLIGHTING
    dis/enables pygments powered syntax highlighting. If you remove this
    dependency, regenwolken is not able to recognize sourcecode file extensions
    as text-type.
MARKDOWN_FORMATTING
    dis/enables markdown formatting of files ending with .md, .mkdown, .markdown


rwctl
=====

``rwctl`` is a small python script to provide some basic maintenance and
administration.

::

    $ rwctl --help
    Usage: rwctl [options] info|account|activate|purge|repair

      info     – provides basic information of regenwolken's MongoDB
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
    Provides basic information of regenwolken's MongoDB. Just a short summary.
activate
    When PUBLIC_REGISTRATION is set to false, you can activate a given account
    using ``rwctl activate myaccount`` or ommit the argument to
    get a list of inactive accounts.
account
    View details or summary of all accounts. Do ``rwctl account --all``
    to get all accounts. ``rwctl myAccountId (or -Name)``.
files
    Not implemented yet. Details about stored files.
purge
    Command to delete a given file, all files (updates account relations as well)
    or account(s). ``rwctl purge --all`` deletes everything.
    ``rwctl purge 2d`` removes all files older than 2 days (works
    for (m)inutes, (h)ours and (w)eeks as well. Even combined like "3d 5h").

    ``rwctl -a --all`` deletes all accounts and
    ``rwctl -a myAccount`` a given accountname/id
repair
    Removes unassociated metadata or files and repairs accounts with missing
    files. Useful in developing progress.

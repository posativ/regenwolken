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
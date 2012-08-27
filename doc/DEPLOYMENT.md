Deploy regenwolken
==================

You'll need at [python][1] ≥ 2.5, [Flask][2] and [pymongo][3] for [MongoDB][4] bindings
and a working MongoDB instance:

On a debian-like system run:

    apt-get install python python-dev mongodb

and then

    pip install regenwolken  # or master from GitHub
    pip install --upgrade git+git://github.com/posativ/regenwolken.git#egg=regenwolken

If you want additional syntax highlighting, markdown support and image
thumbnailing, also run `easy_install -U pygments markdown PIL` respectively.

*NOTE:* if you're using python 2.5, you'll also need `simplejson`.

[1]: http://python.org/
[2]: http://flask.pocoo.org/
[3]: http://api.mongodb.org/python/current/
[4]: http://www.mongodb.org/

[uWSGI][5]
----------

uWSGI has explicit support for virtual environments, so I highly recommend this
method! But unfortunately uWSGI is not shipped with Debian Squeeze, so we have to
type two additional commands as root.

    # apt-get install build-essential python-dev libxml2-dev
    # easy_install uwsgi virtualenv

Now as regular user, choose a path where you want a isolated environment.

    $ virtualenv /path/to/regenwolken/
    $ cd /path/to/regenwolken && source bin/activate

Now we can install all python eggs outside from the system's python. The following
will install regenwolken and libraries for thumbnail support, syntax highlighting and
markdown conversion of text snippets.

    $ easy_install regenwolken PIL pygments markdown
    $ uwsgi -H /path/to/regenwolken/ --http :3000 -M -w "regenwolken:Regenwolken()"

I usually run my services with `start-stop-daemon` (Debian/Ubuntu) so I can manage them
as root but they still run in user space. The following assumes you have your configuration
file stored in `/path/to/regenwolken/rw.cfg`.

    $ cat /etc/init.d/regenwolken
    #!/bin/sh

    NAME=regenwolken
    CHDIR=/path/to/regenwolken/
    USER=py
    DAEMON_OPTS="-H ${CHDIR} --http :8012 -M --env REGENWOLKEN_SETTINGS=${CHDIR}rw.cfg -w regenwolken:Regenwolken()"

    case $1 in
        start)
        echo -n "Starting $NAME: "
        start-stop-daemon --start --pidfile /var/run/$NAME.pid --chdir $CHDIR \
        --chuid $USER --make-pidfile --background --exec /usr/local/bin/uwsgi -- $DAEMON_OPTS || true
        echo "$NAME."
           ;;
    stop)  kill -9 $(cat /var/run/$NAME.pid)
           ;;
    esac

[5]: http://projects.unbit.it/uwsgi/

[gunicorn][6] and lighttpd + `mod_proxy` (or similar proxy methods)
-------------------------------------------------------------------

Running regenwolken with gunicorn achieves the best performance. See
`gunicorn -h` to get a full list of options. Install [gunicorn][5] via

    easy_install -U gunicorn
    gunicorn -w 4 -b localhost:3000 "regenwolken:Regenwolken()"

to run it with four workers. (`sudo guni... -b localhost:80` works too,
but is not recommended because of root privileges.)

[6]: http://gunicorn.org/

using lighttpd + `mod_proxy`
----------------------------

Recommended way. Use some proxy-magic and run it as non-privileged user. Edit
your /etc/lighttpd/lighttpd.conf to something like this:

    $HTTP["host"] =~ "domain.tld|my.cl.ly" {

        # some other stuff related to domain.tld

        $HTTP["host"] =~ "domain.tld|my.cl.ly" {
            proxy.server = ("" =>
               (("host" => "127.0.0.1", "port" => 3000)))
        }
    }

- start mongodb via `invoke-rc.d start mongodb` (if not already running)
- run `regenwolken` as non-privileged user

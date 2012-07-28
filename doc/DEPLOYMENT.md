Deploying regenwolken
=====================

You'll need at [python][1] ≥ 2.6, [Flask][2] and [pymongo][3] for [MongoDB][4] bindings
and a working MongoDB instance:

On a debian-like system run:

    apt-get install python python-dev mongodb

and then

    easy_install -U regenwolken

If you want additional syntax highlighting, markdown support and image
thumbnailing, also run `easy_install -U pygments markdown PIL` respectively.

*NOTE:* if you're using python 2.5, you'll need `easy_install -U simplejson`.

[1]: http://python.org/
[2]: http://flask.pocoo.org/
[3]: http://api.mongodb.org/python/current/
[4]: http://www.mongodb.org/

using lighttpd + `mod_proxy`
----------------------------

Recommended way. Use some proxy-magic and run it as non-privileged user. Edit
your /etc/lighttpd/lighttpd.conf to something like this:

    $HTTP["host"] =~ "cloud.org|my.cl.ly" {

        # some other stuff related to cloud.org

        $HTTP["host"] =~ "my.cloud.org|my.cl.ly" {
            proxy.server = ("" =>
               (("host" => "127.0.0.1", "port" => 9000)))
        }
    }

- start mongodb via `invoke-rc.d start mongodb` (if not already running)
- set "port: 9000" in your *regenwolken.cfg*
- run `regenwolken` as non-privileged user

quick & dirt testing as HTTP server
-----------------------------------

*NOTE:* not recommended for production usage, because it requires to be run as root

- start mongodb via `invoke-rc.d start mongodb` (if not already running)
- set "port: 80" in your *regenwolken.cfg*
- run `sudo regenwolken` as non-privileged user


[gunicorn][5] and lighttpd + `mod_proxy` (or similar proxy method)
------------------------------------------------------------------

Running regenwolken with gunicorn achieves the best performance. See
`gunicorn -h` to get a full list of options. Install [gunicorn][5] via

    easy_install -U gunicorn
    gunicorn -w 4 -b localhost:9000 "regenwolken:Regenwolken()"

to run it with four workers. (`sudo guni... -b localhost:80` works too,
but is not recommended because of root privileges.)

[5]: http://gunicorn.org/


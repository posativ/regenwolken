Deploying regenwolken
=====================

You'll need at least [python][1] (>= 2.5). In addition, regenwolken relies on
the WSGI framework [werkzeug][2], the [jinja2][3] templating engine and
[pymongo][4] for [MongoDB][5] bindings and a working MongoDB instance:

On a debian-like system run:

    apt-get install python python-dev mongodb

and then

    easy_install -U werkzeug jinja2 pymongo
    
If you want additional syntax highlighting, markdown support and image
thumbnailing, also run `easy_install -U pygments markdown PIL` respectively.

*NOTE:* if you're using python 2.5, you'll need `easy_install -U simplejson`.

[1]: http://python.org/
[2]: http://werkzeug.pocoo.org/
[3]: http://jinja.pocoo.org/
[4]: http://api.mongodb.org/python/current/
[5]: http://www.mongodb.org/

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
- set "port: 9000" in your *conf.yaml*
- run `python regenwolken.py` as non-privileged user
    
quick & dirt testing as HTTP server
-----------------------------------

*NOTE:* not recommended for production usage, because it requires to be run as root

- start mongodb via `invoke-rc.d start mongodb` (if not already running)
- set "port: 80" in your *conf.yaml*
- run `sudo python regenwolken.py` as non-privileged user


[gunicorn][6] and lighttpd + `mod_proxy` (or similar proxy method)
------------------------------------------------------------------

Running regenwolken with gunicorn achieves the best performance. See
`gunicorn -h` to get a full list of options. Install [gunicorn][6] via

    easy_install -U gunicorn
    gunicorn -w 4 -b localhost:9000 regenwolken:app
    
to run it with four workers. (`sudo guni... -b localhost:80` works too,
but is not recommended because it needs root privileges.)

[6]: http://gunicorn.org/


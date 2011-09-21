# Regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! Regenwolken offers an
alternate API implementation; hosted on your own server!

### Installation

You'll need [python](http://python.org/) 2.5 or higher and easy_install (or
pip) (e.g. `apt-get install python-setuputils`). Regenwolken uses
[GridFS](http://www.mongodb.org/display/DOCS/GridFS) as file storage backend,
therefore you need [MongoDB](http://mongodb.org/) 1.6 or higher.

    pip install pymongo werkzeug # or
    easy_install pymongo werkzeug
    
    # python2.5 users will need simplejson as well
    pip install simplejson
    
To work as an alternative CloudApp-server, you have to edit their DNS
*my.cl.ly* to your own IP in /etc/hosts. This will not interfere with
CloudApp-Service itself, because they're using *cl.ly* for sharing.

    > cat conf.yaml
    hostname: my.cloud.org
    bind_address: 0.0.0.0
    port: 80 # or 9000 for mod_proxy

    mongodb_host: 127.0.0.1
    mongodb_port: 2701

### Setup

There are two different setups: serve on port 80 as HTTP server or use a
proxy. For the next setp, I assume you'll host Regenwolken on *my.cloud.org*.
      
First start MongoDB via `mongod --dbpath path/to/some/folder` and edit your
*local* machine (where you run e.g. Cloud.app) */etc/hosts* (replace 127.0.0.1
with the desired IP):

    127.0.0.1 my.cl.ly
    127.0.0.1 ws.pusherapp.com # <-- stratus app will drive insane without

#### as HTTP server

This will setup Regenwolken as primary HTTP-Server, listening on Port 80.
Therefore, you'll need root access.

- check, there is no other process on port 80
- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `sudo python wolken.py`
- edit /etc/hosts to
- finally launch Cloud.app, register and then log in
- take a test screenshot

#### using lighttpd and mod_proxy

Recommended way. Use some proxy-magic and run it as non-privileged user. Edit
your /etc/lighttpd/lighttpd.conf to something like this:

    $HTTP["host"] =~ "cloud.org|my.cl.ly" {
        
        # some other stuff related to cloud.org
        
        $HTTP["host"] =~ "my.cloud.org|my.cl.ly" {
            proxy.server = ("" =>
               (("host" => "127.0.0.1", "port" => 9000)))
        }
    }


- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `python regenwolken.py` as non-privileged user
- finally launch Cloud.app, register and log in
- take a test screenshot

#### hints

You might wonder, why we ask for "my.cloud.org|my.cl.ly". Your /eth/hosts
will resolve my.cl.ly to your server IP and requesting with the *Host* my.cl.ly,
but it returns an URL pointing to your (real) server/domain.

Note: you should set a *hostname* (=domain name) in conf.yaml, where you host
Regenwolken. This will return into customized URLs, pointing directly to the
ressource.

### Configuration and Usage

See [USAGE.rst](/posativ/regenwolken/blob/master/doc/USAGE.rst) for a detailed
instruction manual.

### API implementation

Regenwolken provides all API calls to get Cloud.app working and has only few
calls of [CloudApp's API](http://developer.getcloudapp.com/) missing. See
[API.md](/posativ/regenwolken/blob/master/doc/API.md) for a complete list of
features. Below, the following are currently covered by the web interface.
    
    # -H "Accept: text/html"
    
    /              - GET basic web interface
    /<short_id>    - GET file or redirect from bookmark

Thanks to [cmur2](https://github.com/cmur2) for his feature-rich
[CLI](https://github.com/cmur2/cloudapp-cli) and help to build this service!

### Clients

#### working

- Mac OS X [Cloud](http://itunes.apple.com/us/app/cloud/id417602904?mt=12&ls=1)
- [cloudapp-cli](https://github.com/cmur2/cloudapp-cli)
- [Stratus](http://www.getstratusapp.com/) – CloudApp Client for iOS, but failing sometimes
- [Cloudette](http://cloudetteapp.com/) – free CloudApp iPhone client, works flawlessly

#### failing clients

- Windows' [FluffyApp](http://fluffyapp.com/), fails to login

### Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
- [short description in my blog](https://blog.posativ.org/2011/regenwolken-hosting-cloudapp-on-your-own-server/)
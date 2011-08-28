# Regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! Regenwolken offers an
alternate API implementation; hosted on your own server!

### Installation

You'll need [python](http://python.org/) 2.5 or higher and easy_install (or
pip) (e.g. `apt-get install python-setuputils`). Regenwolken uses
[GridFS](http://www.mongodb.org/display/DOCS/GridFS) as file storage backend,
therefore you need [MongoDB](http://mongodb.org/) 1.6 or higher.

    pip install pymongo bottle # or
    easy_install pymongo bottle
    
    # python2.5 users will need simplejson as well
    pip install simplejson
    
To work as an alternative CloudApp-server, you have to edit their DNS *my.cl.ly*
to your own IP in /etc/hosts. This will not interfere with CloudApp itself,
because they're using *cl.ly* for sharing.

    python wolken.py --help
    Usage: wolken.py [options] [Hostname]

    Options:
      --bind=IP        binding address, e.g. localhost [default: 0.0.0.0]
      --port=PORT      port, e.g. 80 [default: 9000]
      --mdb-host=HOST  mongoDB host [default: localhost]
      --mdb-port=PORT  mongoDB port [default: 27017]
      -h, --help       show this help message and exit

### Setup

There are two different setups: serve on port 80 as HTTP server or use a proxy.
For the next setp, I assume you'll host Regenwolken on *my.cloud.org*.
      
First start MongoDB via `mongod --dbpath path/to/some/folder` and edit your
*local* (means, where you'll use Cloud.app) /etc/hosts (replace 127.0.0.1
with the desired IP):

    127.0.0.1 my.cl.ly


#### as HTTP server

- check, there is no other process on port 80
- run `python wolken.py my.cloud.org` as root
- finally launch Cloud.app and log in with `leave@thecloud:now` as user:passwd.

- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `sudo python wolken.py [host]`
- edit /etc/hosts to
- take a test screenshot

Warning: I'm happy, Cloud.app works, but I do not claim wolken.py is non-exploitable!

#### using lighttpd and mod_proxy

(I recommend this way, I don't even trust software I've written myself). Edit
your /etc/lighttpd/lighttpd.conf to something like this:

    $HTTP["host"] =~ "cloud.org|my.cl.ly" {
        
        # some other stuff related to cloud.org
        
        $HTTP["host"] =~ "my.cloud.org|my.cl.ly|" {
            proxy.server = ("" =>
               (("host" => "127.0.0.1", "port" => 9000)))
        }
    }


- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `python wolken.py my.cloud.org` as non-privileged user
- take a test screenshot

You might wonder, why we ask for "my.cloud.org|my.cl.ly". Your /eth/hosts
will resolve my.cl.ly to your server IP and requesting with the *Host* my.cl.ly,
but it returns an URL pointing to your (real) server/domain.

Note: you should invoke the script with a hostname (=domain name), where you
are hosting Regenwolken. This will return into customized URLs, pointing
directly to the ressource.

### Implementation

Regenwolken currently provides only a small subset (but enough to get
Cloud.app working) of [CloudApp's API](http://developer.getcloudapp.com/).

    /account    - basic account info
    /items      - browse uploads
    /items/new  - preparing new upload
    /items/hash - return data
    /           - POST data
    

### (current) Limitations

- Finder -> send via CloudApp fails utterly
- CloudApp is not SSL at all
- only public uploads
- no web-API at all

### Todo:

- implement file <-> user relations and some configurations like maximum file size limit
- test SSL encryption (silent client-side redirection)
- cleanup

### Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
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

### Run

- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `sudo python wolken.py [host]`
- edit /etc/hosts to

/etc/hosts

    127.0.0.1 my.cl.ly
    
    # below not required, but recommended (privacy)
    # 127.0.0.1 ws.pusherapp.com
    # 127.0.0.1 pusherapp.com
    # 127.0.0.1 f.cl.ly
    
- finally launch Cloud.app and log in with `leave@thecloud:now` as user:passwd.
- take a test screenshot

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

### Todo:

- implement file <-> user relations and some configurations like maximum file size limit
- test SSL encryption (silent client-side redirection)
- cleanup

### Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
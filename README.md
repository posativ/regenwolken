# Regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! Regenwolken offers an
alternate API implementation; hosted on your own server!

### Installation

- python2.6 or higher
- MongoDB (relying on GridFS)

- pip install pymongo bottle

### Run

- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `sudo python wolken.py [host]`
- edit /etc/hosts to

/etc/hosts

    127.0.0.1 ws.pusherapp.com
    127.0.0.1 pusherapp.com

    127.0.0.1 f.cl.ly
    127.0.0.1 my.cl.ly
    
- finally launch Cloud.app and log in with `leave@thecloud:now` as user:passwd.
- take a test screenshot

### (current) Limitations

- Finder -> send via CloudApp fails utterly
- CloudApp is not SSL at all
- only public uploads

### Todo:

- session management (Cloud.app does not send the cookie :-/)
- test SSL encryption (silent client-side redirection)
- cleanup

### Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
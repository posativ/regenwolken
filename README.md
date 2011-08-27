# Regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! Regenwolken offers an
alternate API implementation; hosted on your own server!

## Installation

- python2.6 or higher
- MongoDB (relying on GridFS)

- pip install pymongo bottle

## Run

- start MongoDB via `mongod --dbpath path/to/some/folder`
- run `sudo python wolken.py`
- edit /etc/hosts to
    
    127.0.0.1 ws.pusherapp.com
    127.0.0.1 pusherapp.com

    127.0.0.1 f.cl.ly
    127.0.0.1 my.cl.ly
    
- finally launch Cloud.app and take a test screenshot

## (current) Limitations

- you must login one time into cloudapp.com
- Finder -> send via CloudApp fails utterly (mem leak)
- CloudApp is not SSL at all

## Todo:

- enable authentication
- test SSL encryption (silent client-side redirection)
- cleanup

## Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
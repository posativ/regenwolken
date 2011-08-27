# Regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! Regenwolken offers an
alternate API implementation; hosted on your own server!

### Installation

- python2.5 or higher
- MongoDB (relying on GridFS)

- pip install pymongo bottle (python 2.5 needs simplejson as well)

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

If your mongodb server is not on localhost:27017 you have to edit the
script (last lines); same for alternative binding adress (default:
localhost:80).

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
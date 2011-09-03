# Bugs found by Regenwolken

## Cloud.app – official Mac App

Cloud.app features a broken web browser, which follows any redirects and is
able to authenticate via HTTP Digest Authentication specified in [RCF2617][1].

[1]: https://tools.ietf.org/html/rfc2617

Features:

    - Redirects: yes, wherever you want
    - Cookies: yes, but not transmitted to different URLs on the same host -> senseless
    - HTTP Digest Auth RFC2069: not tested
    - HTTP Digest Auth RFC2617: works
    - SSL: not tested
    
Bugs:

    - automatic screenhots uploading adds a \u0000 char to the end of
      the filename. Server-side seems to fix it.  Would break e.g. `cloudapp_api`
    - /register: HTTP 201 -> success, but there is no way, to indicate, what
      could be wrong with the current username (exists e.g.)
    - Cloud.app can not handle 413 Request Entity Too Large
      
      
## cloudapp_api (Ruby wrapper)

    - missing HTTP Digest Auth RFC 2617 in httpary, see
      https://github.com/posativ/regenwolken/issues/8
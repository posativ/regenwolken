# Bugs found by Regenwolken

## Cloud.app – official Mac App

Cloud.app features a broken web browser, which follows any redirects and is
able to authenticate via HTTP Digest Authentication specified in [RCF2617][1].

[1]: https://tools.ietf.org/html/rfc2617

REST-API Features:

    - Redirects: yes, wherever you want
    - Cookies: yes, but not transmitted to different URLs on the same host -> senseless
    - HTTP Digest Auth RFC2069: not tested
    - HTTP Digest Auth RFC2617: works
    - SSL: not tested
    
Bugs:

    - adds a \u0000 char at the end of filename. Server-side seems to fix it.
      Would break cloudapp_api e.g
      
      
## cloudapp_api (Ruby wrapper)

    - missing HTTP Digest Auth RFC 2617 in httpary, see
      https://github.com/posativ/regenwolken/issues/8
# regenwolken – an open source CloudApp server

[Cloud.app][app] is *really* handy, sharing files was never that easy. But I don't
like to see (personal) data like screenshots or code snippets go out of my
reach. Regenwolken is a full-featured implementation of the Cloud App API with
one malus: you have do edit your `/etc/hosts`.

#### open server

I've set up a server open for everyone. Simply, add `213.218.178.67 my.cl.ly`
to your `/etc/hosts`. Items older than three days will be purged at midnight
(only a small vserver). Happy testing!

## Quickstart

Short instructions for OS X, adapt these commands to your linux distribution
of choice (Debian Squeeze!).

    $ brew install mongodb
    $ mongod --dbpath foo/ &

Now install Regenwolken and its dependencies:

    $ easy_install regenwolken
    $ easy_install pygments PIL markdown  # optional

Modify /etc/hosts, launch regenwolken and register a new account

    $ sudo echo "127.0.0.1 my.cl.ly" >> /etc/hosts
    $ regenwolken &
    [... open Cloud.app or another client and register a new account]
    $ rwctl activate USERNAME

## How to use regenwolken

As an alternative CloudApp-server, you have to edit their DNS *my.cl.ly*
to point to your own IP. This will not interfere with CloudApp Service
itself, because they are using *cl.ly* and *f.c.ly* for sharing.

    $ sudo echo "12.34.56.78 my.cl.ly" >> /etc/hosts

Note: you should set a *hostname* (= your domain) in regenwolken.cfg.
This will return into customized URLs, pointing directly to your host,
so others don't need to modify their hosts.

## Setup and Configuration

See [DEPLOYMENT.md](/posativ/regenwolken/blob/master/doc/DEPLOYMENT.md) and
[CONFIG.rst](/posativ/regenwolken/blob/master/doc/CONFIG.rst) for details.

## API implementation

regenwolken provides all API calls to get Cloud.app working and has only few
calls of [CloudApp's API](http://developer.getcloudapp.com/) missing. See
[API.md](/posativ/regenwolken/blob/master/doc/API.md) for a complete list of
features. Below, the following are currently covered by the web interface.

    # -H "Accept: text/html"

    /                          - GET basic web interface
    /items/<short_id>          - GET file or redirect from bookmark
    /items/<short_id>/filename - GET same as /items/<short_id>
    /<short_id>                - GET viso-like file view or redirect from bookmark
    /thumb/<short_id>          - GET thumbnail of item

Thanks to [cmur2](https://github.com/cmur2) for his feature-rich
[CLI](https://github.com/cmur2/cloudapp-cli) and help to build this service!

## Clients

### working

- Mac OS X [Cloud.app][app]
- [Cloudette](http://cloudetteapp.com/) – free CloudApp iPhone client, works flawlessly
- [BlueNube](http://bluenubeapp.com/) – 1,99$ iPad client
- [Stratus](http://www.getstratusapp.com/) – CloudApp Client for iOS (iPhone/iPad); add `127.0.0.1 ws.pusherapp.com` to /etc/hosts as well.
- [cloudapp-cli](https://github.com/cmur2/cloudapp-cli) – commandline tool
- [JCloudApp](https://github.com/cmur2/jcloudapp) – cross-platform Cloud.app widget in Java
- [gloudapp](https://github.com/cmur2/gloudapp) – linux+GTK-based client

### failing clients

- Windows' [FluffyApp](http://fluffyapp.com/), fails to login

## Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
- [short description in my blog](http://blog.posativ.org/2011/regenwolken-hosting-cloudapp-on-your-own-server/)

[app]: http://itunes.apple.com/us/app/cloud/id417602904?mt=12&ls=1

# regenwolken – an open source, self-hosting Cloud.app

[CloudApp](http://getcloudapp.com/) sucks! Well, Cloud.app is really handy –
but it's free of charge and this can't be good! regenwolken offers an
alternate API implementation; hosted on your own server!

#### playground

I've set up a server open for everyone. Simply, add `213.218.178.200 my.cl.ly`
to your `/etc/hosts`. Items older than three days will be purged at midnight
(only a small vserver). Happy testing!

### How to use regenwolken
    
To work as an alternative CloudApp-server, you have to edit their DNS
*my.cl.ly* to point your own IP in /etc/hosts. This will not interfere with
CloudApp-Service itself, because they're using *cl.ly* and *f.c.ly* for
sharing.

*/etc/hosts*

    127.0.0.1 my.cl.ly

You might wonder, why we ask for "my.cloud.org|my.cl.ly". Your /etc/hosts
will resolve my.cl.ly to your server IP and requesting with the *Host* my.cl.ly,
but it returns an URL pointing to your (real) server/domain.

Note: you should set a *hostname* (=domain name) in conf.yaml, where you host
regenwolken. This will return into customized URLs, pointing directly to your
server.

### Setup and Configuration

There are two different setups: serve on port 80 as HTTP server or use a
proxy. See [DEPLOYMENT.md](/posativ/regenwolken/blob/master/doc/DEPLOYMENT.md)
for detailed instruction. For configuration details see
[USAGE.rst](/posativ/regenwolken/blob/master/doc/USAGE.rst).

### API implementation

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

### Clients

#### working

- Mac OS X [Cloud.app](http://itunes.apple.com/us/app/cloud/id417602904?mt=12&ls=1)
- [Cloudette](http://cloudetteapp.com/) – free CloudApp iPhone client, works flawlessly
- [BlueNube](http://bluenubeapp.com/) – 1,99$ iPad client
- [Stratus](http://www.getstratusapp.com/) – CloudApp Client for iOS (iPhone/iPad); add `127.0.0.1 ws.pusherapp.com` to /etc/hosts as well.
- [cloudapp-cli](https://github.com/cmur2/cloudapp-cli) – commandline tool
- [JCloudApp](https://github.com/cmur2/jcloudapp) – cross-platform Cloud.app widget in Java
- [gloudapp](https://github.com/cmur2/gloudapp) – linux+GTK-based client

#### failing clients

- Windows' [FluffyApp](http://fluffyapp.com/), fails to login

### Links:

- [rixth/raincloud](https://github.com/rixth/raincloud) – a (full?) cloud
  implementation written in node.js
- [short description in my blog](https://blog.posativ.org/2011/regenwolken-hosting-cloudapp-on-your-own-server/)
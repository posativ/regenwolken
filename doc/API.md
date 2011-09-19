# API overview and implementation details

Regenwolken currently supports (see <http://developer.getcloudapp.com/>):

#### Account

- [Change Default Security](http://developer.getcloudapp.com/change-default-security)
- [Change Email](http://developer.getcloudapp.com/change-email)
- [Change Password](http://developer.getcloudapp.com/change-password)
- [Register](http://developer.getcloudapp.com/register)
- [View Account Details](http://developer.getcloudapp.com/view-account-details)
- [View Account Stats](http://developer.getcloudapp.com/view-account-stats)

#### Items

- [Bookmark Link](http://developer.getcloudapp.com/bookmark-link)
- [Bookmark Multiple Links](http://developer.getcloudapp.com/bookmark-multiple-links)
- [Change Security of Item](http://developer.getcloudapp.com/change-security-of-item)
- [Delete Item](http://developer.getcloudapp.com/delete-item)
- [List Items](http://developer.getcloudapp.com/list-items)
- [List Items by Source](http://developer.getcloudapp.com/list-items-by-source)
- [Recover Deleted Item](http://developer.getcloudapp.com/recover-deleted-item)
- [Rename Item](http://developer.getcloudapp.com/rename-item)
- [Upload File](http://developer.getcloudapp.com/upload-file)
- [Upload File With Specific Privacy](http://developer.getcloudapp.com/upload-file-with-specific-privacy)
- [View Item](http://developer.getcloudapp.com/view-item)

#### not implemented

- [Forgot Password](http://developer.getcloudapp.com/forgot-password)
- [Set Custom Domain](http://developer.getcloudapp.com/set-custom-domain)
- [Empty Trash](http://developer.getcloudapp.com/empty-trash)
- [Stream Items](http://developer.getcloudapp.com/streaming-items)
- [View Domain Details](http://developer.getcloudapp.com/view-domain-details)
- [Redeem Gift Card](http://developer.getcloudapp.com/redeem-gift-card)
- [View Gift Card Details](http://developer.getcloudapp.com/view-gift-card)

## Overview

    # -H "Accept: application/json"

    /*                 - POST files
    /items*            - POST (multiple) bookmarks
    /register          - POST register (instantly) new account
    /<short_id>        - GET item details
    /account*          - GET account info
    /account/stats*    - GET overall file count and views
    /items*            - GET list of uploaded items
    /items/new*        - GET key for new upload
    /items/new?item['private]=true|false* - GET key for new upload
    /items/<short_id>* - PUT rename/recover/change privacy of item
    /account*          - PUT change password, username and default privacy
    /items/<short_id>* - DELETE item

URLs marked with an asterix (*) require authentication.


## Details

While Regenwolken tries to simulate the [CloudApp][1] API as good as possible
using their sparse documentation details, there is one major point,
Regenwolken handles different: private and public items. CloudApp *thinks*,
items are private, when they have a longer hash. That's no joke, that's their
current implementation. When you upload a file without privacy hint, it tries
to get the hash as short as possible, e.g. [cl.ly/5hd](). When you make this
item private, the hash will change in something like this
[cl.ly/29xgnqa49ny84jg83l](). This is *security by obscurity*. In Regenwolken,
your private items requires authentication. Only when you know the
credentials, you have access to your private data.

Another thing are *bookmarks* and *files*. I decided, to use [Heise][2]'s (a
popular german site) link scheme: host.tld/-mylink, notice the dash. Files
have no dash in front. Regenwolken also does not need an email-address to
register (but most clients force you to do so), alphanumeric names without @
and . are supported, by default.

### upload-file (with given privacy)

CloudApp uses [Heroku][3] and [S3][4] as their database and storage backend.
Regenwolken only features one webservice. The upload progress divided into two
parts: `GET /items/new` (optional with privacy specs) to receive the upload
URL as well as some CloudApp specific stuff we don't need (AWSAccessKeyId,
signature, policy and redirect). Every client behaves the same and POSTs the
server's response json to the `url`, which is *my.cl.ly* and Regenwolken is
listening to. You see, `GET` and `POST` are completely different requests and
URLs, therefore you will receive a `key=1234` on `/items/new` you will include
when POSTing your files. If the server accepts your “upload key” (=~ session,
timeout after 60 minutes per default), your upload is valid.

## HTTP status codes

    200 Ok           - everything fine
    201 Ok           - register was successfully
    301 Redirect     - redirect instantly to new URL
    400 Bad Request  - wrong json
    401 Unauthorized - requires authentication
    403 Unauthorized - authentication failure
    404 Not Found    - short_id/_id is not found
    406 User already exists - when /register-ing an alreay existing user
    409 Conflict     - account not activated
    413 Request Entity Too Large - our size limit is 64 MiB
    
### HTTP Digest Authentication and salted passwords

CloudApp Network stores the users' password as plain text. This is the
main dis-advantage of HTTP Digest Auth, which requires access to the plain
password to generate proper hashes sent over the internet.

[1]: http://getcloudapp.com/
[2]: http://heise.de/
[3]: http://heroku.com/
[4]: http://aws.amazon.com/s3
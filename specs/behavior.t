Testing MANIFEST.in

  $ [ -n "$PYTHON" ] || PYTHON="`which python`"
  $ LANG="de_DE.UTF-8" && unset LC_ALL && unset LANGUAGE
  $ LOGFILE="/tmp/rw.log"
  $ echo "y" | rwctl purge -a --all
  delete all accounts? [y/n] deleting ? accounts (glob)

Does it actually works?

  $ echo "HOSTNAME = 'localhost:3000'" > "$(pwd)/rw.cfg"
  $ export REGENWOLKEN_SETTINGS="$(pwd)/rw.cfg"
  $ regenwolken --debug > $LOGFILE 2>&1 &
  $ PID="$!"

If we do not sleep here, cram says "Fuck you" and you fall in deep depressions
  $ sleep 1
  $ cloudapp service localhost:3000
  New service saved.

  $ cloudapp -y register foo 1234
  Successfully registered but your account isn't currently activated.
  Saving login to local login storage .+ (re)

  $ rwctl activate foo
  `foo` activated

  $ echo "Hello World" > README.md
  $ cloudapp upload README.md
  http://localhost:3000/\w+ (re)

  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)

  $ echo "Foo Bar " > foo.txt
  $ URL=$(cloudapp upload foo.txt | tail -n 1)
  $ cloudapp view $(basename $URL)
  Details for \w+: (re)
    Name:     foo.txt
    Type:     text
    URL:      http://localhost:3000/\w+ (re)
    Privacy:  public
    Views:    0
    Created:  ??. ??? ???? ??:??:?? (glob)
    Updated:  ??. ??? ???? ??:??:?? (glob)

  $ cloudapp private $(basename $URL) > /dev/null
  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)
  \w+        p- text      [^ ]+ [^ ]+ http://localhost:3000/\w+        foo.txt (re)

  $ cloudapp public $(basename $URL) > /dev/null
  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)
  \w+        -- text      [^ ]+ [^ ]+ http://localhost:3000/\w+        foo.txt (re)

Delete an item (note that this will *not* actually delete the item but mark it as deleted). Next
we will recover it.

  $ cloudapp delete $(basename $URL) > /dev/null
  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)

  $ cloudapp recover $(basename $URL) > /dev/null
  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)
  \w+        -- text      [^ ]+ [^ ]+ http://localhost:3000/\w+        foo.txt (re)

But we have a kill switch... let's try.

  $ cloudapp delete $(basename $URL) > /dev/null
  $ curl -su foo:1234 --digest -H "Accept: application/json" -X POST http://localhost:3000/items/trash
  $ cloudapp list --disable-colors --deleted
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)

So now back to some basic stuff. Try to change our password to a more difficult one.

  $ cloudapp change -y password 123456 > /dev/null
  $ (curl -sI -u foo:123456 --digest http://localhost:3000/items | grep FORBIDDEN)
  [1]

Try the URL shortening service.

  $ URL=$(cloudapp bookmark foo http://google.com/ | tail -n 1)
  $ cloudapp list --disable-colors
  SLUG       p=private, d=deleted
  \w+        -- unknown   [^ ]+ [^ ]+ http://localhost:3000/\w+        README.md (re)
  \w+        -- bookmark  [^ ]+ [^ ]+ http://localhost:3000/\w+        http://google.com/ -> foo (re)

  $ curl -Is $URL | head -n 1
  HTTP/1.0 302 FOUND

Minors

  $ curl -s http://localhost:3000/domains/foo.bar
  {
    "home_page": "http://localhost:3000"
  } (no-eol)

End this madness...

  $ kill -9 $PID

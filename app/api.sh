#!/bin/bash

upload() { 
    curl -s \ #--digest -u leave@thecloud:now \
         -F "file=@../README.md" \
         "http://my.cl.ly:5000/"
}

list_items() {
    curl -v --digest -u test:qq \
        "http://my.cl.ly:5000/items?page=1&per_page=5&type=image&deleted=true"
}

auth() {
    curl -v --digest -u leave@thecloud:now -H "Accept: application/json" \
         "http://my.cl.ly:5000/$1"
}

register() {
    curl -v -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -d \
        '{
          "user": {
            "email":      "arthur@dent.com",
            "password":   "towel",
            "accept_tos": true
          }
        }' \
     http://my.cl.ly/register
}

#upload
list_items
#auth items/new
#register
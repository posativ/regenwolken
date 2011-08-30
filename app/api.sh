#!/bin/bash

upload() { 
    curl -s \ #--digest -u leave@thecloud:now \
         -F "file=@../README.md" \
         "http://my.cl.ly:5000/"
}

list_items() {
    curl -v --digest -u leave@thecloud:now \
        "http://my.cl.ly:5000/items?page=1&per_page=5&type=image&deleted=true"
}

auth() {
    curl -v --digest -u leave@thecloud:now -H "Accept: application/json" \
         "http://my.cl.ly:5000/$1"
}

upload
#list_items
#auth items/new
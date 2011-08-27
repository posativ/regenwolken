#!/bin/bash

upload() { 
    curl -s \ #--digest -u leave@thecloud:now \
         -F "file=@../README.md" \
         "http://my.cl.ly/"
}

list_items() {
    curl -s "http://my.cl.ly/items?page=1&per_page=5&type=image&deleted=true"
}

auth() {
    curl -i -s --digest -u leave@thecloud:now -H "Accept: application/json" \
         "http://my.cl.ly/$1"
}

upload
#list_items
#auth items/new
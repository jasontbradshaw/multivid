#!/usr/bin/env python

import os

import bottle

import multivid

# where static files are kept
STATIC_FILES_ROOT = os.path.abspath("static")

@bottle.route("/")
def index():
    return bottle.static_file("index.html", root=STATIC_FILES_ROOT)

@bottle.route('/static/<filename:path>')
def serve_static(filename):
    return bottle.static_file(filename, root=STATIC_FILES_ROOT)

@bottle.get("/search/autocomplete")
def autocomplete():
    results = multivid.autocomplete(bottle.request.query["query"])
    return {
        "query": bottle.request.query["query"],
        "results": [r.to_dict() for r in results]
    }

@bottle.get("/search/find")
def find():
    results = multivid.find(bottle.request.query["query"])
    return {
        "query": bottle.request.query["query"],
        "results": [r.to_dict() for r in results]
    }

bottle.debug(True)
bottle.run(host="localhost", port=8000, reloader=True)

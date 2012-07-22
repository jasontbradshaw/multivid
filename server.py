#!/usr/bin/env python

import bottle

import multivid

@bottle.get("/search/autocomplete")
def autocomplete():
    return multivid.autocomplete(bottle.request.query["query"])

@bottle.get("/search/find")
def find():
    # make results objects into dicts so they can be mapped to JSON
    result_dict = multivid.find(bottle.request.query["query"])
    for originator, results in result_dict.items():
        result_dict[originator] = [r.to_dict() for r in results]

    return result_dict

bottle.debug(True)
bottle.run(host="localhost", port=8000, reloader=True)

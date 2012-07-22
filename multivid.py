#!/usr/bin/env python

import bottle

import collections
import itertools

import search
import tmap

# the canonical list of search plugins used to do all the searches
SEARCHERS = [
    search.AmazonSearch(),
    search.HuluSearch(),
    search.NetflixSearch()
]

# NOTE: we assume that all Search class implementors are thread-safe

@bottle.get("/search/autocomplete")
def autocomplete():
    # build the query function we'll map onto the searchers
    query = bottle.request.query["query"]
    qf = lambda s: s.autocomplete(query)

    # get the results in parallel
    results = tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS))

    # put the results into a dict under their searcher name
    result_dict = {}
    for searcher, result in itertools.izip(SEARCHERS, results):
        result_dict[searcher.name] = result

    # return the results as JSON
    return result_dict

@bottle.get("/search/find")
def find():
    query = bottle.request.query["query"]
    qf = lambda s: s.find(query)

    # return the results as one long list
    results = []
    for result in tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS)):
        for r in result:
            results.append(r.to_dict())

    return {"results": results}

bottle.debug(True)
bottle.run(host="localhost", port=8000, reloader=True)

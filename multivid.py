import itertools

import search
import tmap

# the canonical list of search plugins used to do all the searches
SEARCHERS = [
    search.AmazonSearch(),
    search.HuluSearch(),
    search.NetflixSearch()
]

def autocomplete(query):
    # the query function we'll map onto the searchers
    qf = lambda s: s.autocomplete(query)

    # get the results in parallel
    results = tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS))

    # put the results into a dict under their searcher name
    result_dict = {}
    for searcher, result in itertools.izip(SEARCHERS, results):
        result_dict[searcher.name] = result

    # return the results
    return result_dict

def find(query):
    qf = lambda s: s.find(query)
    results = tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS))

    result_dict = {}
    for searcher, result in itertools.izip(SEARCHERS, results):
        result_dict[searcher.name] = result

    return result_dict

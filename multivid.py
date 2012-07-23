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

    # get the results from the searchers
    searcher_results = tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS))

    # return the results as one list
    return [r for r in itertools.chain(*searcher_results)]

def find(query):
    qf = lambda s: s.find(query)
    searcher_results = tmap.map(qf, SEARCHERS, num_threads=len(SEARCHERS))
    return [r for r in itertools.chain(*searcher_results)]

import itertools

import search
import gevent

# the canonical list of search plugins used to do all the searches
SEARCHERS = [
    search.AmazonSearch(),
    search.HuluSearch(),
    search.NetflixSearch()
]

def autocomplete(query):
    # get the results from the searchers
    jobs = [gevent.spawn(s.autocomplete, query) for s in SEARCHERS]
    gevent.joinall(jobs)

    # return the results as one list
    return [job.value for job in jobs]

def find(query):
    jobs = [gevent.spawn(s.find, query) for s in SEARCHERS]
    gevent.joinall(jobs)
    return [job.value for job in jobs]

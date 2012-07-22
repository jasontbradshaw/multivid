#!/usr/bin/env python

import search
import thread_pool

if __name__ == "__main__":
    from pprint import pprint as pp
    import sys

    to_dict = lambda r: r.to_dict()

    h = search.HuluSearch()
    a = search.AmazonSearch()
    n = search.NetflixSearch()

    # get the query from the first argument or from user input
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = raw_input("search: ")

    # perform searches in parallel
    pool = thread_pool.Pool(3)

    # get a shorter query to use for autocomplete
    ac_query = query[0:3]

    ac_results = pool.map(lambda s: s.autocomplete(ac_query), (a, h, n))
    autocomplete_results = {
        "amazon": ac_results[0],
        "hulu": ac_results[1],
        "netflix": ac_results[2],
    }

    print "autocomplete results for '" + ac_query + "':"
    pp(autocomplete_results)
    print

    results = pool.map(lambda s: s.find(query), (a, h, n))
    search_results = {
        "amazon": map(to_dict, results[0]),
        "hulu": map(to_dict, results[1]),
        "netflix": map(to_dict, results[2])
    }

    print "search results for '" + query + "':"
    pp(search_results)
    print

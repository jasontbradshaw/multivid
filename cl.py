#!/usr/bin/env python

import multivid

if __name__ == "__main__":
    from pprint import pprint as pp
    import sys

    # get the query from the first argument or from user input
    if len(sys.argv) > 1:
        query = sys.argv[1]
        if query.strip() == "":
            raise ValueError("Non-blank query string is required!")
    else:
        # get a non-blank query string
        query = ""
        while query.strip() == "":
            query = raw_input("search: ")

    # get a shorter query to use for autocomplete
    ac_query = query[0:3]
    ac_results = multivid.autocomplete(ac_query)

    print "autocomplete results for '" + ac_query + "':"
    pp(ac_results)
    print

    find_results = multivid.find(query)
    for originator, results in find_results.items():
        find_results[originator] = [r.to_dict() for r in results]

    print "search results for '" + query + "':"
    pp(find_results)
    print

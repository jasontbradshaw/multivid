#!/usr/bin/env python

import base64
import hashlib
import hmac
import urllib
import time

import bs4
import requests

import arequests

class Result:
    """A video search result."""

    def __init__(self):
        self.description = None
        self.rating_fraction = None
        self.video_url = None
        self.thumbnail_url = None
        self.duration_seconds = None

    def to_dict(self):
        # return a copy of our own dict
        return dict(self.__dict__)

class TvResult(Result):
    """A television search result."""

    def __init__(self):
        self.show_title = None
        self.episode_title = None
        self.season_number = None
        self.episode_number = None

        Result.__init__(self)

class MovieResult(Result):
    """A film search result."""

    def __init__(self):
        self.title = None

        Result.__init__(self)

class Search(object):
    """Base class for search plugins."""

    def find(self, query):
        """
        Synchonously run a search for some query and return the list of results.
        If no results are found, should return an empty list.
        """

        raise NotImplemented("find must be implemented!")

    def autocomplete(self, query):
        """
        Get the list of lowercase strings suggested by the autocomplete search
        for some query, partial or otherwise. If no suggestions are found, or
        autocomplete is not supported, this should return an empty list.
        """

        raise NotImplemented("autocomplete must be implemented!")

class HuluSearch(Search):
    def __init__(self):
        # URLs we request data from
        self.search_url = "http://m.hulu.com/search"
        self.autocomplete_url = "http://www.hulu.com/search/suggest_json"

        # the maximum rating a video may receive
        self.rating_max = 5

        Search.__init__(self)

    def find(self, query):
        # we make two requests, one for movies and one for TV shows
        tv_params = {
            "page": 1,
            "type": "episode",
            "query": query
        }
        movie_params = {
            "page": 1,
            "type": "feature_film",
            "query": query
        }

        # build the requests
        tv_request = arequests.get(self.search_url, params=tv_params)
        movie_request = arequests.get(self.search_url, params=movie_params)

        # get both requests and parse their XML payloads
        tv_response, movie_response = arequests.map((tv_request, movie_request))

        tv_soup = bs4.BeautifulSoup(tv_response.text)
        movie_soup = bs4.BeautifulSoup(movie_response.text)

        results = []
        for video in tv_soup.videos("video", recursive=False):
            r = TvResult()

            r.show_title = unicode(video.show.find("name").string)
            r.episode_title = unicode(video.title.string)
            r.season_number = int(video.find("season-number").string)
            r.episode_number = int(video.find("episode-number").string)
            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.video_url = u"http://www.hulu.com/watch/" + video.id.string
            r.thumbnail_url = unicode(video.find("thumbnail-url").string)
            r.duration_seconds = int(float(video.duration.string))

            results.append(r)

        for video in movie_soup.videos("video", recursive=False):
            r = MovieResult()

            r.title = unicode(video.title.string)
            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.video_url = u"http://www.hulu.com/watch/" + video.id.string
            r.thumbnail_url = unicode(video.find("thumbnail-url").string)
            r.duration_seconds = int(float(video.duration.string))

            results.append(r)

        return results

    def autocomplete(self, query):
        params = {
            "query": query
        }

        response = requests.get(self.autocomplete_url, params=params)

        # if we got JSON data back, parse it
        if response.json is not None:
            # throw out query strings from result
            json = filter(lambda s: not isinstance(s, basestring), response.json)
            if len(json) > 0:
                return [s.lower() for s in json[0]]

        # default to returning no results
        return []

class AmazonSearch(Search):
    def __init__(self):
        # URLs we request data from
        self.search_url = "http://webservices.amazon.com/onca/xml"
        self.autocomplete_url = "http://completion.amazon.com/search/complete"

        # Amazon API keys
        self.access_key_id = ""
        self.secret_access_key = ""

        # the maximum rating a video may receive
        self.rating_max = 5

        # the number of pages of results to retrieve from the API
        self.pages_to_get = 2

        Search.__init__(self)

    @staticmethod
    def build_params(http_method, access_key_id, secret_access_key, **params):
        """
        Builds a signed dict of params acceptable to Amazon. Adds the
        'Timestamp' param automatically
        """

        # allow only GET or POST requests
        assert http_method.lower() in {"get", "post"}

        # add the timestamp and access key id params
        params["Timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        params["AWSAccessKeyId"] = access_key_id

        # quote and store all the keys and values of the sorted params
        query_string_builder = []
        for param in sorted(params.keys()):
            query_string_builder.append(param)
            query_string_builder.append("=")
            query_string_builder.append(urllib.quote(str(params[param]), "~"))
            query_string_builder.append("&")
        query_string_builder.pop()

        # build the canonical query string
        canonicalized_query_string = "".join(query_string_builder)

        # join with the HTTP method, host header, and HTTP request URI
        str_to_sign_builder = [http_method.upper()]
        str_to_sign_builder.append("webservices.amazon.com")
        str_to_sign_builder.append("/onca/xml")
        str_to_sign_builder.append(canonicalized_query_string)

        # join the strings with newlines
        str_to_sign = "\n".join(str_to_sign_builder)

        # sign the string using the secret key and sha256
        signer = hmac.new(secret_access_key, str_to_sign, hashlib.sha256)

        # add the signature to the original params and return them
        params["Signature"] = base64.b64encode(signer.digest())
        return params

    def find(self, query):
        params = AmazonSearch.build_params(
            "GET", self.access_key_id, self.secret_access_key,
            Service="AWSECommerceService", # default according to docs
            AssociateTag="N/A", # dummy tag, we don't need one
            Version="2011-08-01", # the latest version as of 7/12
            Operation="ItemSearch",
            SearchIndex="UnboxVideo", # seems to be mostly instant video
            Availability="Available",

            # related items, item data, image urls
            ResponseGroup="RelatedItems,ItemAttributes,Images",
            RelationshipType="Episode", # so we can get season name

            Keywords=query
        )

        # get all the pages of results at once
        search_requests = []
        for i in xrange(1, self.pages_to_get + 1):
            r = arequests.get(self.search_url, params=params)
            search_requests.append(r)

        # get all the items from the responses as soup objects
        results = []
        for response in arequests.map(search_requests):
            soup = bs4.BeautifulSoup(response.text)

            # iterate over all the item nodes
            for item in soup.items("item", recursive=False):
                attrs = item.itemattributes

                # are we dealing with a TV episode or a movie?
                if attrs.productgroup.string.lower().count("movie") > 0:
                    r = MovieResult()
                else:
                    r = TvResult()

                # handle tv results vs. movie results
                if isinstance(r, TvResult):
                    # prefix the title with the season name if possible
                    if item.relateditems is not None:
                        rel_attrs = item.relateditems.find("itemattributes")
                        if rel_attrs is not None:
                            # make sure it's a TV season
                            prod_group = rel_attrs.productgroup.string
                            if prod_group.lower().count("season") > 0:
                                # get the show title
                                r.show_title = unicode(rel_attrs.title.string)

                                # get the season number
                                r.season_number = int(rel_attrs.episodesequence.string)

                    r.episode_title = unicode(attrs.title.string)
                    r.episode_number = int(attrs.episodesequence.string)
                else:
                    r.title = unicode(attrs.title.string)

                r.video_url = unicode(item.detailpageurl.string)
                r.thumbnail_url = unicode(item.largeimage.url.string)

                # occasionally, there isn't a running time
                mins = attrs.find("runningtime", units="minutes")
                if mins is not None:
                    minutes = int(mins.string)
                    r.duration_seconds = 60 * minutes

                # NOTE: description and rating_fraction don't come back in the
                # results, and would take too long to scrape. we leave them
                # unset.

                results.append(r)

        return results

    def autocomplete(self, query):
        params = {
            "method": "completion",
            "mkt": 1,
            "client": "amazon-search-ui",
            "search-alias": "instant-video",
            "q": query
        }

        response = requests.get(self.autocomplete_url, params=params)

        # if we got JSON data back, parse it
        if response.json is not None and len(response.json) > 1:
            # skip the query itself and return the suggestion list
            return [s.lower() for s in response.json[1]]

        # default to returning no results
        return []

class NetflixSearch(Search):
    def __init__(self):
        base_url = "http://api-public.netflix.com"
        self.search_url = base_url + "/catalog/titles"
        self.autocomplete_url = base_url + "/catalog/titles/autocomplete"

        self.consumer_key = ""
        self.shared_secret = ""

        Search.__init__(self)

    def find(self, query):
        pass

    def autocomplete(self, query):
        params = {
            "oauth_consumer_key": self.consumer_key,
            "term": query
        }

        response = requests.get(self.autocomplete_url, params=params)
        soup = bs4.BeautifulSoup(response.text)

        results = []
        for item in soup("autocomplete_item"):
            title = unicode(item.title["short"]).lower()
            results.append(title)

        return results

if __name__ == "__main__":
    from pprint import pprint as pp

    to_dict = lambda r: r.to_dict()

    #print "Hulu:"
    #h = HuluSearch()
    #pp(h.autocomplete("c"))
    #pp(map(to_dict, h.find("c")))
    #print

    #print "Amazon:"
    #a = AmazonSearch()
    #pp(a.autocomplete("c"))
    #pp(map(to_dict, a.find("c")))
    #print

    print "Netflix:"
    n = NetflixSearch()
    pp(n.autocomplete("c"))
    pp(map(to_dict, n.find("c")))
    print

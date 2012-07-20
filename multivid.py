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
        self.title = None
        self.description = None
        self.rating_fraction = None
        self.video_url = None
        self.thumbnail_url = None

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "rating_fraction": self.rating_fraction,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url
        }

class Search(object):
    """
    Base class for search plugins. Implementing classes should call the init
    method to enable support for the supports_autocomplete property.
    """

    def __init__(self, supports_autocomplete=True):
        self.__supports_autocomplete = supports_autocomplete

    @property
    def supports_autocomplete(self):
        return self.__supports_autocomplete

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

        # only requires implementation if autocomplete is supported
        if self.supports_autocomplete:
            raise NotImplemented("autocomplete must be implemented!")
        return []

class HuluSearch(Search):
    def __init__(self):
        # URLs we request data from
        self.search_url = "http://m.hulu.com/search"
        self.autocomplete_url = "http://www.hulu.com/search/suggest_json"

        # the maximum rating a video may receive
        self.rating_max = 5

        Search.__init__(self, supports_autocomplete=True)

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
        for video in tv_soup.videos.find_all("video"):
            r = Result()

            # title it show title: episode title for tv shows
            r.title = unicode(video.show.find("name").string)
            r.title += ": " + unicode(video.title.string)

            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.video_url = u"http://www.hulu.com/watch/" + video.id.string
            r.thumbnail_url = unicode(video.find("thumbnail-url").string)

            results.append(r)

        for video in movie_soup.videos.find_all("video"):
            r = Result()

            # movie names are just the title
            r.title = unicode(video.title.string)

            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.video_url = u"http://www.hulu.com/watch/" + video.id.string
            r.thumbnail_url = unicode(video.find("thumbnail-url").string)

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
        self.pages_to_get = 3

        Search.__init__(self, supports_autocomplete=True)

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
            ResponseGroup="ItemAttributes,Images", # item data and image urls
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
            for item in soup.find("items").find_all("item"):
                r = Result()

                # NOTE: description and rating_fraction don't come back in the
                # results, and would take too long to scrape. we leave them
                # unset.
                r.title = unicode(item.itemattributes.title.string)
                r.video_url = unicode(item.detailpageurl.string)
                r.thumbnail_url = unicode(item.largeimage.url.string)

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

if __name__ == "__main__":
    from pprint import pprint as pp

    to_dict = lambda r: r.to_dict()

    print "Hulu:"
    h = HuluSearch()
    pp(h.autocomplete("d"))
    pp(map(to_dict, h.find("downton")))
    print

    print "Amazon:"
    a = AmazonSearch()
    pp(a.autocomplete("d"))
    pp(map(to_dict, a.find("downton")))
    print

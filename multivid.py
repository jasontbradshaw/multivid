#!/usr/bin/env python

import base64
import hashlib
import hmac
import oauth.oauth as oauth
import random
import string
import time
import urllib

import bs4
import requests

import arequests

class Result:
    """A basic search result."""

    MOVIE = "movie"
    EPISODE = "episode"
    SERIES = "series"

    def __init__(self, result_type):
        assert result_type in {Result.MOVIE, Result.EPISODE, Result.SERIES}
        self.type = result_type

        self.description = None
        self.rating_fraction = None
        self.url = None
        self.image_url = None

    def to_dict(self):
        # return a copy of our own dict
        return dict(self.__dict__)

class EpisodeResult(Result):
    """A television search result."""

    def __init__(self):
        self.series_title = None
        self.episode_title = None
        self.season_number = None
        self.episode_number = None
        self.duration_seconds = None

        Result.__init__(self, Result.EPISODE)

class MovieResult(Result):
    """A film search result."""

    def __init__(self):
        self.title = None
        self.duration_seconds = None

        Result.__init__(self, Result.MOVIE)

class SeriesResult(Result):
    """A TV series result."""

    # TODO: collect Amazon and Hulu episode results into series results

    def __init__(self):
        self.title = None
        self.season_count = None
        self.episode_count = None

        Result.__init__(self, Result.SERIES)

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
        # we make two requests, one for movies and one for TV shows. this is to
        # filter out useless clips and previews and the like.
        tv_params = {
            "page": 1,
            "type": "episode",
            "site": "hulu",
            "query": query
        }
        movie_params = {
            "page": 1,
            "type": "feature_film",
            "site": "hulu",
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
            r = EpisodeResult()

            r.series_title = unicode(video.show.find("name").string)
            r.episode_title = unicode(video.title.string)
            r.season_number = int(video.find("season-number").string)
            r.episode_number = int(video.find("episode-number").string)
            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.url = u"http://www.hulu.com/watch/" + video.id.string
            r.image_url = unicode(video.find("thumbnail-url").string)
            r.duration_seconds = int(float(video.duration.string))

            results.append(r)

        for video in movie_soup.videos("video", recursive=False):
            r = MovieResult()

            r.title = unicode(video.title.string)
            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.url = u"http://www.hulu.com/watch/" + video.id.string
            r.image_url = unicode(video.find("thumbnail-url").string)
            r.duration_seconds = int(float(video.duration.string))

            results.append(r)

        return results

    def autocomplete(self, query):
        params = {
            "query": query
        }

        response = requests.get(self.autocomplete_url, params=params)

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
        for param, value in sorted(params.items()):
            query_string_builder.append(param)
            query_string_builder.append("=")
            query_string_builder.append(urllib.quote(str(value), "~"))
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

            # NOTE: we might be able to emulate season searching by adding
            # 'season' as a search term and using the related results to get
            # episode information.

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

                # handle the different result types
                if "movie" in attrs.productgroup.string.lower():
                    r = MovieResult()
                    r.title = unicode(attrs.title.string)
                else:
                    r = EpisodeResult()

                    # prefix the title with the season name if possible
                    if item.relateditems is not None:
                        rel_attrs = item.relateditems.find("itemattributes")
                        if rel_attrs is not None:
                            # make sure it's a TV season
                            prod_group = rel_attrs.productgroup.string
                            if "season" in prod_group.lower():
                                # get the show title
                                r.series_title = unicode(rel_attrs.title.string)

                                # get the season number
                                r.season_number = int(rel_attrs.episodesequence.string)

                    r.episode_title = unicode(attrs.title.string)
                    r.episode_number = int(attrs.episodesequence.string)

                r.url = unicode(item.detailpageurl.string)
                r.image_url = unicode(item.largeimage.url.string)

                # occasionally, there isn't a running time
                mins = attrs.find("runningtime", units="minutes")
                if mins is not None:
                    minutes = int(mins.string)
                    r.duration_seconds = 60 * minutes

                # NOTE: description and rating_fraction don't come back in the
                # results, and would take a long time to scrape, so we don't.

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

        # the maximum number of starts a title may be rated
        self.rating_max = 5

        # our private netflix keys
        self.consumer_key = ""
        self.shared_secret = ""

        Search.__init__(self)

    @staticmethod
    def build_params(http_method, url, consumer_key, shared_secret, **params):
        """
        OAuth-encodes and signs the given parameters for some request, adding
        the nonce, timestamp, and other required parameters along the way.
        """
        # make sure the verb is supported
        assert http_method.lower() in {"get", "post", "put", "delete"}

        base_str_builder = []
        base_str_builder.append(http_method.upper())
        base_str_builder.append(urllib.quote(url, "~"))

        # add required params
        params["oauth_version"] = "1.0"
        params["oauth_consumer_key"] = consumer_key
        params["oauth_signature_method"] = "HMAC-SHA1"

        # generate a nonce and the timestamp
        abc = string.letters
        params["oauth_nonce"] = ''.join(random.choice(abc) for i in xrange(32))
        params["oauth_timestamp"] = str(int(time.time()))

        # build the parameter string (alphabetical)
        param_str_builder = []
        for param, value in sorted(params.items()):
            param_str_builder.append(param)
            param_str_builder.append("=")
            # must double-escape param values, once here and again later
            param_str_builder.append(urllib.quote(str(value), "~"))
            param_str_builder.append("&")
        param_str_builder.pop()

        # escape it separately and add it to the base string
        param_str = urllib.quote(''.join(param_str_builder), "~")
        base_str_builder.append(param_str)

        # the string we sign has unescaped ampersands separating its parts
        str_to_sign = "&".join(base_str_builder)

        # sign the string
        signer = hmac.new(shared_secret + "&", str_to_sign, hashlib.sha1)

        # add the signature to the original params and return them
        params["oauth_signature"] = base64.b64encode(signer.digest())
        return params

    def find(self, query):
        params = NetflixSearch.build_params(
            "GET", self.search_url, self.consumer_key, self.shared_secret,
            v=2.0, # use the newest API version (JSON support, filters, etc.)
            output="json", # we want JSON responses, not XML

            # don't get too many results at once
            max_results=25,

            # we only want instant streaming results
            filters="http://api.netflix.com/categories/title_formats/instant",

            # get all the data we care about as part of the single request
            expand="@title,@seasons,@episodes,@short_synopsis",

            term=query
        )

        response = requests.get(self.search_url, params=params)

        results = []
        for item in response.json["catalog"]:

            # figure out what kind of result we're dealing with
            if "movie" in item["id"]:
                r = MovieResult()
            elif "series" in item["id"]:
                r = SeriesResult()
                r.episode_count = item["episode_count"]
                r.season_count = item["season_count"]

            r.title = item["title"]["regular"]
            r.description = item["synopsis"]["short_synopsis"]
            r.rating_fraction = self.rating_max / float(item["average_rating"])
            r.url = item["web_page"]

            # pick the largest image size available
            largest_size = 0
            image_url = None
            for size_str, url in item["box_art"].items():
                size_num = int(size_str.replace("pix_w", ""))
                if size_num >= largest_size:
                    largest_size = size_num
                    image_url = url
            r.image_url = image_url

            # NOTE: no duration information comes back, so we don't fill it out.
            # this could be remedied with the bulk request API, if necessary.

            # NOTE: episodes aren't directly returned as part of the search,
            # only (seemingly) as part of a series. since series are much more
            # useful than individual episodes, we leave it alone.

            results.append(r)

        return results

    def autocomplete(self, query):
        params = {
            "oauth_consumer_key": self.consumer_key,
            "term": query
        }

        response = requests.get(self.autocomplete_url, params=params)
        soup = bs4.BeautifulSoup(response.text)

        results = []
        for item in soup("autocomplete_item"):
            title = unicode(item.title["short"])
            results.append(title.lower())

        return results

if __name__ == "__main__":
    from pprint import pprint as pp
    import sys

    to_dict = lambda r: r.to_dict()

    h = HuluSearch()
    a = AmazonSearch()
    n = NetflixSearch()

    # get the query from the first argument or from user input
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = raw_input("search: ")

    # get a shorter query to use for autocomplete
    ac_query = query[0:3]

    print "autocomplete results for '" + ac_query + "':"
    autocomplete_results = {}
    autocomplete_results["amazon"] = a.autocomplete(ac_query)
    autocomplete_results["hulu"] = h.autocomplete(ac_query)
    autocomplete_results["netflix"] = n.autocomplete(ac_query)

    pp(autocomplete_results)
    print

    print "search results for '" + query + "':"
    search_results = {}
    search_results["amazon"] = map(to_dict, a.find(query))
    search_results["hulu"] = map(to_dict, h.find(query))
    search_results["netflix"] = map(to_dict, n.find(query))

    pp(search_results)
    print

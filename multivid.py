import bs4
import requests
import arequests

class Result:
    """A search result."""

    def __init__(self):
        self.title = None
        self.description = None
        self.rating_fraction = None
        self.site_link = None
        self.direct_link = None
        self.thumbnail_link = None

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
        Get the list of strings suggested by the autocomplete search for some
        query, partial or otherwise. If no suggestions are found, or
        autocomplete is not supported, this should return an empty list.
        """

        # only requires implementation if autocomplete is supported
        if self.supports_autocomplete:
            raise NotImplemented("autocomplete must be implemented!")
        return []

class HuluSearch(Search):
    def __init__(self):
        # URLs we request data from
        self.search_url = "http://www.hulu.com/search"
        self.autocomplete_url = "http://www.hulu.com/search/suggest_json"

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
        movie_request = arequests.get(self.search_url, params=tv_params)

        # get both requests and parse their XML payloads
        tv_response, movie_response = arequests.map((tv_request, movie_request))

        tv_xml = bs4.BeautifulSoup(tv_response.text, "xml")
        movie_xml = bs4.BeautifulSoup(movie_response.text, "xml")

        print tv_xml, movie_xml

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
                return json[0]

        # default to returning no results
        return []

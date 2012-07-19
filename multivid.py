import bs4
import requests
import arequests

class SearchResult:
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
        for video in tv_soup.find("videos").find_all("video"):
            r = SearchResult()

            # title it show title: episode title for tv shows
            r.title = unicode(video.show.find("name").string)
            r.title += ": " + unicode(video.title.string)

            r.description = unicode(video.description.string)
            r.rating_fraction = float(video.rating.string) / self.rating_max
            r.video_url = u"http://www.hulu.com/watch/" + video.id.string
            r.thumbnail_url = unicode(video.find("thumbnail-url").string)

            results.append(r)

        for video in movie_soup.find("videos").find_all("video"):
            r = SearchResult()

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
        self.autocomplete_url = "http://completion.amazon.com/search/complete"

        # the maximum rating a video may receive
        self.rating_max = 5

        Search.__init__(self, supports_autocomplete=True)

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

    h = HuluSearch()
    pp(h.autocomplete("c"))
    pp(map(lambda x: x.to_dict(), h.find("c")))

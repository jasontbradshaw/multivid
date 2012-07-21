import json
import os

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

    def __init__(self, config_file="multivid.conf"):
        # set the config file if one is needed/was specified
        self.config_file = None
        if config_file is not None:
            self.config_file = os.path.abspath(config_file)

        # where the loaded config file is cached once read
        self.__config = None

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

    @property
    def config(self):
        """Return the JSON config file contents."""

        # return the cached value if it exists
        if self.__config is not None:
            return self.__config

        # only load the file if one was specified and the file exists
        config = None
        if self.config_file is not None:
            # raise an error if there's no such config file
            if not os.path.exists(self.config_file):
                raise ValueError("config file could not be located: " +
                        self.config_file)

            # load and parse the config file if it does exist
            with open(self.config_file, 'r') as cf:
                try:
                    config = json.load(cf)
                except ValueError:
                    # return None if the config failed to parse
                    config = None
        else:
            # if there was no config specified, return an empty config
            config = {}

        # cache the loaded config file before returning it
        self.__config = config

        return config

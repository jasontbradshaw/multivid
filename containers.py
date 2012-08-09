import json

class Suggestion:
    """An autocomplete suggestion."""
    def __init__(self, provider=None):
        self.provider = provider
        self.suggestion = None

    def to_dict(self):
        return dict(self.__dict__)

class Result:
    """A basic search result."""

    # canonical types of results
    MOVIE = u"movie"
    EPISODE = u"episode"
    SERIES = u"series"

    def __init__(self, result_type, provider=None):
        assert result_type in {Result.MOVIE, Result.EPISODE, Result.SERIES}
        self.type = result_type

        # who the search result came from
        self.provider = provider

        self.title = None
        self.description = None
        self.rating_fraction = None
        self.url = None
        self.image_url = None

    def to_dict(self):
        return dict(self.__dict__)

class EpisodeResult(Result):
    """A television search result."""

    def __init__(self, provider):
        self.series_title = None
        self.season_number = None
        self.episode_number = None
        self.duration_seconds = None

        Result.__init__(self, Result.EPISODE, provider=provider)

class MovieResult(Result):
    """A film search result."""

    def __init__(self, provider):
        self.duration_seconds = None

        Result.__init__(self, Result.MOVIE, provider=provider)

class SeriesResult(Result):
    """A TV series result."""

    # TODO: generate Amazon series results as well as episode results

    def __init__(self, provider):
        self.season_count = None
        self.episode_count = None

        Result.__init__(self, Result.SERIES, provider=provider)

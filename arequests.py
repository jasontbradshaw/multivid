"""
arequests
~~~~~~~~~

This module contains an asynchronous replica of ``requests.api``, powered
by Python's built-in threading module. All API methods return a ``Request``
instance (as opposed to ``Response``). A list of requests can be sent with
``map()``.
"""

import thread_pool

from requests import api

__all__ = (
    'map', 'imap',
    'get', 'options', 'head', 'post', 'put', 'patch', 'delete', 'request'
)

def patched(f):
    """Patches a given API function to not send."""

    def wrapped(*args, **kwargs):

        kwargs['return_response'] = False
        kwargs['prefetch'] = True

        config = kwargs.get('config', {})
        config.update(safe_mode=True)

        kwargs['config'] = config

        return f(*args, **kwargs)

    return wrapped

# patched requests.api functions.
get = patched(api.get)
options = patched(api.options)
head = patched(api.head)
post = patched(api.post)
put = patched(api.put)
patch = patched(api.patch)
delete = patched(api.delete)
request = patched(api.request)

def send(request, prefetch):
    """Send a request and return its response."""
    request.send(prefetch)
    return request.response

def map(requests, prefetch=True, size=None):
    """Concurrently converts a list of Requests to Responses.

    :param requests: a collection of Request objects.
    :param prefetch: If False, the content will not be downloaded immediately.
    :param size: Specifies the number of requests to make at a time. If None, no throttling occurs.
    """

    # create pool of specified size or default to one thread per request
    pool = thread_pool.Pool(size if size is not None else len(requests))
    return pool.map(lambda r: send(r, prefetch), requests)

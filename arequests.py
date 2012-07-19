"""
arequests
~~~~~~~~~

This module contains an asynchronous replica of ``requests.api``, powered
by Python's built-in threading module. All API methods return a ``Request``
instance (as opposed to ``Response``). A list of requests can be sent with
``map()``.
"""

import threading
import Queue as queue

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

class Pool:
    """A basic thread pool that supports only a map method."""

    def __init__(self, size=4):
        self.size = size

    @staticmethod
    def worker(target, work_queue, result_queue):
        """
        Worker thread that consumes from and produces to two Queues. Each item
        in the work queue is assumed to be a tuple of (index, item). When the
        work is processed, it is put into the result queue with the same index
        and item. This ensures that ordering is preserved when work is done
        asynchronously if a PriorityQueue is used. If ordering isn't desired,
        simply use normal queues with fake indexes.
        """

        try:
            index, item = work_queue.get_nowait()
            result_queue.put_nowait((index, target(item)))
            work_queue.task_done()
        except queue.Empty:
            # stop working when all the work has been processed
            return
        except queue.Full:
            # we should NEVER manage to do more work than was expected
            assert False

    def map(self, target, sequence):
        """
        Map a function onto a sequence in parallel. Blocks until results are
        ready, and returns them in the order of the original sequence.
        """

        work_queue = queue.Queue(len(sequence))
        result_queue = queue.PriorityQueue(len(sequence))

        # add all the original items to the work queue with their index
        for index_item_tup in enumerate(sequence):
            work_queue.put_nowait(index_item_tup)

        assert work_queue.full()

        # start a number of worker threads equal to our size
        threads = []
        args = (target, work_queue, result_queue)
        for i in xrange(self.size):
            thread = threading.Thread(target=Pool.worker, args=args)
            threads.append(thread)
            thread.start()

        # wait until all threads have finished
        for thread in threads:
            thread.join()

        # wait until all work has been processed
        work_queue.join()

        assert work_queue.empty()
        assert result_queue.full()

        # return the results in the original order from the result queue
        results = []
        while not result_queue.empty():
            index, result = result_queue.get_nowait()
            results.append(result)

        assert result_queue.empty()
        return results

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
    pool = Pool(size if size is not None else len(requests))
    return pool.map(lambda r: send(r, prefetch), requests)

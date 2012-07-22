import threading
import Queue as queue

def worker(function, work_queue, result_queue):
    """
    Worker thread that consumes from and produces to two Queues. Each item
    in the work queue is assumed to be a tuple of (index, item). When the
    work is processed, it is put into the result queue with the same index
    and item. This ensures that ordering is preserved when work is done
    asynchronously if a PriorityQueue is used. If ordering isn't desired,
    simply use normal queues with fake indexes. The work queue is assumed to be
    full at the time the worker thread is started.
    """

    # keep getting work until there's no more to be had
    while 1:
        try:
            index, item = work_queue.get_nowait()
            result_queue.put_nowait((index, function(item)))
            work_queue.task_done()
        except queue.Empty:
            # stop working when all the work has been processed
            return
        except queue.Full:
            # we should NEVER manage to do more work than was expected
            assert False

def map(function, sequence, num_threads=2):
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

    # start the worker threads
    threads = []
    args = (function, work_queue, result_queue)
    for i in xrange(num_threads):
        thread = threading.Thread(target=worker, args=args)
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

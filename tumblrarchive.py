from HTMLParser import HTMLParser
import pytumblr
import Queue
import re
import sys
import threading
import time
import traceback
import urllib


class Worker(object):
    def __init__(self, name, queue):
        self.name = name
        self.thread = threading.Thread(target=self.run)
        self.queue = queue
        self.running = True
        self.idle = True
        self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
            self.idle = True

    def run(self):
        while self.running:
            try:
                job = self.queue.get(True, 3)
                self.idle = False
                job.execute()
            except Queue.Empty:
                self.idle = True


class Job(object):
    def __init__(self):
        self.log = []

    def execute_inner(self):
        pass

    def execute(self):
        try:
            self.execute_inner()
        except Exception as e:
            self.log += traceback.format_exception(*sys.exc_info())

        if self.log:
            statusqueue.put(self.log)


class FetchPostInfoJob(Job):
    limit = 20

    def __init__(self, url, post_offset):
        super(FetchPostInfoJob, self).__init__()
        self.url = url
        self.post_offset = post_offset

    def execute_inner(self):
        response = tumblrclient.posts(self.url, offset=self.post_offset, limit=self.limit)
        if response[u"posts"] > self.post_offset:
            workqueue.put(FetchPostInfoJob(self.url, self.post_offset + self.limit))

        for post in response[u"posts"]:
            self.log.append(str(post))


def workers_running(workers):
    return any([not w.idle for w in workers])


def run_jobs(queue, workers):
    while not queue.empty() and workers_running(workers):
        print "loop"
        try:
            print '\n'.join(statusqueue.get(False, 1000))
        except Queue.Empty:
            pass

def shutdownworkers():
    for i, w in enumerate(workers):
        print "stopping worker", i
        w.stop()


workqueue = Queue.Queue()
statusqueue = Queue.Queue()
workers = [Worker('Worker %s' % i, workqueue) for i in xrange(5)]

authlines = open("authinfo.txt").readlines()[0:4]
tumblrclient = pytumblr.TumblrRestClient(*authlines)

workqueue.put(FetchPostInfoJob(sys.argv[1], 0))

try:
    while True:
        run_jobs(workqueue, workers)
        while not statusqueue.empty():
            print '\n'.join(statusqueue.get())

except KeyboardInterrupt:
    pass

finally:
    shutdownworkers()

    while not statusqueue.empty():
        print '\n'.join(statusqueue.get())

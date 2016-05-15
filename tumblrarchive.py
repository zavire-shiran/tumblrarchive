from datetime import datetime
from datetime import timedelta
from HTMLParser import HTMLParser
import pytumblr
import Queue
import re
import sys
import threading
import time
import traceback
import urllib
import os
import json
import errno


class Worker(object):
    def __init__(self, name, queue):
        self.name = name
        self.thread = threading.Thread(target=self.run)
        self.queue = queue
        self.running = True
        self.lastactive = datetime.now()
        self.thread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
            self.lastactive = datetime.min

    def run(self):
        while self.running:
            try:
                job = self.queue.get(True, 3)
                self.lastactive = datetime.now()
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


class StorePost(Job):
    def __init__(self, url, post):
        super(StorePost, self).__init__()
        self.url = url
        self.post = post

    def execute_inner(self):
        postdate = datetime.strptime(self.post[u"date"], "%Y-%m-%d %H:%M:%S %Z")
        postdirectory = os.path.join(self.url, str(postdate.year), "{0}-{1}".format(postdate.month, postdate.day), str(self.post[u"id"]))
        self.log.append("{0} {1} {2} {3}".format(self.url, self.post[u"id"], self.post[u"type"], postdirectory))

        if self.post["type"] == "photo":
            for photo in self.post["photos"]:
                workqueue.put(FetchImageJob(photo["original_size"]["url"], postdirectory))

        try:
            os.makedirs(postdirectory)
        except os.error as e:
            if e.errno != errno.EEXIST:
                raise
        with open(os.path.join(postdirectory, "json"), "w") as f:
            f.write(json.dumps(self.post))


class FetchPostInfoJob(Job):
    limit = 20

    def __init__(self, url, post_offset):
        super(FetchPostInfoJob, self).__init__()
        self.url = url
        self.post_offset = post_offset

    def execute_inner(self):
        response = tumblrclient.posts(self.url, offset=self.post_offset, limit=self.limit)
        if response[u"blog"][u"posts"] > self.post_offset:
            workqueue.put(FetchPostInfoJob(self.url, self.post_offset + self.limit))

        for post in response[u"posts"]:
            workqueue.put(StorePost(self.url, post))


class FetchImageJob(Job):
    def __init__(self, image_url, savepath):
        super(FetchImageJob, self).__init__()
        self.image_url = image_url
        self.savepath = savepath

    def execute_inner(self):
        self.log.append("Fetching {0} to {1}".format(self.image_url, self.savepath))
        image = urllib.urlopen(self.image_url).read()
        filename = self.image_url.split("/")[-1]
        open(os.path.join(self.savepath, filename), "w").write(image)


def workers_running(workers, max_time_since_active):
    now = datetime.now()
    return any([(now - w.lastactive) < max_time_since_active for w in workers])


def run_jobs(queue, workers):
    while not queue.empty() or workers_running(workers, timedelta(seconds=30)):
        try:
            print '\n'.join(statusqueue.get(False, 1000))
        except Queue.Empty:
            pass

def shutdownworkers():
    for w in workers:
        w.running = False
    for i,w in enumerate(workers):
        print "stopping", i
        w.thread.join()

workqueue = Queue.Queue()
statusqueue = Queue.Queue()
workers = [Worker('Worker %s' % i, workqueue) for i in xrange(5)]

authlines = open("authinfo.txt").readlines()[0:4]
tumblrclient = pytumblr.TumblrRestClient(*authlines)

workqueue.put(FetchPostInfoJob(sys.argv[1], 0))

try:
    run_jobs(workqueue, workers)
    while not statusqueue.empty():
        print '\n'.join(statusqueue.get())

except KeyboardInterrupt:
    pass

finally:
    shutdownworkers()

    while not statusqueue.empty():
        print '\n'.join(statusqueue.get())

#! /usr/bin/python
# -*- coding: utf-8 -*-

import Queue
import time
import threading

from collections import OrderedDict

class MessagePriority:
    Critical = 0
    High = 1
    Normal = 2
    Low = 3

class Event: pass

class Message(object):
    def __init__(self, event, data = None):
        self._event = event
        self._data = data
        self._result = Queue.Queue()

    def _repr__(self):
        print 'Message (Event = {})'.format(self._event.__class__.__name__ )

    def getData(self):
        return self._data

    def getEvent(self):
        return self._event

    def setResult(self, result):
        self._result.put(result)

    def getResult(self):
        return self._result.get()

class MessageQueue(object):
    def __init__(self):
        self._sortedQueues = {}
        self._queue = Queue.Queue()
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

    def _empty(self):
        return len(self._sortedQueues) == 0

    def _get(self):
        priority, queue = self._sortedQueues.items()[0]
        data = queue.get(block = False)
        if queue.empty():
            del self._sortedQueues[priority]
        return data

    def empty(self):
        with self._lock:
            return self._empty()

    def queue(self, message, priority, _block = True):
        with self._cv:
            queues = self._sortedQueues
            if priority in queues:
                queue = queues[priority]
                queue.put(message, block = _block)
            else:
                queue = Queue.Queue()
                queues[priority] = queue
                self._sortedQueues = OrderedDict(sorted(queues.items(), key = lambda t : t[0]))
                queue.put(message, block = _block)

            self._cv.notifyAll()

    def dequeue(self, _block = True):
        with self._cv:
            while self._empty():
                if not _block: raise Queue.Empty()
                self._cv.wait()

            return self._get()

    def drain(self):
        with self._lock:
            while not self._empty():
                message = self._get()
                message.setResult(None)

class Connection(object):
    def __init__(self, queue):
        self._queue = queue

    def sendMessage(self, message, priority):
        self._queue.queue(message, priority)

    def sendMessageForResult(self, message, priority):
        self._queue.queue(message, priority)
        return message.getResult()

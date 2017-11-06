#! /usr/bin/python
# -*- coding: utf-8 -*-

import threading

class ServiceThread(threading.Thread):
    def __init__(self, serviceName = None):
        super(ServiceThread, self).__init__(name = serviceName)
        self._started = threading.Event()
        self._started.clear()

    def start(self):
        self._started.set()
        threading.Thread.start(self)

    def stop(self):
        self._started.clear()

    def run(self):
        self.onStart()

        while self._started.is_set():
            self.loop()

        self.onExit()

    def loop(self):
        pass

    def onStart(self):
        pass

    def onStop(self):
        pass

    def onExit(self):
        pass
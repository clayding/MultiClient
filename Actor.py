#! /usr/bin/python
# -*- coding: utf-8 -*-

import Queue
import threading
from ServiceThread import ServiceThread
from MessageQueue import MessageQueue, Connection, Event, MessagePriority, Message


class ActorEvent(Event): pass


class ActorReset(ActorEvent): pass


class ActorReady(ActorEvent): pass


class ActorConnect(ActorEvent): pass


class ActorDisconnect(ActorEvent): pass


class ActorEventHandled(ActorEvent): pass


class ActorProxy(object):
    def __init__(self, actor, connection):
        self._actor = actor
        self._connection = connection

    def stop(self):
        self._actor.stop()

    def reset(self):
        # self._actor._reset()
        self.ask(Message(ActorReset), MessagePriority.Critical)

    def ready(self):
        # self._actor._ready()
        self.ask(Message(ActorReady), MessagePriority.Critical)

    def connect(self, actorProxy):
        # self._connection.sendMessage(Message(ActorConnect, actorProxy._getActor()),
        # MessagePriority.Critical)
        self._actor._connectTo(actorProxy._getActor())

    def disconnect(self, actorProxy):
        # self._connection.sendMessage(Message(ActorDisconnect, actorProxy._getActor()),
        #                             MessagePriority.Critical)
        self._actor._disconnectedFrom(actorProxy._getActor())

    def tell(self, message, priority=MessagePriority.Normal):
        self._connection.sendMessage(message, priority)

    def ask(self, message, priority=MessagePriority.Normal):
        return self._connection.sendMessageForResult(message, priority)

    def _getActor(self):
        return self._actor


class Actor(ServiceThread):
    def __init__(self, name=None):
        super(Actor, self).__init__(name)
        self._messageQueue = MessageQueue()

        self._connections = {}
        self._connectionsLock = threading.RLock()

    @classmethod
    def start(cls, *args, **kwargs):
        actor = cls(*args, **kwargs)
        actor._start()
        return actor

    def _start(self):
        super(Actor, self).start()

    def _reset(self):
        self._messageQueue.drain()
        self.onReset()

    def _ready(self):
        self.onReady()

    def _connectTo(self, actor):
        with self._connectionsLock:
            if actor not in self._connections:
                # print '{} connected to {}'.format(type(self), type(actor))
                self._connections[actor] = actor.createConnection()

    def _disconnectedFrom(self, actor):
        with self._connectionsLock:
            if actor in self._connections:
                del self._connections[actor]

    def createConnection(self):
        return Connection(self._messageQueue)

    def proxy(self):
        return ActorProxy(self, Connection(self._messageQueue))

    def sendMessage(self, actor, message, priority=MessagePriority.Normal):
        with self._connectionsLock:
            if actor in self._connections:
                connection = self._connections[actor]
                connection.sendMessage(message, priority)

    def broadcast(self, message, priority=MessagePriority.Normal, target=None):
        with self._connectionsLock:
            for actor, connection in list(self._connections.items()):
                if target is None or target == actor.__class__:
                    connection.sendMessage(message, priority)

    def loop(self):
        # handle pending messages
        if not self._messageQueue.empty():
            message = self._messageQueue.dequeue()
            self._handleMessage(message)
        # allow subclasses to implement their own actions
        self.act()

    def _handleMessage(self, message):
        # check whether it's actor message
        event = message.getEvent()
        if issubclass(event, ActorEvent):
            result = self._handleActorEvent(event, message.getData())
        else:
            result = self.handleMessage(message)
        message.setResult(result)

    def _handleActorEvent(self, event, data):
        if event == ActorReset:
            self._reset()
        elif event == ActorReady:
            self._ready()

    def handleMessage(self, message):
        pass

    def act(self):
        pass

    def onReset(self):
        pass

    def onReady(self):
        pass

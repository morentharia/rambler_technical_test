# -*- encoding: utf-8 -*-
import signal
import weakref
import re
from collections import deque
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado import gen
from tornado.tcpserver import TCPServer
from tornado.options import define, options

import logging
log = logging.getLogger(__name__)

define('port', default=23, help='chat port', type=int)

HISTORY_LENGTH = 10


class Cached(type):
    def __init__(self, *args, **kwargs):
        super(Cached, self).__init__(*args, **kwargs)
        self.__cache = weakref.WeakValueDictionary()

    def __call__(self, *args):
        if args in self.__cache:
            return self.__cache[args]
        else:
            obj = super(Cached, self).__call__(*args)
            self.__cache[args] = obj
            return obj


class Room(object):
    __metaclass__ = Cached

    def __init__(self, name):
        self._name = name
        self._users = weakref.WeakSet()
        self._history = deque(maxlen=HISTORY_LENGTH)
        super(Room, self).__init__()

    @gen.coroutine
    def write(self, message):
        self._history.append(message)
        for user in self.users:
            user.write(message)

    @property
    def users(self):
        return self._users

    def add_user(self, user):
        assert isinstance(user, User)
        if self._history:
            user.write('*** {} history\n'.format(self))
        for message in self._history:
            user.write(message)
        self._users.add(user)

    def remove_user(self, user):
        assert isinstance(user, User)
        if user in self._users:
            self._users.remove(user)

    def is_empty(self):
        return not bool(self.users)

    def __str__(self):
        return '#{}'.format(self._name)


class User(object):
    def __init__(self, stream, nick=None):
        self._stream = stream
        self._nick = nick if nick else 'anonymous'
        self._rooms = weakref.WeakSet()
        super(User, self).__init__()

    @gen.coroutine
    def write(self, message):
        if not self._stream.closed():
            yield self._stream.write(message)

    @property
    def nick(self):
        return self._nick

    @nick.setter
    def nick(self, val):
        self._nick = val

    @property
    def rooms(self):
        return self._rooms

    @property
    def stream(self):
        return self._stream

    def add_room(self, room):
        assert isinstance(room, Room)
        self._rooms.add(room)

    def remove_room(self, room):
        assert isinstance(room, Room)
        self._rooms -= set([room])

    def __str__(self):
        return '{}'.format(self._nick)


class Server(TCPServer):
    pattern = re.compile(r'^\W*?(LOGIN|JOIN|LEFT)\W+(\w+)', re.IGNORECASE)

    __all_rooms = set()
    __all_users = set()

    @gen.coroutine
    def handle_stream(self, stream, address):
        user = User(stream)
        self.__all_users.add(user)

        while True:
            try:
                message = yield stream.read_until('\n')
                match = self.pattern.match(message)
                if match:
                    cmd, param = match.groups()
                    func = getattr(self, 'handle_' + cmd.lower())
                    if func and callable(func):
                        yield func(user, param)
                    else:
                        raise NotImplementedError
                else:
                    yield self.send(user, message)

            except StreamClosedError:
                log.info("%s disconnect.", user)
                break

        yield self.broadcast("*** User {} leave chat".format(user))
        for room in user.rooms:
            yield self.handle_left(user, room)
        self.__all_users.remove(user)

    @gen.coroutine
    def handle_join(self, user, room_name):
        room = Room(room_name)
        self.__all_rooms.add(room)
        user.add_room(room)
        room.add_user(user)
        yield self.broadcast("User {} joined room {}".format(user, room))

    @gen.coroutine
    def handle_left(self, user, room_name):
        room = Room(room_name)
        user.remove_room(room)
        room.remove_user(user)
        if room.is_empty():
            self.__all_rooms -= set([room])
        yield self.broadcast("User {} lefted room {}".format(user, room))

    @gen.coroutine
    def handle_login(self, user, nick):
        yield self.broadcast("User change nick {} --> {}".format(user.nick,
                                                                 nick))
        user.nick = nick

    @gen.coroutine
    def send(self, user, message):
        for room in user.rooms:
            yield room.write(
                "{}:{}> {}".format(room, user.nick, message)
            )

    @gen.coroutine
    def broadcast(self, message):
        for user in self.__all_users:
            yield user.write("*** {}\n".format(message))

    @classmethod
    def shutdown(cls):
        for user in cls.__all_users:
            user.write("*** have a nice day ***\n")
            if not user.stream.closed():
                user.stream.close()

if __name__ == "__main__":
    options.parse_command_line()

    server = Server()
    server.listen(options.port)

    def shutdown(sig, frame):
        server.shutdown()
        IOLoop.instance().stop()

    signal.signal(signal.SIGINT, shutdown)
    ioloop = IOLoop.instance().start()

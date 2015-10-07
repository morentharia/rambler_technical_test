# -*- encoding: utf-8 -*-
import signal
import weakref
import re
from tornado.ioloop import IOLoop
from tornado.iostream import StreamClosedError
from tornado import gen
from tornado.tcpserver import TCPServer
from tornado.options import define, options

import logging
log = logging.getLogger(__name__)

define('port', default=None, help='chat port', type=int)


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
        super(Room, self).__init__()

    @gen.coroutine
    def write(self, message):
        for user in self.users:
            user.write(message)

    @property
    def users(self):
        return self._users

    def add_user(self, user):
        assert isinstance(user, User)
        self._users.add(user)

    def remove_user(self, user):
        assert isinstance(user, User)
        if user in self._users:
            self._users.remove(user)

    def is_empty(self):
        return not bool(self.users)

    def __repr__(self):
        return 'Room("{}") {} {}'.format(self._name, list(self.users))

    def __str__(self):
        return '{}'.format(self._name)

    # def __del__(self):
    #     print self, id(self), 'Die'
    #     pass


class User(object):
    def __init__(self, stream, nick=None):
        self._stream = stream
        self._nick = nick if nick else 'anonymous'

        self._rooms = weakref.WeakSet()
        super(User, self).__init__()

    @gen.coroutine
    def write(self, message):
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

    def add_room(self, room):
        assert isinstance(room, Room)
        self._rooms.add(room)

    def remove_room(self, room):
        assert isinstance(room, Room)
        self._rooms -= set([room])

    def __repr__(self):
        return 'User("{}")'.format(self._nick)


class Server(TCPServer):
    pattern = re.compile(r'^\W*?(LOGIN|JOIN|LEFT)\W+(\w+)', re.IGNORECASE)

    __all_rooms = set()
    __all_users = set()

    @gen.coroutine
    def handle_stream(self, stream, address):
        log.info("New connection. %s", stream)

        user = User(stream)
        self.__all_users.add(user)
        print 'add user', list(self.__all_users)

        while True:
            try:
                message = yield stream.read_until('\n')
                match = self.pattern.match(message)
                if match:
                    cmd, param = match.groups()
                    func = getattr(self, cmd.lower())
                    if func and callable(func):
                        func(user, param)
                    else:
                        raise NotImplementedError
                else:
                    yield self.broadcast(user, message)

            except StreamClosedError:
                log.info("%s left.", user)
                break

        print 'remove user', list(self.__all_users)
        self.__all_users.remove(user)
        for room in user.rooms:
            self.left(user, room)

    @gen.coroutine
    def broadcast(self, user, message):
        for room in user.rooms:
            yield room.write(
                "{}:{}> {}".format(room, user.nick, message)
            )

    def join(self, user, room_name):
        room = Room(room_name)
        self.__all_rooms.add(room)
        user.add_room(room)
        room.add_user(user)

    def left(self, user, room_name):
        room = Room(room_name)
        user.remove_room(room)
        room.remove_user(user)
        if room.is_empty():
            self.__all_rooms -= set([room])

    def login(self, user, nick):
        user.nick = nick


    # @classmethod
    # def shutdown(self):
    #     for client in Server.__clients:
    #         if not client.closed():
    #             client.close()
    #         Server.__clients.remove(client)

if __name__ == "__main__":
    server = Server()
    options.parse_command_line()
    port = options.port or int(raw_input("enter port (8080): ") or 8080)

    ioloop = IOLoop.instance()
    server.listen(port)

    def shutdown():
        # server.shutdown()
        ioloop.stop()

    signal.signal(signal.SIGINT, lambda sig, frame: shutdown())

    ioloop.start()

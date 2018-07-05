#!/usr/bin/env python
import os.path, logging
from LogBuffer import LogBuffer


class LogFileHandler():
    def __init__(self, path, filters):
        self.reset()
        self.path = path
        self.position = 0
        self.object = None
        self.buffer = LogBuffer(filters)
        self.open()
        self.tail()

    def reset(self):
        self.path = None
        self.object = None
        self.position = 0

    def is_open(self):
        return os.path.isfile(self.path) and self.object is not None

    def open(self):
        self.close()
        if os.path.isfile(self.path):
            logging.debug("Action: Open. File {0}".format(self.path))
            self.object = open(self.path, 'r')

    def close(self):
        if self.is_open():
            logging.debug("Action: Close. File {0}".format(self.path))
            self.object.close()
            self.object = None

    def tail(self):
        if self.is_open():
            self.object.seek(self.position)
            data = self.object.read()
            self.position = self.object.tell()
            if data:
                logging.debug("Action: Tail {0}: {1}".format(self.path, data))
                self.buffer.push(data)

    def get_buffer(self):
        return self.buffer



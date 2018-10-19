#!/usr/bin/env python
import os, re, json, logging
from LogFilter import LogFilter, LogFilterSet, LogSkipException


class LogBuffer():

    def __init__(self, filters):
        self.temp = ''
        self.filters = LogFilterSet(filters)
        self.stack = []

    def append(self, string):
        try:
            self.stack.append(self.filters.apply(string))
        except LogSkipException as skip:
            logging.debug(str(skip))

    def push(self, string):
        self.temp += string
        lines = self.temp.splitlines(True)
        while lines:
            line = lines.pop(0)
            if not line.endswith(os.linesep): 
                self.temp = line
                break
            self.temp = ''
            self.append(line.rstrip())

    def empty(self):
        return not self.stack

    def pop(self):
        if self.stack:
            return self.stack.pop(0)


#!/usr/bin/env python
import os, re, json
from LogFilter import LogFilter, LogFilterSet
            

class LogBuffer():

    def __init__(self, filters):
        self.temp = ''
        self.filters = LogFilterSet(filters)
        self.stack = []

    def append(self, string):
        #self.stack.append(self.filters.apply(string))
        print self.filters.apply(string)

    def push(self, string):
        self.temp += string
        lines = self.temp.splitlines(True)
        while lines:
            line = lines.pop(0)
            if not line.endswith(os.linesep): 
                self.temp = line
                break
            self.temp = ''
            self.append(line)

    def pop(self):
        if self.stack:
            self.stack.pop(0)
            


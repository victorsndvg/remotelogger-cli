#!/usr/bin/env python
import os, re, json

class LogFilter():

    def __init__(self, pattern, verbosity=None, severity=None, progress=None):
        self.pattern   = pattern
        self.regex     = re.compile(pattern)
        self.verbosity = verbosity # None/0-5
        self.severity  = severity  # None/0-5
        self.progress  = progress  # None/0-100%

    def match(self, string):
        return self.regex.match(string)

    def to_json(self, string):
        return json.dumps({ 'string': string, 
                            'verbosity': self.verbosity,
                            'severity': self.severity,
                            'progress': self.progress
                         })


class DummyLogFilter(LogFilter):

    def __init__(self, pattern):
        self.pattern   = pattern
        self.regex     = None
        self.verbosity = None
        self.severity  = None
        self.progress  = None

    def match(self, string):
        return True


class LogFilterSet():
    def __init__(self, filters):
        self.filters = filters
        self.filters.append(DummyLogFilter(pattern="*"))

    def apply(self, string):
        for filter in self.filters:
            if filter.match(string): return filter.to_json(string)

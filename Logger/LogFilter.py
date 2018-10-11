import os, re, json

class LogFilter():

    def __init__(self, attributes):
        self.pattern = attributes.pop('pattern')
        self.attributes = attributes
        self.regex      = re.compile(self.pattern)
        print(self.attributes)
        print(self.to_json('blah'))

    def match(self, string):
        return self.regex.match(string)

    def to_json(self, string):
        tmp = {'string':string}
        tmp.update(self.attributes)
        return json.dumps(tmp)


class DummyLogFilter(LogFilter):

    def __init__(self, pattern):
        self.attributes = {}

    def match(self, string):
        return True


class LogFilterSet():
    def __init__(self, filters):
        self.filters = filters
        self.filters.append(DummyLogFilter(pattern="*"))

    def apply(self, string):
        for filter in self.filters:
            if filter.match(string): return filter.to_json(string)

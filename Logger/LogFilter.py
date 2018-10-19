import os, re, json

class LogSkipException(Exception):

    def __init__(self, pattern, message):
        self.expression = pattern
        self.message = message
        super(Exception, self).__init__('[SKIP] pattern: "'+str(pattern)+'", string: "'+message+'"')


class LogFilter():

    def __init__(self, attributes):
        self.pattern    = attributes.pop('pattern')
        self.regex      = re.compile(self.pattern)
        self.action     = getattr(self.regex, attributes.pop('action', 'match'), self.regex.match)
        self.serialize  = self.skip if attributes.pop('ignore', False) else self.to_json
        self.attributes = attributes

    def skip(self, string):
        raise LogSkipException(self.pattern, string)

    def apply(self, string):
        return self.action(string)

    def to_json(self, string):
        tmp = {'string':string}
        tmp.update(self.attributes)
        return json.dumps(tmp)


class DummyLogFilter(LogFilter):

    def __init__(self, pattern):
        self.attributes = {}
        self.serialize     = self.to_json

    def apply(self, string):
        return True


class LogFilterSet():
    def __init__(self, filters):
        self.filters = filters or []
        self.filters.append(DummyLogFilter(pattern="*"))

    def apply(self, string):
        for filter in self.filters:
            if filter.apply(string):
                return filter.serialize(string) 


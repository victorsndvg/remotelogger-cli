#!/usr/bin/env python
import os.path, logging
from LogFileHandler import LogFileHandler
from watchdog.events import PatternMatchingEventHandler



class LogEventHandler(PatternMatchingEventHandler):
    def __init__(self, path, filters, patterns=None, ignore_patterns=None, ignore_directories=False, case_sensitive=False):
        self._patterns           = patterns
        self._ignore_patterns    = ignore_patterns
        self._ignore_directories = ignore_directories
        self._case_sensitive     = case_sensitive
        self.file                = LogFileHandler(path, filters)

        super(LogEventHandler, self).__init__(  patterns=self._patterns, 
                                                ignore_patterns=self._ignore_patterns,
                                                ignore_directories=self._ignore_directories, 
                                                case_sensitive=self._case_sensitive )

    def on_moved(self, event):
        super(LogEventHandler, self).on_moved(event)
        logging.debug("Event: move. Origin: {0} Destiny: {1}".format(event.src_path, event.dest_path))
        self.file.close()
        self.stop()
        super(LogEventHandler, self).__init__( patterns=[event.dest_path],
                                          ignore_patterns=self._ignore_patterns,
                                          ignore_directories=self._ignore_directories,
                                          case_sensitive=self._case_sensitive)
        self.file.path = event.dest_path
        self.file.open()
        self.start(dir=os.path.split(event.dest_path)[0], recursive=False)

    def on_created(self, event):
        super(LogEventHandler, self).on_created(event)
        logging.debug("Event: create. File: {0}".format(event.src_path))
        if not self.file.is_open():
            self.file.open()
        
    def on_deleted(self, event):
        super(LogEventHandler, self).on_deleted(event)
        logging.debug("Event: delete. File: {0}".format(event.src_path))
        self.file.close()

    def on_modified(self, event):
        super(LogEventHandler, self).on_modified(event)
        logging.debug("Event: modify. File: {0}".format(event.src_path))
        if(self.file.is_open()):
            self.file.tail()




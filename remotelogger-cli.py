#!/usr/bin/env python
import sys, os, time, logging
from Logger.LogFileHandler import LogFileHandler
from Logger.LogEventHandler import LogEventHandler
from Logger.LogFileHandler import LogFileHandler
from Logger.LogFilter import LogFilter, LogFilterSet
from watchdog.observers import Observer
import argparse
import yaml



def log(path, filters, observer):
    dir = os.path.split(path)[0]
    logging.info("File: {path}".format(path=path))

    logeventhandler = LogEventHandler(  path=path,
                                        filters=filters,
                                        patterns=[path],
                                        ignore_patterns=[],
                                        ignore_directories=True,
                                        case_sensitive=True)

    observer.schedule(logeventhandler, path=dir, recursive=False)


def parse():
    parser = argparse.ArgumentParser("Send your logs to remote endpoints")
    parser.add_argument('-c', '--config', dest='config', type=str, help='Path to config file', required=True)
    parser.print_help()
    args = parser.parse_args()
    return args.config


if __name__ == "__main__":
    #event_handler = MyHandler()
    logging.basicConfig(level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')
    config_file = parse()


    with open(config_file, 'r') as stream:
        try:
            config = yaml.load(stream)
            logging.debug("Config file: {0} {1}".format(os.linesep, yaml.dump(config)))
            # validate(config, schema)
        except Exception as e:
            logging.error("[ERROR] Parsing CONFIG file: {0} {1} Please, check the YAML format".format(e, os.linesep))

    observer = Observer()
    try:
        for rule in config:
            filters = []
            for filter in rule['filters']:
                filters.append(LogFilter(**filter))
            log(os.path.abspath(rule['filename']), filters, observer)   
    except Exception as e:
        logging.error("[ERROR] Reading CONFIG file: {0} {1} Please, check the YAML content".format(e, os.linesep))


    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()


#!/usr/bin/env python
import sys, os, time, signal, logging
from Logger.LogEventHandler import LogEventHandler
from Logger.LogFilter import LogFilter, LogFilterSet
from Logger.LogPublisher import LogPublisher
from watchdog.observers import Observer
import argparse
import yaml

publisher = None
observer = None
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


def kill():
    if publisher is not None:
        publisher.stop()
    if observer is not None:
        observer.stop()

def signal_handler(sig, frame):
    logging.info('Gracefully closing remotelogger (Signal: {sinal}) ... '.format(signal=sig))
    kill()
    sys.exit(0)

def signals_trap():
    signal.signal(signal.SIGABRT,  signal_handler)
    signal.signal(signal.SIGFPE,   signal_handler)
    signal.signal(signal.SIGILL,   signal_handler)
    signal.signal(signal.SIGINT,   signal_handler)
    signal.signal(signal.SIGSEGV,  signal_handler)
    signal.signal(signal.SIGTERM,  signal_handler)

def log(path, filters, observer, publisher):
    dir = os.path.split(path)[0]
    logging.info("File: {path}".format(path=path))

    logeventhandler = LogEventHandler(  path=path,
                                        filters=filters,
                                        publisher=publisher,
                                        patterns=[path],
                                        ignore_patterns=[],
                                        ignore_directories=True,
                                        case_sensitive=True)

    observer.schedule(logeventhandler, path=dir, recursive=False)


def parse():
    parser = argparse.ArgumentParser("Send your logs to remote endpoints")
    args = {'config': None, 'filter': None}

    try:
        parser.add_argument('-c', '--config', dest='config', type=str, help='Path to config file', required=True)
        parser.add_argument('-f', '--filter', dest='filter', type=str, help='Path to filter file', required=True)
        args = parser.parse_args()
    except:
        parser.print_help()

    return args


if __name__ == "__main__":
    signals_trap()
    args = parse()


    with open(args.config, 'r') as stream:
        try:
            config = yaml.load(stream)
            logging.debug("Config file: {0} {1}".format(os.linesep, yaml.dump(config)))
            # validate(config_yaml, schema)
        except Exception as e:
            logging.error("[ERROR] Parsing CONFIG file: {0} {1} Please, check the YAML format".format(e, os.linesep))
            kill()
            sys.exit(0)

    publisher = LogPublisher(config, logging)
    publisher.start()
    observer = Observer()

    with open(args.filter, 'r') as stream:
        try:
            filters_yaml = yaml.load(stream)
            logging.debug("Filter file: {0} {1}".format(os.linesep, yaml.dump(filters_yaml)))
            # validate(filters_yaml, schema)
            for rule in filters_yaml:
                filters = []
                for filter in rule['filters']:
                    filters.append(LogFilter(**filter))
                log(os.path.abspath(rule['filename']), filters, observer, publisher)  
        except Exception as e:
            logging.error("[ERROR] Parsing FILTER file: {0} {1} Please, check the YAML format".format(e, os.linesep))
            kill()
            sys.exit(0)

    observer.start()

    try:
        while True:
            time.sleep(1)
    except:
        kill()
        sys.exit(0)

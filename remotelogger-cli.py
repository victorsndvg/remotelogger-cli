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
    logging.info('Gracefully closing remotelogger (Signal: {signal}) ... '.format(signal=sig))
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
    logging.info("Remotelogger observing file: {path}".format(path=path))

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

    parser.add_argument('-d', '--debug', dest='debug', help='Debug mode', action='store_true')    
    parser.add_argument('-f', '--filter', dest='filter', type=str, help='Path to filter file', required=True)    
    parser.add_argument('-c', '--config', dest='config', type=str, help='Path to config file')
    parser.add_argument('-sh', '--host', dest='host', type=str, default='localhost', help='Server host')
    parser.add_argument('-u', '--user', dest='user', type=str, default='guest', help='Server username')
    parser.add_argument('-p', '--pass', dest='passwd', type=str, default='guest', help='Server password')
    parser.add_argument('-e', '--exchange', dest='exchange', type=str, default='default', help='Exchange name')
    parser.add_argument('-rk', '--routing_key', dest='routing_key', type=str, default='default', help='Routing key')
    parser.add_argument('-q', '--queue', dest='queue', type=str, default='default', help='Queue name')
    parser.add_argument('-sp', '--port', dest='port', type=int, default=5672, help='Server port')
    parser.add_argument('-et', '--exchange_type', dest='exchange_type', type=str, default='direct', help='Exchange type')
    parser.add_argument('-hb', '--heartbeat', dest='heartbeat', type=int, default=0, help='Hearbeat')
    parser.add_argument('-bct', '--blocked_connection_timeout', dest='blocked_connection_timeout', type=int, default=300, help='Blocked connection timeout')
    try:
        args = parser.parse_args()
        if args.debug:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        if args.config is None:
            if args.host and args.port and args.user and \
                    args.passwd and args.exchange and \
                    args.routing_key and args.queue:
                args.config = {}
                args.config['host'] = args.host
                args.config['port'] = args.port
                args.config['user'] = args.user
                args.config['pass'] = args.passwd
                args.config['exchange'] = args.exchange
                args.config['routing_key'] = args.routing_key
                args.config['queue'] = args.queue
                args.config['exchange_type'] = args.exchange_type
                args.config['heartbeat'] = args.heartbeat
                args.config['blocked_connection_timeout'] = args.blocked_connection_timeout
            else:
                parser.error("Wrong number of arguments!")
    except:
        sys.exit(0)

    return args


if __name__ == "__main__":
    signals_trap()
    args = parse()

    if isinstance(args.config, dict):
        config = args.config
    else:
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

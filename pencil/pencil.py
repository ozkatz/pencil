#!/usr/bin/env python
"""
A non blocking statsd-like UDP proxy to the Graphite graphing server.
This is more than just a python implementation of statsd. the differences are:

1. Support for gauges (arbitrary numbers) in addition to aggregated counters and timers.
2. No forced name spaces. up to the client to determine the prefixes for his data.
3. Well, built in python. so no dependency on node.js if it isn't part of your stack.

Dependencies:

Described requirements.txt (pip installable).
but basically you need only python > 2.5 (tested against python 2.6 and python 2.7)
and the gevent (http://gevent.org) library for the nifty async I/O stuff.
in order to build gevent (latest version in pypi is too old), you need Cython installed.

HOWTO:

For most projects, installing dependecies and running `./pencil.py &` is sufficient.
A log file will be created in the local directory, with minimal information being logged.
pencil is compatible with most current statsd clients, although the pencil-client library is good reference
in case you also want gauges.

Changing settings:
Simply run `./pencil.py /path/to/settings.json &`

Available settings:
     
    'bind_adress' - Where to listen for incoming requests. this is a UDP port. 
    default is '127.0.0.1:8125'
     
    'management_address' - For the telnet-like TCP interface. useful for stats and debugging.
    default is '127.0.0.1:8126'

    'flush_interval' - Time in seconds between flushes to Graphite.
    default is  10
    
    'graphite_address' - Where graphite is listening to (127.0.0.1:2003 is the default for graphite).
    default is '127.0.0.1:2003'

    'log_name' - Path to the log file for the server.
    default is 'pencil.log'


    'log_level' - How much information do you want in your log file.
    default is 'info'. possible values are: 'debug','info','warning','error'.
    Choose 'error' if you don't care and just want the minimum amount of logging done.
"""

import sys
import pprint
import datetime
import logging
try:
    import json
except ImportError:
    # For python < 2.6
    import simplejson as json

import gevent

from command_server import create_command_server
from listeners import create_datagram_server
from graphite_client import Graphite


DEFAULT_SETTINGS = {
    
    # Point your client library to this address
    'bind_adress' : '127.0.0.1:8125',
     
    # For the telnet-like TCP interface. useful for stats and debugging.
    'management_address' : '127.0.0.1:8126',
    
    # Time in seconds between flushes to Graphite
    'flush_interval' : 10,
    
    # Where graphite is listening to (127.0.0.1:2003 is the default for graphite)
    'graphite_address' : '127.0.0.1:2003',

    # Logging, if needed.
    'log_name' : 'pencil.log',
    'log_level' : 'info' # One of:  debug, info, warning, error
}


class PencilServer(object):
    """
    The main server.
    Listens on a UDP port for incoming aggregation requests,
    and also provides a TCP port for telnet commands.
    """

    def __init__(self, config_file_path=None, additional_settings=None):
        """
        Takes a single argument - a path to a JSON formatted file, containing a key-value mapping of settings.
        Available settings are listed under DEFAULT_SETTINGS in this module
        """
        self.settings = DEFAULT_SETTINGS

        if config_file_path is not None:
            self._load_config(config_file_path)
        
        if additional_settings:
            self.settings.update(additional_settings)

        print('initializing settings:')
        pprint.pprint(self.settings)
    
        self._setup_logging()
        
        # Initialize all components
        storage  = []
        self._listener = self._setup_listener(storage)
        self._management_listener = self._setup_management_server()
        self.graphite = self._setup_graphite_client()

        # setup some info about the server.
        self._is_running = False
        self.start_date = None
        self.request_count = 0
        logging.info('initialized pencil server')
        

    def _load_config(self, config_file_path):
        """
        Load JSON configuration from an external JSON file.
        """
        print('loading configuration')
        
        try:
            conf = open(config_file_path, 'r')
        except IOError:
            print('Unable to open config file: %s' % (config_file_path))
            return
        try:
            json_data = json.load(conf)
            self.settings.update(json_data)
        except ValueError:
            print('Configuration file is not a valid JSON document: %s' % (config_file_path))

        conf.close()    
        
        

    
    def _setup_logging(self):
        """
        Initialize a very basic log file.
        """
        # initialize log file
        log_level = self.settings['log_level']
        if log_level == 'debug':
            print('starting logger in debug mode. filename = %s' % (self.settings['log_name']))
            logging.basicConfig(filename=self.settings['log_name'], level=logging.DEBUG)
        elif log_level == 'info':
            print('starting logger in info mode. filename = %s' % (self.settings['log_name']))
            logging.basicConfig(filename=self.settings['log_name'], level=logging.INFO)
        elif log_level == 'warning':
            print('starting logger in warning mode. filename = %s' % (self.settings['log_name']))
            logging.basicConfig(filename=self.settings['log_name'], level=logging.WARNING)
        elif log_level == 'error':
            print('starting logger in error mode. filename = %s' % (self.settings['log_name']))
            logging.basicConfig(filename=self.settings['log_name'], level=logging.ERROR)

    
    def start(self):
        """
        Start the services for this server:
        UDP listener - receiving requests from client processes such as statsd clients.
        command server - simple TCP server that accepts arbitrary commands. usually over telnet
        flush daemon - a daemon that flushed aggregated data to graphite every X seconds.
        """
        self._is_running = True
        self.start_date = datetime.datetime.now()

        logging.info('starting UDP listener')
        listener = gevent.Greenlet(self._listener.serve_forever)
        listener.start()

        logging.info('starting flush daemon')
        flush_daemon_greenlet = gevent.Greenlet(self._setup_flush_daemon)
        flush_daemon_greenlet.start()

        logging.info('starting command server')
        command_server = gevent.Greenlet(self._management_listener.serve_forever)
        command_server.start()

        logging.info('pencil server started, and is accepting requests.')
        # exit when all of them are done.
        listener.join()
        flush_daemon_greenlet.join()
        command_server.join()

        # Flush before stopping the server:
        self.flush()
        logging.info('pencil server - all services halted.')


    def stop(self):
        """
        Stops all services for this server and exits
        """
        # Stop listener
        logging.info('stopping UDP listener')
        self._listener.stop()
        # Stop command server
        logging.info('stopping command server')
        self._management_listener.stop()
        # Stop flusing daemon
        logging.info('stopping flush daemon')
        self._is_running = False

    
    def _setup_listener(self, storage):
        """
        create a UDP listener instance
        """
        return create_datagram_server(
            self.settings['bind_adress'],
            message_buffer=storage
        )
    
    def _setup_management_server(self):
        """
        create a TCP command server instance
        """
        return create_command_server(
            self.settings['management_address'],
            pencil_instance=self
        )
    
    def _setup_graphite_client(self):
        """
        A non-blocking graphite client using gevent's socket library.
        """
        return Graphite(
            self.settings['graphite_address'],
            flush_interval=self.settings['flush_interval']
        )

    def _setup_flush_daemon(self):
        """
        runs the flush() command every X (configurable) seconds.
        """
        interval = self.settings['flush_interval']
        g = None
        while self._is_running:
            g = gevent.Greenlet(self.flush)
            g.start_later(interval)
            gevent.sleep(interval)
        
        if g is not None:
            g.join()


    def flush(self):
        """
        Flush data to graphite.
        the graphite client shoud take all requests that were aggregated so far,
        crunch them and send the relevant graph data to graphite.
        """
        logging.debug('flushing message buffer')
        queue = []
        for msg in self._listener.message_buffer:
            queue.append(msg)
            self.request_count += 1
        self._listener.message_buffer = []

        # Aggregate and send over TCP
        logging.debug('sending the following data to graphite client: %s' % (queue))
        self.graphite.write(queue)



def main():
    try:
        config_path = sys.argv[1]
    except IndexError:
        config_path = None
    
    
    server = PencilServer(config_path)
    server.start()


if __name__ == '__main__':
    main()

    




import time
import logging
from gevent import socket 

def get_timestamp():
    return int(time.time())

class Graphite(object):

    def __init__(self, server_addr, flush_interval):
        host, port = server_addr.split(':')
        self.host = host
        self.port = port
        
        self.flush_interval = flush_interval
        
        self.processed = 0
        self.bad_lines = 0
        
        # Initialize data
        self.counters = {}
        self.gauges = {}
        self.timers = {}
        self.stats = []

        # collect messages into a buffer in case graphite is down.
        self._buffer = []
        logging.debug('initialized Graphite client.')
        logging.debug(' host = %s, port = %s, flush interval = %d' % (
            host, port, flush_interval
        ))


    def socket_write_buffer(self):
        try:
            msg = ''.join(self._buffer)
            logging.debug('connecting to graphite over TCP')
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            logging.debug('connected to graphite, sending data')
            sock.send(msg)
            logging.debug('send the following message to graphite: %s' % (msg))
            sock.close()
            logging.debug('TCP socket to graphite closed.')

            self.processed += len(msg.split('\n'))
            self._buffer = []
        
        except socket.error, msg:
            logging.error('could not flush data to graphite server: %s' % (msg))
            logging.error('will try again in %d seconds' % (self.flush_interval))
        


    def write(self, queue):
        # Parse and aggregate data.
        for message in queue:
            key, value = message.split(':')
            fields = value.split('|')
            msg_type = fields[1].strip()
            msg_value = fields[0]
            
            if not len(fields) > 1:
                # Bad line
                logging.warning('got a bad line: %s' % (message))
                self.bad_lines += 1
                continue
            
            logging.debug('message key = %s, type = %s, message value = %s' % (key, msg_type, msg_value))
            
            # Timers
            if msg_type == 'ms':
                if not key in self.timers:
                    self.timers[key] = []
                logging.debug('got timer request. appending to key = %s, value = %s' % (key, float(msg_value)))
                self.timers[key].append(float(msg_value))
            
            # Gauges
            elif msg_type == 'g':
                logging.debug('got gauge request. setting key = %s, value = %s' % (key, msg_value))
                self.gauges[key] = msg_value

            # Counters
            else:
                if key not in self.counters:
                    self.counters[key] = 0
                logging.debug('got counter request. appending to key = %s, value = %s' % (key, msg_value))
                self.counters[key] += float(msg_value)
                logging.debug('counter request current value = %s' % (self.counters[key]))
        
        # aggregate data
        timestamp = get_timestamp()
        
        # Timers
        for k,v in self.timers.iteritems():
            if len(v) > 0:
                self.stats.append('%s.count %s %s' % (k, len(v), timestamp))
                self.stats.append('%s.lower %s %s' % (k, int(min(v)), timestamp))
                self.stats.append('%s.avg %s %s' % (k, int(sum(v, 0.0) / len(v)), timestamp))
                self.stats.append('%s.sum %s %s' % (k, int(sum(v, 0)), timestamp))
                self.stats.append('%s.upper %s %s' % (k, int(max(v)), timestamp))

            # Reset timer.
            self.timers[k] = []
        
        # Gauges
        for k,v in self.gauges.iteritems():
            self.stats.append('%s, %s, %s' % (k, v, timestamp))

        # Counters
        for k,v in self.counters.iteritems():
            if v == 0:
                self.stats.append('%s %s %s' % (k, v, timestamp))
            else:
                self.stats.append('%s %s %s' % (k, v / self.flush_interval, timestamp))
            
            # Reset counter
            self.counters[k] = 0
        
        logging.debug('about to send the following messages: %s' % (self.stats))
        

        # Send over to graphite server.
        if len(self.stats) > 0:
            msg = '\n'.join(self.stats)
            self._buffer.append(msg)
            self.stats = []

        if len(self._buffer) > 0:
            logging.debug('buffer size: %s, sending data to graphite' % (len(self._buffer)))
            self.socket_write_buffer()
        else:
            logging.debug('buffer is empty, not sending data to graphite')
        


            







        

                
            
            
    

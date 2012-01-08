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
        counters = {}
        gauges = {}
        timers = {}
        stats = []

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
                if not key in timers:
                    timers[key] = []
                logging.debug('got timer request. appending to key = %s, value = %s' % (key, float(msg_value)))
                timers[key].append(float(msg_value))
            
            # Gauges
            elif msg_type == 'g':
                logging.debug('got gauge request. setting key = %s, value = %s' % (key, msg_value))
                gauges[key] = msg_value

            # Counters
            else:
                if key not in counters:
                    counters[key] = 0
                logging.debug('got counter request. appending to key = %s, value = %s' % (key, msg_value))
                counters[key] += float(msg_value)
                logging.debug('counter request current value = %s' % (counters[key]))
        
        # aggregate data
        timestamp = get_timestamp()
        
        # Timers
        for k,v in timers.iteritems():
            stats.append('%s_count %s %s' % (k, len(v), timestamp))
            stats.append('%s_lower %s %s' % (k, min(v), timestamp))
            stats.append('%s_avg %s %s' % (k, sum(v, 0.0) / len(v), timestamp))
            stats.append('%s_sum %s %s' % (k, sum(v, 0.0), timestamp))
            stats.append('%s_upper %s %s' % (k, max(v), timestamp))
        
        # Gauges
        for k,v in gauges.iteritems():
            stats.append('%s, %s, %s' % (k, v, timestamp))

        # Counters
        for k,v in counters.iteritems():
            if v == 0:
                stats.append('%s %s %s' % (k, v, timestamp))
            else:
                stats.append('%s %s %s' % (k, v / self.flush_interval, timestamp))
        
        logging.debug('about to send the following messages: %s' % (stats))
        

        # Send over to graphite server.
        if len(stats) > 0:
            msg = '\n'.join(stats)
            self._buffer.append(msg)

        if len(self._buffer) > 0:
            logging.debug('buffer size: %s, sending data to graphite' % (len(self._buffer)))
            self.socket_write_buffer()
        else:
            logging.debug('buffer is empty, not sending data to graphite')
        


            







        

                
            
            
    

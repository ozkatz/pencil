"""
This is the application side interface.
the UDP listener is a lean and mean component that takes a message from a pencil (or statsd) client,
and adds it to the current message buffer for the running pencil server.
"""
import logging
from gevent.server import DatagramServer

class UDPListener(DatagramServer):

    def __init__(self, *args, **kwargs):
        self.message_buffer = kwargs.pop('message_buffer')
        super(UDPListener, self).__init__(*args, **kwargs)        

    def handle(self, data, address):
        logging.debug('got message from %s: "%s"' % (address, data))
        self.message_buffer.append(data)
    
    def __str__(self):
        return 'Pencil UDP Listener'



def create_datagram_server(addr, message_buffer):
    return UDPListener(addr, message_buffer=message_buffer)

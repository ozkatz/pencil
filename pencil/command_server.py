"""
Pencil's command server.
A telnet interface for probing and querying a Pencil server instance.
This file defines the available commands, as well as define the command
server interface, accepting these commands.
"""

import logging
from gevent.server import StreamServer


# Command actions.
class BaseCommand(object):
    """
    A baseline for all commands to inherit from.
    basically defines the execute(*args) method,
    and holds a reference to the pencil server instance.
    """
    def __init__(self, pencil_server):
        self.pencil_server = pencil_server
    
    def execute(self, *args):
        raise NotImplementedError('Override this!')


class ShowStorageCommand(BaseCommand):
    """
    print out the raw message buffer currently stored 
    by the pencil server instance.
    """
    def execute(self, *args):
        return str(self.pencil_server._listener.message_buffer)


class ShowStatusCommand(BaseCommand):
    """
    Print out the server's start date
    and the amount of handled requests
    """
    def execute(self, *args):
        return 'up since %s, total requests: %s' % (
            self.pencil_server.start_date,
            self.pencil_server.request_count
        )


class StopServerCommand(BaseCommand):
    """
    Stop the pencil server instance.
    """
    def execute(self, *args):
        self.pencil_server.stop()
        return 'shutting down server.'


class GraphiteTimers(BaseCommand):
    """
    print the currently aggregated timers for this pencil instance.
    """
    def execute(self, *args):
        return str(self.pencil_server.graphite.timers)


class GraphiteCounters(BaseCommand):
    """
    print the currently aggregated counters for this pencil instance.
    """
    def execute(self, *args):
        return str(self.pencil_server.graphite.counters)


class GraphiteGauges(BaseCommand):
    """
    print the currently aggregated gauges for this pencil instance.
    """
    def execute(self, *args):
        return str(self.pencil_server.graphite.gauges)

# The actual server class
class CommandServer(object):
    """
    this class holds the logic for running commands and serving clients.
    """
    commands =  {
        'storage': ShowStorageCommand,
        'status' : ShowStatusCommand,
        'stop_server' : StopServerCommand,
        'timers' : GraphiteTimers,
        'gauges' : GraphiteGauges,
        'counters' : GraphiteCounters
    }

    def __init__(self, pencil_server):
        self.pencil_server = pencil_server
        self.commands = self.__class__.commands

    def get_commands(self):
        commands = self.commands.keys()
        commands.append('help')
        commands.append('quit')
        command_list = ', '.join(commands)

        return 'available commands: %s' % (command_list)


    def server(self, socket, address):
        """
        this method will be used to build a TCP server (`StreamServer`) by gevent
        """
        fileobj = socket.makefile()
        fileobj.write('Welcome to pencil\'s command server. Type quit to exit.\r\n')
        logging.debug('new connection from ' + str(address))
        fileobj.flush()
        while True:
            line = fileobj.readline()
            
            if not line:
                fileobj.write('')
                continue
            
            command_parts = line.strip().lower().split()
            if not len(command_parts) > 0:
                fileobj.write('')
                continue

            command = command_parts[0]
            args = command_parts[1:]

            logging.debug('executing command from %s: %s' % (address, line))

            if command == 'quit':
                break

            if command in self.commands.keys():
                command_class = self.commands[command](self.pencil_server)
                output = command_class.execute(*args)
            else:
                output = self.get_commands()

            fileobj.write('%s\r\n' % (output))
            fileobj.flush()



def create_command_server(addr, pencil_instance):
    command_server =  CommandServer(pencil_instance)
    return StreamServer(addr, command_server.server)









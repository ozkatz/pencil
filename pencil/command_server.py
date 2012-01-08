import logging
from gevent.server import StreamServer


# Command actions.
class BaseCommand(object):

    def __init__(self, pencil_server):
        self.pencil_server = pencil_server
    
    def execute(self, *args):
        raise NotImplementedError('Override this!')


class ShowStorageCommand(BaseCommand):

    def execute(self, *args):
        return str(self.pencil_server._listener.message_buffer)


class ShowStatusCommand(BaseCommand):

    def execute(self, *args):
        return 'up since %s, total requests: %s' % (
            self.pencil_server.start_date,
            self.pencil_server.request_count
        )


class StopServerCommand(BaseCommand):

    def execute(self, *args):
        self.pencil_server.stop()
        return 'shutting down server.'


# The actual server class
class CommandServer(object):

    commands =  {
        'storage': ShowStorageCommand,
        'status' : ShowStatusCommand,
        'stop_server' : StopServerCommand
    }

    def __init__(self, pencil_server):
        self.pencil_server = pencil_server
        self.commands = self.__class__.commands

    def get_commands(self):
        command_list = ', '.join(self.commands.keys())
        command_list.append('help')
        command_list.append('quit')
        return 'available commands: %s' % (command_list)


    def server(self, socket, address):
        fileobj = socket.makefile()
        fileobj.write('Welcome to the echo server! Type quit to exit.\r\n')
        logging.debug('new connection from %s' % (address))
        fileobj.flush()
        while True:
            line = fileobj.readline()
            
            if not line:
                break
            
            command_parts = line.strip().lower().split()
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









from pencil.pencil import PencilServer, main

__all__ = ['PencilServer', ]
VERSION = (0, 1, 0)
__version__ = '.'.join(map(str, VERSION))

if __name__ == '__main__':
    main()
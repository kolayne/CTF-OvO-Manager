#!/usr/bin/python3
from sys import argv, stderr

from common import is_help_request
from run import main as run
from stop import main as stop
from cleanup import main as cleanup

usage = """Usage: ovo <command> [<args>]

The CTF OvO Manager is an application that helps you controlling task distribution inside a team during a CTF game

These are ovo commands:
    run     run a new game
    rerun   run an existing stopped game
    stop    stop the game by it's id
    cleanup remove game's database and remove all the files
    owo     run operation with a running game (more info in `ovo owo --help`)"""

if __name__ == "__main__":
    if(len(argv) == 1) or is_help_request(argv):
        print(usage, file=stderr)
        exit(len(argv) - 1)
    elif(argv[1] == 'run'):
        run(argv[1:])
    elif(argv[1] == 'rerun'):
        run(argv[1:], rerun=True)
    elif(argv[1] == 'stop'):
        stop(argv[1:])
    elif(argv[1] == 'cleanup'):
        cleanup(argv[1:], timer=5)
    elif(argv[1] == 'owo'):
        pass
    else:
        print("Unknown command {}. Try --help for usage".format(argv[1]), file=stderr)
        exit(1)

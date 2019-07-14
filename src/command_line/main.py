#!/usr/bin/python3
from sys import argv, stderr, path

path.append('/usr/ovo/command_line')
from common import is_help_request
from run import main as run
from stop import main as stop
from cleanup import main as cleanup
from owo import main as owo

usage = """Usage: ovo <command> [<args>]

The CTF OvO Manager is an application that helps you controlling task distribution inside a team during a CTF game

These are ovo commands:
    run     run a new game
    rerun   run an existing stopped game
    stop    stop the game
    cleanup remove game's database and remove all the files
    owo     call an operation with a running game (more info in `ovo owo --help`)
"""

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
        cleanup(argv[1:])
    elif(argv[1] == 'owo'):
        owo(argv[1:])
    else:
        print("Unknown command {}. Try --help for usage".format(argv[1]), file=stderr)
        exit(1)

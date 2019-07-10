#!/usr/bin/python3
from sys import stderr, argv
from pathlib import Path
from os import path
from time import sleep

import mysql.connector

from common import is_help_request, \
        get_db_connection, \
        assert_ok_dbname

usage = """Usage: ovo stop <id: str>

Stops the OvO game with the given id
"""

def _main(game_id:str):
    """Creates a stop-file for the game with given id
    Parameters:
        id (str): Game identificator
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT files_folder FROM game_info')
    folder, = c.fetchone()
    Path(path.join(folder, 'exit')).touch()
    sleep(1)

def main(args):
    if is_help_request(args):
        print(usage, file=stderr)
        exit(0)
    if(len(args) == 2):
        _main(args[1])
    else:
        print("Wrong number of arguments. Try --help for usage", file=stderr)
        exit(1)

if __name__ == "__main__":
    main(argv)

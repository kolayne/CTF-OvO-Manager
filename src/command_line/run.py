#!/usr/bin/python3
from sys import argv, stderr
from getpass import getpass
from os import listdir, remove, path
from pathlib import Path
from subprocess import Popen, DEVNULL
from time import sleep

import mysql.connector
import bcrypt

from common import is_help_request, \
        get_db_connection, \
        assert_ok_dbname
from stop import _main as stop

usage = """Usage: ovo <run/rerun> [<args>]. Required arguments not specified in the command line will be requested from stdin.

Runs a new game under OvO Manager

If you're running `run`:
Required args:
    -i, --id: str               An identifier of the game. Will be used to stop or cleanup it. The ('OvO_' + id) database will be created in MySQL
    -r, --register-pass: str    A password required to register in the system
    -c, --captain-pass: str     A password required to register as a team captain
    -p, --port: int             The port to run web interface on
    -f, --files-folder: str     The path to the folder where (uploaded) files will be stored
Positional args:
    --judge-url: str            An url to the CTF platform to get tasks from. It must contain protocol (http/https/...) and port if not 80
    --judge-login: str          User login for the CTF platform. No need to specify, if the CTF platform supports getting tasks with no authorization
    --judge-pass: str           User password for the CTF platform. No need to specify, if the CTF platform supports getting tasks with no authorization

If you're running `rerun`, `id` is the only required argument. No arguments will be requested from stdin for `rerun`

Examples:
    ovo run -i HeLlO -r easy_password --captain-pass harder_password --port 5000 --judge-url http://ctfd_host.ru:5000 --judge-login a --judge-pass b
    ovo rerun -i HeLlO --judge-url https://ctfd_host.ru/path/to/ctfd --captain-pass new_password
"""

def init_db(db_name:str, c):
    """Initializes a mysql database for a new game
    Parameters:
        db_name(str): New database name
        cursor: mysql cursor
    """
    assert_ok_dbname(db_name)
    c.execute('CREATE DATABASE {}'.format(db_name))
    c.execute('USE ' + db_name)
    query = "CREATE TABLE users ( \
            login VARCHAR(3072) PRIMARY KEY NOT NULL, \
            password TEXT NOT NULL, \
            is_captain ENUM('Y', 'N') NOT NULL DEFAULT 'N', \
            avatar VARCHAR(128) \
            )"
    c.execute(query)
    query = "CREATE TABLE tasks ( \
            id VARCHAR(128) PRIMARY KEY NOT NULL, \
            name TEXT NOT NULL, \
            is_solved ENUM('Y', 'N') NOT NULL DEFAULT 'N', \
            original_link TEXT, \
            original_id TEXT, \
            text TEXT \
            )"
    c.execute(query)
    query = "CREATE TABLE solvings ( \
            user_id VARCHAR(2944) NOT NULL, \
            task_id VARCHAR(128) NOT NULL, \
            PRIMARY KEY (`user_id`, `task_id`) \
            )"
    c.execute(query)
    query = "CREATE TABLE files ( \
            id VARCHAR(128) PRIMARY KEY NOT NULL, \
            name TEXT NOT NULL \
            )"
    c.execute(query)
    query = "CREATE TABLE comments( \
            id VARCHAR(128) NOT NULL PRIMARY KEY, \
            task_id VARCHAR(128) NOT NULL, \
            user_id VARCHAR(2944) NOT NULL, \
            text TEXT, \
            attached_files_ids TEXT \
            )"
    c.execute(query)
    query = "CREATE TABLE session_data( \
            user_id VARCHAR(2944) NOT NULL PRIMARY KEY, \
            session_id VARCHAR(128) NOT NULL UNIQUE KEY \
            )"
    c.execute(query)
    query = "CREATE TABLE game_info( \
            port INTEGER NOT NULL, \
            files_folder VARCHAR(4096) NOT NULL, \
            register_pass TEXT NOT NULL, \
            captain_pass TEXT NOT NULL, \
            judge_url TEXT, \
            judge_login TEXT, \
            judge_pass TEXT, \
            _uniquer ENUM('0') NOT NULL DEFAULT '0' UNIQUE KEY \
            )"
    c.execute(query)

def _main(args:dict, rerun:bool=False):
    """Runs a new OvO game
    Parameters:
        args (dict): Arguments dict in the {agument: value} format
    """
    assert_ok_dbname(args['--id'])

    db = get_db_connection()
    c = db.cursor()
    c.execute('SHOW DATABASES')
    if('OvO_' + args['--id'] in map(lambda x: x[0], c.fetchall())):
        if rerun:
            stop(args['--id'])
        else:
            raise RuntimeError("The game with {} identifier already exists".format(args['--id']))
    
    if '--files-folder' in args.keys():
        args['--files-folder'] = path.abspath(args['--files-folder'])
    if '--register-pass' in args.keys():
        args['--register-pass'] = bcrypt.hashpw(
                args['--register-pass'].encode('utf-8'),
                bcrypt.gensalt()
                ).decode('utf-8')
    if '--captain-pass' in args.keys():
        args['--captain-pass'] = bcrypt.hashpw(
                args['--captain-pass'].encode('utf-8'),
                bcrypt.gensalt()
                ).decode('utf-8')

    if rerun: # Updating values
        c.execute('USE OvO_' + args['--id'])
        for arg, value in args.items():
            if(arg == '--id'): continue
            key = arg[2:].replace('-', '_')
            assert_ok_dbname(key)
            query = 'UPDATE game_info SET {}=(%s)'
            c.execute(query.format(key), (value,))
    else: # Saving values
        init_db('OvO_' + args['--id'], c)
        c.execute('INSERT INTO game_info (port, files_folder, register_pass, captain_pass, judge_url, judge_login, judge_pass) \
                VALUES (%s, %s, %s, %s, %s, %s, %s)', tuple(map(lambda x: args.get(x), [
                    '--port', '--files-folder', '--register-pass', '--captain-pass', '--judge-url', '--judge-login', '--judge-pass'
                    ]))) # If some required values were not specified, MySQL will raise an exception
    if rerun:
        # Remove the stop-file if exists:
        c.execute('SELECT files_folder FROM game_info')
        try:
            remove(path.join(c.fetchone()[0], 'exit'))
        except FileNotFoundError:
            pass
    else:
        # Create files directory:
        try:
            Path(args['--files-folder']).mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            if len(list(listdir(args['--files-folder']))):
               raise ValueError("The folder for files must be empty")

    pass # RUN TASKS CATCHER HERE
    db.commit()
    Popen([
        path.join(path.dirname(path.abspath(__file__)), '../web/main.py'),
        args['--id']
        ], stdout=DEVNULL)
    sleep(1)

def main(args:list, rerun:bool=False):
    """Runs a new OvO game
    Parameters:
        args(list): Arguments list in the format of command line args
    """
    if is_help_request(args):
        print(usage, file=stderr)
        exit(0)
    else:
        args = args[1:]

    to_long = {'-i': '--id', '-r': '--register-pass',
            '-c': '--captain-pass', '-p': '--port', '-f': '--files-folder'}
    long_only = ['--judge-url', '--judge-login', '--judge-pass']
    required = ['--id', '--register-pass', '--captain-pass', '--port', '--files-folder']

    converted_args = {}
    now_insertable_key = None
    for arg in args:
        if(now_insertable_key is None):
            if(arg in long_only) or (arg in to_long.values()):
                now_insertable_key = arg
            elif arg in to_long.keys():
                now_insertable_key = to_long[arg]
            else:
                raise ValueError("Unknown argument {}. Please, see --help".format(arg))
        else:
            converted_args[now_insertable_key] = arg
            now_insertable_key = None

    if not rerun:
        for arg in required:
            if arg in converted_args.keys():
                continue
            read_func = None
            if arg.endswith('pass') or arg.endswith('password'):
                read_func = lambda x: getpass('(safe input) ' + x)
            else:
                read_func = input
            converted_args[arg] = read_func("Please, enter the value for {}: ".format(arg))

    _main(converted_args, rerun)

if __name__ == "__main__":
    main(argv)

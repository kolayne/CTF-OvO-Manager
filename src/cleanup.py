#!/usr/bin/python3
from sys import argv, stderr
from time import sleep
from os import path, remove, rmdir

import mysql.connector

from common import is_help_request, \
        get_db_connection, \
        assert_ok_dbname
from stop import _main as stop

usage = """Usage: ovo cleanup <id: string>

Removes all the information about the game with the given id, including uploaded files
"""

def _main(game_id:str, timer:int=0):
    """Removes all the game info, including uploaded files
    Parameters:
        game_id(str): The game begin removed identifier
        timer(int, optional): if specified, the user will be given `timer` seconds to interrupt
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)

    while timer > 0:
        print("Be careful: I'm now going to remove all the data about the game with {} \
identificator. You have {} seconds left to interrupt (Ctrl+C)".format(
                    game_id,
                    timer
                    ), file=stderr, end='\r')
        sleep(1)
        timer -= 1
    print()

    stop(game_id)

    c.execute('SELECT files_folder FROM game_info')
    folder, = c.fetchone()
    c.execute('SELECT id FROM files')
    for filename in ['exit'] + list(map(lambda x: x[0], c.fetchall())):
        try:
            remove(path.join(folder, filename))
        except FileNotFoundError:
            print("Important warning: couldn't delete a file, because it doesn't exist", file=stderr)
        except PermissionError:
            print("Important warning: couldn't delete a file, because of permissions", file=stderr)
        except OSError as e:
            print("Important warning: couldn't delete a file, because of OSError ({})".format(e), file=stderr)
        except Exception as e:
            print("Important warning: couldn't delete a file, because of unknown error ({})".format(e), file=stderr)
    try:
        rmdir(folder)
    except FileNotFoundError:
        print("VERY important warning: directory for containing this game files doesn't exist", file=stderr)
    except PermissionError:
        print("Important warning: couldn't delete the folder, because of permissions", file=stderr)
    except OSError as e:
        print("Important warning: couldn't delete the folder, because of OSError ({})".format(e), file=stderr)
    except Exception as e:
        print("Important warning: couldn't delete the folder, because of unknown error ({})".format(e), file=stderr)
    
    c.execute('DROP DATABASE OvO_' + game_id) # The program freezes here until the database is freed
    db.commit()

def main(args, timer=0):
    if is_help_request(args):
        print(usage, file=stderr)
        exit(0)
    if len(args) == 2:
        _main(args[1], timer)
    else:
        print("Wrong number of arguments. Try --help for usage", file=stderr)
        exit(1)

if __name__ == "__main__":
    main(argv)

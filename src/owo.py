from sys import stderr, argv
from random import random
from hashlib import sha3_512
import json
from functools import reduce

import mysql.connector
import bcrypt

from common import is_help_request, \
        get_db_connection, \
        assert_ok_dbname

usage = """Usage: ovo owo <game_id: str> <command> [<args>]

Calls an operation (`command`) for a running game with the given id

The following commands are avaliable:
    add task <--name: str> [--original-link: str] [--original-id str] [--text str]
        Adds the task. original-id is a value used to identify that the task
            has already been imported from the original platform
    add file <name: str>
        Creates the file id (it will be printed). You have to save your file
            as ${GAME_FILES_FOLDER}/${FILE_ID}. After that you can use
            the generated id as an argument for other commands
    add user <--login: str> <--password: str> [--is-captain] [--avatar: str]
        Adds the user. avatar is the file id (got after `ovo owo add file`)
    add comment <--user-id: str> <--text: str> <--task-id: str> [<--file-id: str>]
        Adds the comment. Can contain an attachment or attachmentS (--file-id)
    rm <task, file, user, comment> <entity_id: str>
        Removes the entity with the given id
    mark user <user_id: str> <captain/default>
        Marks the user as a captain or as a default participant
    mark task <task_id: str> <solved/unsolved>
        Marks the task as solved or not solved
    update_avatar <user_id: str> <file_id: str>
        Updates user's avatar with the given file
    take_task <--task-id: str> <--user-id: str>
        Remembers, that the user is solving the task. One user can take multiple
            tasks. One task can be taken by multiple users

Examples:
    ovo owo MY_GAME_1 add user --login user1 --password abcde
    FILE_ID=$(ovo owo MY_GAME_1 add file --name my_new_file)
    cp /home/me/my_new_file ${GAME_FILES_FOLDER}/${FILE_ID}
    ovo owo MY_GAME_1 update_avatar user1 $FILE_ID
    ovo owo MY_GAME_1 mark user user1 captain
"""


def _generate_id() -> str:
    """Generates a random id for an entity
    Returns:
        str: random hash
    """
    return sha3_512(str(random()).encode('utf-8')).hexdigest()

def _db_insert(game_id:str, query:str, values:tuple):
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    while True: # Looging for id wasn't given before
        local_id = _generate_id()
        try:
            c.execute(query, [local_id] + list(values))
            break
        except Exception as e:
            if e.errno == 1062: # The given id already exists
                continue
            else:
                raise e
    db.commit()
    return local_id

def add_task(game_id:str, name:str, original_link:str=None,
        original_id:str=None, text:str=None) -> str:
    """Adds the task to the game database
    Parameters:
        game_id(str): The game identifier
        name(str): The task name to be displayed
        original_link(str, optional): A link to the task on the main platform
            to be displayed
        original_id(str, optional): The task identifier on the main platform
        text(str, optional): The text of the task to be displayed
    Returns:
        str: The created task id
    """
    query = 'INSERT INTO tasks(id, name, original_link, original_id, task_text) \
            VALUES (%s, %s, %s, %s, %s)'
    return _db_insert(game_id, query, (name, original_link, original_id, text))

def add_file(game_id:str, name:str, silent:bool=False) -> str:
    """Adds the file to the game database
    Parameters:
        game_id(str): The game identifier
        name(str): The file name to be displayed
        silent(bool, optional): If the function has to be silent or \
                it can output some hints to stderr
    Returns:
        str: The created file id
    """
    query = 'INSERT INTO files(id, name) VALUES (%s, %s)'
    ans = _db_insert(game_id, query, (name,))
    if not silent:
        print("Please save your file to the game files folder, please use the \
following name: {}".format(ans), file=stderr)
    return ans

def add_user(game_id:str, login:str, password:str,
        is_captain:bool=False, avatar_file_id:str=None):
    """Adds the user to the game database
    Parameters:
        game_id(str): The game identifier
        login(str): The user identifier
        password(str): User's password
        is_captain(bool, optional): if the registering user must become captain
        avatar_file_id(str, optional): The avatar file id (got from add_file)
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    query = 'INSERT INTO users(login, password, is_admin, avatar) \
            VALUES (%s, %s, %s, %s)'
    c.execute(query, (
        login,
        bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        'Y' if is_captain else 'N',
        avatar_file_id
        ))
    db.commit()

def add_comment(game_id:str, user_id:str, task_id:str, text:str=None, files_ids:list=None) -> str:
    """Adds the comment to the game database
    Parameters:
        game_id(str): The game identifier
        user_id(str): The comment author identifier
        task_id(str): The commenting task's identifier
        text(str, optional): The comment text
        files_ids(list[str], optional): Identifiers of the attaching files
    Returns:
        str: The created comment id
    """
    if files_ids is None:
        files_ids = []
    assert(all(map(lambda x: type(x) is str, files_ids)))
    query = 'INSERT INTO comments(comment_id, task_id, user_id, text, attached_files_ids) \
            VALUES (%s, %s, %s, %s, %s)'
    return _db_insert(game_id, query, (task_id, user_id, text, json.dumps(files_ids)))

def _db_rmer(game_id:str, table_name:str, removing_id:str, entity_id:str):
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('SHOW TABLES')
    assert(table_name in map(lambda x: x[0], c.fetchall()))
    c.execute('DELETE FROM {} WHERE {}=(%s)'.format(table_name, removing_id), (entity_id,))
    db.commit()

def rm_task(game_id:str, task_id:str) -> list:
    """Removes the task from the game database
    Parameters:
        game_id(str): The game identifier
        task_id(str): The task identifier
    Returns:
        list[str]: ids of files which were attached to the task
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT attached_files_ids FROM comments WHERE task_id=(%s)', (task_id,))
    ans = reduce(lambda a, b: json.dumps(json.loads(a) + json.loads(b[0])), c.fetchall())
    if type(ans) is tuple: # Only one attached file
        ans, = ans
    c.execute('DELETE FROM comments WHERE task_id=(%s)', (task_id,))
    c.execute('DELETE FROM tasks WHERE id=(%s)', (task_id,))
    db.commit()
    return json.loads(ans)

def rm_file(game_id:str, file_id:str):
    """Removes the file from the game database
    Parameters:
        game_id(str): The game identifier
        file_id(str): The file identifier
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c.execute('USE OvO_' + game_id)
    c.execute('DELETE FROM files WHERE id=(%s)', (file_id,))
    db.commit()

def rm_user(game_id:str, user_id:str) -> str:
    """Removes the user from the game database
    Parameters:
        game_id(str): The game identifier
        user_id(str): The user identifier
    Returns:
        str: The user's avatar file id to be removed
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT avatar FROM users WHERE login=(%s)', (user_id,))
    ans, = c.fetchone()
    c.execute('DELETE FROM users WHERE login=(%s)', (user_id,))
    db.commit()
    return ans

def rm_comment(game_id:str, comment_id:str) -> list:
    """Removes the comment from the game database
    Parameters:
        game_id(str): The game indentifier
        comment_id(str): The comment identifier
    Returns:
        list[str]: ids of files which were attached to the comment
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT attached_files_ids FROM comments WHERE comment_id=(%s)', (comment_id,))
    ans, = c.fetchone()
    c.execute('DELETE FROM comments WHERE comment_id=(%s)', (comment_id,))
    db.commit()
    return json.loads(ans)


def mark_user(game_id:str, user_id:str, new_type:str):
    """Marks the user as a captain or as a default participant
    Parameters:
        game_id(str): The game identifier
        user_id(str): The user identifier
        new_type(str): Either "captain" or "default"
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    query = 'UPDATE users SET is_admin=(%s)'
    if new_type == "captain":
        c.execute(query, ('Y',))
    elif new_type == "default":
        c.execute(query, ('N',))
    else:
        raise ValueError("Unknown user type. Must be either captain or default")
    db.commit()

def mark_task(game_id:str, task_id:str, new_type:str):
    """Marks the task as solved or not solved
    Parameters:
        game_id(str): The game identifier
        task_id(str): The task identifier
        new_type(str): Either "solved" or "unsolved"
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE  OvO_' + game_id)
    query = 'UPDATE tasks SET is_solved=(%s)'
    if new_type == "solved":
        c.execute(query, ('Y',))
    elif new_type == "unsolved":
        c.execute(query, ('N',))
    else:
        raise ValueError("Unknown task type. Must be either solved or unsolved")
    db.commit()

def update_avatar(game_id:str, user_id:str, avatar_file_id:str):
    """Updates the user's avatar with the given
    Parameters:
        game_id(str): The game identifier
        user_id(str): The user identifier
        avatar_file_id(str): The avatar file id (got from add_file)
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('UPDATE users SET avatar=(%s) WHERE login=(%s)', (avatar_file_id, user_id))
    db.commit()

def take_task(game_id:str, task_id:str, user_id:str):
    """Creates a connection between the user and the task
            (a user can be connected to multiple tasks,
            a task can be connected to multiple users)
       Parameters:
            game_id(str): The game identifier
            task_id(str): The task identifier
            user_id(str): The user identifier
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('INSERT INTO solvings(task_id, user_id) VALUES (%s, %s)', (task_id, user_id))
    db.commit()

def main(args: list):
    ans = None

    try:
        if(is_help_request(args)):
            print(usage, file=stderr)
            exit(0)
        game_id = args[1]
        if args[2] == 'add':
            d = None
            if args[3] == 'file':
                d = {'name': args[4]}
            elif args[3] == 'task':
                d = {}
                now_insertable = None
                for arg in args[4:]:
                    if now_insertable is None:
                        now_insertable = arg
                        continue
                    d[now_insertable[2:].replace('-', '_')] = arg
                    now_insertable = None
            elif args[3] == 'user':
                d = {}
                now_insertable = None
                for arg in args[4:]:
                    if arg == '--is-captain':
                        d['is_captain'] = True
                        continue
                    if now_insertable is None:
                        now_insertable = arg
                        continue
                    d[now_insertable[2:].replace('-', '_')] = arg
                    now_insertable = None
            elif args[3] == 'comment':
                d = {}
                now_insertable = None
                files_ids = []
                for arg in args[4:]:
                    if now_insertable is None:
                        now_insertable = arg
                        continue
                    if now_insertable == '--file-id':
                        files_ids.append(arg)
                    else:
                        d[now_insertable[2:].replace('-', '_')] = arg
                    now_insertable = None
                d['files_ids'] = files_ids
            else:
                raise ValueError("Unknown entitie {}. Task, file, user, comment are avaliable".format(args[2]))
            ans = {'task': add_task, 'file': add_file, 'user': add_user, 'comment': add_comment} \
                    [args[3]](game_id, **d)
        elif args[2] == 'rm':
            ans = {'task': rm_task, 'file': rm_file, 'user': rm_user, 'comment': rm_comment} \
                    [args[3]](game_id, args[4])
        elif args[2] == 'mark':
            ans = {'user': mark_user, 'task': mark_task}[args[3]](game_id, args[4], args[5])
        elif args[2] == 'update_avatar':
            ans = update_avatar(game_id, args[3], args[4])
        elif args[2] == 'take_task':
            d = {}
            now_insertable = None
            for arg in args[3:]:
                if now_insertable is None:
                    now_insertable = arg
                    continue
                d[now_insertable[2:].replace('-', '_')] = arg
                now_insertable = None
            ans = take_task(**d)
        else:
            raise ValueError("Unknown command {}. Try --help for usage".format(args[2]))
    except IndexError:
        raise ValueError("Wrong number of arguments specified. Try --help for usage")
    except TypeError:
        raise ValueError("Looks like you either missed an argument or gave an unexpected one. For more information, read the original error mentioned above or read the ovo owo --help")

    if ans is not None:
        print(json.dumps(ans))
    exit(0)

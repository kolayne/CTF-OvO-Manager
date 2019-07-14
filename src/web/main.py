#!/usr/bin/python3
import sys
import json
from os import path, _exit
from functools import wraps

import flask
import bcrypt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.append('../command_line')
from owo import add_file, add_user, add_comment, \
        rm_comment, mark_user, mark_task, \
        update_avatar, take_task, reject_task, \
        authorize
from common import get_db_connection, \
        assert_ok_dbname

game_id = None # Must be replaced when executing

app = flask.Flask(__name__)

def _parse_mysql_vomit(vomit:list) -> list:
    """Takes mysql's cursor's fetchall() result and returns it beautified
            if there was one field in SELECT, otherwise raises a ValueError
    Parameters:
        vomit(list[tuple[X]]): A mysql's cursor's fetchall() result
    Returns:
        list[X]: The beautified result as a map object (see examples below)
    Examples:
        list(_parse_mysql_vomit([(1,), (2,), ("x",)])) == [1, 2, "x"]
        list(_parse_mysql_vomit([(1, 2), (3, 4)])) -> ValueError
    """
    if not all(map(lambda x: len(x) == 1, vomit)):
        raise ValueError("Only one field must be requested in the sql query")
    return map(lambda x: x[0], vomit)

def get_user_info(user_id:str) -> dict:
    """Returns the user info like a dict
    Parameters:
        user_id(str): The user identifier
    Returns:
        dict: A dict with the following keys:
            login(str) - the user login
            is_captain(bool) - if the user is a captain
            avatar(str) - the avatar file id
            solving(list) - ids of tasks took by the user

    If the user doesn't exist, the returned dict will be:
        {'login': 'DELETED', 'is_captain': False, 'avatar': None,
        'solving': []}
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execue('SELECT is_admin, avatar FROM users WHERE login=(%s)',
            (user_id,))
    user_info = c.fetchone()
    if user_info is None:
        return {'login': 'DELETED', 'is_captain': False, 'avatar': None, 'solving': []}
    else:
        c.execute('SELECT task_id FROM solvings WHERE user_id=(%s)', (user_info['login'],))
        return {'login': user_id, 'is_captain': user_info[0], 'avatar': user_info[1],
                'solving': list(_parse_mysql_vomit(c.fetchall()))}

def get_task_info(task_id:str) -> dict:
    """Returns the task info like a dict
    Parameters:
        task_id(str): The task identifier
    Returns:
        dict: A dict with the following keys:
            id(str) - The task identifier
            name(str or NoneType) - The task name
            is_solved(bool) - If the task solved or not
            original_link(str or NoneType) - The link to the task on the main platform
            original_id(str or NoneType) - The task identifier on main platform
            text(str or NoneType) - The task text
            solvers(list) - ids of users, who took the task
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT * FROM tasks WHERE id=(%s)', (task_id,))
    ans = dict(zip(['id', 'name', 'is_solved', 'original_link', 'original_id', 'text'],
            c.fetchone()))
    ans['is_solved'] = True if ans['is_solved'] == 'Y' else False
    c.execute('SELECT user_id FROM solvings WHERE task_id=(%s)', (task_id,))
    ans['solvers'] = list(_parse_mysql_vomit(c.fetchall()))
    return ans

def get_comment_info(comment_id:str) -> dict:
    """Returns the comment info like a dict
    Parameters:
        comment_id(str): The comment identifier
    Returns:
        dict: A dict with the following keys:
            id(str) - The comment identifier
            task_id(str) - The identifier of the task the comment attached to
            user_id(str) - The comment's author identifier
            text(str or NoneType) - The comment text
            attached_files(list[str] or NoneType) - A list of ids of files attached to the comment
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT * FROM comments WHERE id=(%s)', (comment_id,))
    ans = dict(zip(['id', 'task_id', 'user_id', 'text', 'attached_files'], c.fetchall()))
    ans['attached_files'] = json.loads(ans['attached_files'])
    return ans

def get_game_info() -> dict:
    """Returns the game info as a dict
    Returns:
        dict: A dict with the following keys:
            port(int) - The network port to run web interface on
            files_folder(str) - A path to the folder for game files
            register_pass(str) - A password, required for registration (bcrypt)
            captain_pass(str) - A password, required for registering as
                a captain (bcrypt)
            judge_url(str or NoneType) - The main platform URL
            judge_login(str or NoneType) - A username for the main platform
            judge_pass(str or NoneType) - A password for the main platform
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT * FROM game_info')
    ans = dict(zip(['port', 'files_folder', 'register_pass', 'captain_pass', \
            'judge_url', 'judge_login', 'judge_pass'], c.fetchone()))
    return ans

def get_user_info_s(session_id:str) -> dict:
    """Returns the user info by his session id
    Parameters:
        session_id(str): The session identifier
    Returns:
        dict: User info (got from `get_user_info`)

    Raises ValueError if the session id doesn't exist
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT user_id FROM session_data WHERE session_id=(%s)',
            (session_id,))
    tmp = c.fetchone()
    if tmp is None:
        raise ValueError("Invalid session id")
    return get_user_info(tmp[0])

def assert_is_authorized(func):
    """A decorator for flask route functions.
        Interrupts with 403 status code if
        the request came from an unauthorized
        user
    """
    @wraps(func)
    def ans(*args, **kwargs):
        try:
            get_user_info_s(request.cookies['session_id'])
        except (IndexError, ValueError):
            return flask.abort(403)

        return func(*args, **kwargs)

    return ans

def check_given_params(required_params:set,
        all_params:set, given_params:set) -> bool:
    """Checks if all the required params where given
        and all the given params are valid
    Parameters:
        required_params(set): The set of params keys
            required for the method
        all_params(set): The set of valid params keys
            for the method
        given_params(set): The set of given params keys
    Returns:
        bool: True, if the given params are correct,
            otherwise False
    """
    if len(required_params.intersection(given_params)) < \
            len(required_params):
        return False
    if len(given_params - all_params) > 0:
        return False
    return True

def assert_ok_params(required:set, positional:set):
    """Returns a decorator for flask route functions.
        Interrupts with 400 status code if the request
        parameters are not correct
    Parameters:
        required(set): A set of parameters required for
            the api method
        positional(set): A set of poistional parameters for
            the api method

    The result function aborts if not all the required arguments
        were specified
    The result function aborts if unknown arguments were specified
    """
    def decorator(func):
        @wraps(func)
        def ans(*args, **kwargs):
            if check_given_params(
                    required,
                    required + positional,
                    set(flask.form.keys())
                    ):
                return func(*args, **kwargs)
            else:
                return flask.abort(400)

        return ans

    return decorator

# UI:
pass

# API:
# ------ BEGIN NON-CONST API METHODS ------
@app.route('/api/authorize', methods=['POST'])
@assert_ok_params({'login', 'password'}, set())
def web_authorize():
    try:
        session_id = authorize(game_id, **flask.request.form)
        resp = app.make_response(
                json.dumps(session_id)
                )
        resp.set_cookie('session_id', session_id)
        return resp
    except ValueError:
        return flask.abort(401)

@app.route('/api/add_file', methods=['POST'])
@assert_ok_params(set(), {'name'})
@assert_is_authorized
def web_add_file():
    if set(flask.request.files.keys()) != {'file'}:
        return flask.abort(400)
    f = flask.request.files[f]
    file_id = add_file(game_id, flask.request.form.get('name', f.filename), silent=True)
    f.save(path.join(get_game_info()['files_folder'], file_id))
    return json.dumps(file_id)

@app.route('/api/add_user', methods=['POST'])
@assert_ok_params({'login', 'password'},
        {'is_captain', 'avatar'})
def web_add_user():
    add_user(game_id, **flask.request.form)

@app.route('/api/add_comment', methods=['POST'])
@assert_ok_params({'task_id'}, {'text', 'files_ids'})
@assert_is_authorized
def web_add_comment():
    user_id = get_user_info_s(flask.cookies['session_id'])['login']
    return json.dumps(add_comment(game_id, user_id, **flask.request.form))

@app.route('/api/rm_comment', methods=['POST'])
@assert_ok_params({'id'}, set())
@assert_is_authorized
def web_rm_comment():
    user_info = get_user_info_s(flask.cookies['session_id'])
    comment_info = get_comment_info(flask.request.form['id'])
    if user_info['is_captain'] or (user_info['login'] == comment_info['user_id']):
        rm_comment(game_id, flask.request.form['id'])
    else:
        return flask.abort(403)

@app.route('/api/mark_user', methods=['POST'])
@assert_ok_params({'id', 'new_type'}, set())
@assert_is_authorized
def web_mark_user():
    if not get_user_info_s(flask.cookies['session_id'])['is_captain']:
        return flask.abort(403)
    mark_user(game_id, *(flask.request.form[i] for i in ['id', 'new_type']))

@app.route('/api/mark_task', methods=['POST'])
@assert_ok_params({'id', 'new_type'}, set())
@assert_is_authorized
def web_mark_task():
    mark_task(game_id, *(flask.request.form[i] for i in ['id', 'new_type']))

@app.route('/api/update_avatar', methods=['POST'])
@assert_ok_params({'user_id', 'avatar_file_id'}, set())
@assert_is_authorized
def web_update_avatar():
    if get_user_info_s(flask.cookies['session_id']) != flask.request.form['user_id']:
        return flask.abort(403)
    update_avatar(game_id, **flask.request.form)

@app.route('/api/take_task', methods=['POST'])
@assert_ok_params({'task_id', 'user_id'}, set())
@assert_is_authorized
def web_take_task():
    user_info = get_user_info_s(flask.cookies['session_id'])
    if user_info['is_captain'] or (user_info['login'] == flask.request.form['user_id']):
        take_task(game_id, **flask.request.form)
    else:
        return flask.abort(403)

@app.route('/api/reject_task', methods=['POST'])
@assert_ok_params({'task_id', 'user_id'}, set())
@assert_is_authorized
def web_reject_task():
    user_info = get_user_info_s(flask.cookies['session_id'])
    if user_info['is_captain'] or (user_info['login'] == flask.request.form['user_id']):
        reject_task(game_id, **flask.request.form)
    else:
        return flask.abort(403)
# ------ END NON-CONST API METHODS ------


def file_path_and_name(file_id:str) -> tuple:
    """Returns a path to the file and it's original name, if exists
    Parameters:
        file_id(str): The file identifier
    Returns:
        tuple: (path_to_file, original_filename) if the file exists, (None, None) otherwise
    """
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT name FROM files WHERE id=(%s)', (file_id,))
    name = c.fetchone()
    if name is None:
        return (None, None)
    else:
        return (path.join(get_game_info()['files_folder'], file_id), name)

# ------ BEGIN CONST API METHODS ------
@app.route('/api/get_file/<file_id>')
def web_get_file(file_id):
    path, name = file_path_and_name(file_id)
    if path is None:
        return flask.abort(404)
    return send_file(path)

@app.route('/api/download_file/<file_id>')
def web_download_file(file_id):
    path, name = file_path_and_name(file_id)
    if path is None:
        return flask.abort(404)
    return send_file(path, as_attachment=True, attachment_filename=name)

@app.route('/api/get_users')
def web_get_users():
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT login FROM users')
    return json.dumps(
            [get_user_info(uid) for uid in _parse_mysql_vomit(c.fetchall())]
            )

@app.route('/api/get_tasks')
def web_get_tasks():
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT id FROM tasks')
    return json.dumps(
            [get_task_info(tid) for tid in _parse_mysql_vomit(c.fetchall())]
            )

@app.route('/api/get_solvings')
def web_get_solvings():
    assert_ok_dbname(game_id)
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT * FROM solvings')
    return json.dumps(
            [dict(zip(['user_id', 'task_id'], i)) for i in c.fetchall()]
            )

@app.route('/api/get_files')
def web_get_files():
    assert_ok_dbname()
    db = get_db_connection()
    c = db.cursor()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT * FROM files')
    return json.dumps(
            [dict(zip(['id', 'name'], i)) for i in c.fetchall()]
            )
@app.route('/api/get_comments')
def web_get_comments():
    assert_ok_dbname()
    db = get_db_connection()
    c = db.connection()
    c.execute('USE OvO_' + game_id)
    c.execute('SELECT id FROM comments')
    return json.dumps(
            [get_comment_info(cid) for cid in _parse_mysql_vomit(c.fetchall())]
            )
# ------ END CONST API METHODS ------

class WaitForExit(FileSystemEventHandler):
    def on_created(self, event):
        if(not event.is_directory) and (event.src_path.split('/')[-1] == 'exit'):
            _exit(0)

if __name__ == "__main__":
    game_id = sys.argv[1]
    game_info = get_game_info()
    observer = Observer()
    observer.schedule(WaitForExit(), path=game_info['files_folder'])
    observer.start()
    app.run('0.0.0.0', port=game_info['port'])

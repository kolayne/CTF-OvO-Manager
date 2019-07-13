import sys
import json

import flask

sys.path.append('../command_line')
from owo import add_file, add_user, add_comment, \
        rm_task, rm_file, rm_comment, \
        mark_user, mark_task, update_avatar, \
        take_task, reject_task, authorize
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
                'solving': _parse_mysql_vomit(c.fetchall())}

def get_task_info(task_id:str) -> dict:
    """Returns the task info like a dict
    Parameters:
        task_id(str): The task identifier
    Returns:
        dict: A dict with the following keys:
            pass
    """
    pass

def get_comment_info(session_id:str) -> dict:
    pass

def get_file_name(file_id:str) -> str:
    pass

def get_game_info() -> str:
    pass

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

def assert_ok_params(func, required:set, positional:set):
    """A decorator for flask route functions.
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
    def ans(*args, **kwargs):
        if check_given_params(
                required,
                required + positional,
                set(flask.form.keys())
                ):
            return func(*args, **kwargs)
        else:
            return flask.abort(400)

# UI:
pass

# API:
@app.route('/api/authorize', methods=['POST'])
@assert_ok_params({'login', 'password'}, set())
def web_authorize():
    try:
        return json.dumps(authorize(game_id, **flask.request.form))
    except ValueError:
        return flask.abort(401)

@app.route('/api/add_file', methods=['POST'])
@assert_ok_params({'name'}, set())
@assert_is_authorized
def web_add_file():
    return json.dumps(add_file(game_id, **flask.request.form, silent=True))

@app.route('/api/add_user', methods=['POST'])
@assert_ok_params({'login', 'password'},
        {'is_captain', 'avatar'})
def web_add_user():
    add_user(game_id, **flask.request.form)

@app.route('/api/add_comment', methods=['POST'])
@assert_ok_params({'task_id'}, {'text', 'files_ids'})
@assert_is_authorized
def web_add_comment():
    user_id = get_user_info_s(flask.cookies['session_id'])
    return json.dumps(add_comment(game_id, user_id, **flask.request.form))

@app.route('/api/rm_task', methods=['POST'])
@assert_ok_params({'id'}, set())
@assert_is_authorized
def web_rm_task():
    pass

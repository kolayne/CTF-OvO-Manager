from os import listdir, path
from sys import stderr
from subprocess import run, PIPE
from importlib.machinery import SourceFileLoader
import json
import requests
from time import sleep

import bcrypt

common = SourceFileLoader('common', '../src/command_line/common.py').load_module()
from test_station import TestStation

def _run_and_check(cmd:list) -> str:
    """Runs a process and checks that the exit code is 0
    Parameters:
        cmd(list[str]): The command line redirected to subprocess
    Returns:
        str: The process' stdout
    """
    p = run(cmd, stdout=PIPE) # Can't redirect stderr to PIPE because of flask
    """p = run(cmd, stdout=PIPE, stderr=PIPE)
    if p.returncode != 0:
        print("Stdout:", p.stdout, file=stderr)
        print("Stderr:", p.stderr, file=stderr)"""
    assert(p.returncode == 0)
    return p.stdout

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

def dsorted(lod: list) -> list:
    """Sorts a list of dicts
    Parameters:
        lod(list[dict]): The list to be sorted
    Returns:
        list[dict]: Sorted list
    """
    return sorted(lod, key=lambda d: list(d.items()))

def test_run_stop_rerun_cleanup():
    game_id = 'TeSTing'
    common.assert_ok_dbname(game_id)
    db = common.get_db_connection(autocommit=True)
    c = db.cursor()
    
    _run_and_check(['../src/command_line/main.py', 'run', '--id', game_id, '--register-pass', '1', \
            '--captain-pass', '2', '--files-folder', './new', '--port', '5000'])
    assert('new' in listdir())
    assert('exit' not in listdir('new'))
    c.execute('USE OvO_' + game_id)
    c.execute('SHOW TABLES')
    assert(set(_parse_mysql_vomit(c.fetchall())) == {'users', 'tasks', 'solvings', \
            'files', 'comments', 'session_data', 'game_info'})
    c.execute('SELECT COUNT(*) FROM users')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM tasks')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM solvings')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM files')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM comments')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM session_data')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM game_info')
    assert(c.fetchone() == (1,))
    c.execute('SELECT port, files_folder, judge_url, judge_login, judge_pass FROM game_info')
    assert(c.fetchone() == (5000, path.abspath('./new'), None, None, None))
    c.execute('SELECT register_pass FROM game_info')
    assert(bcrypt.checkpw(
        b'1',
        c.fetchone()[0].encode('utf-8')
        ))
    c.execute('SELECT captain_pass FROM game_info')
    assert(bcrypt.checkpw(
        b'2',
        c.fetchone()[0].encode('utf-8')
        ))

    _run_and_check(['../src/command_line/main.py', 'stop', game_id])
    assert('exit' in listdir('new'))
    _run_and_check(['../src/command_line/main.py', 'rerun', '--id', game_id])
    assert('exit' not in listdir('new'))
    c.execute('SELECT COUNT(*) FROM users')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM tasks')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM solvings')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM files')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM comments')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM session_data')
    assert(c.fetchone() == (0,))
    c.execute('SELECT COUNT(*) FROM game_info')
    assert(c.fetchone() == (1,))

    c.execute('USE mysql') # Must do this, otherwise cleanup will freeze
    db.close()
    _run_and_check(['../src/command_line/main.py', 'cleanup', game_id])
    db = common.get_db_connection()
    c = db.cursor()
    assert('new' not in listdir())
    c.execute('SHOW DATABASES')
    assert('OvO_' + game_id not in _parse_mysql_vomit(c.fetchall()))

def test_owo():
    game_id = 'TeSTing'
    common.assert_ok_dbname(game_id)
    db = common.get_db_connection(autocommit=True)
    c = db.cursor()
    _run_and_check(['../src/command_line/main.py', 'run', '--id', 'TeSTing', '--register-pass', '1', \
            '--captain-pass', '1', '--files-folder', './new', '--port', '5000'])
    c.execute('USE OvO_' + game_id)
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'user', '--login', 'user1', \
            '--password', 'abcde'])
    fid0 = json.loads(
            _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'file', 'user2 avatar'])
            )
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'user', '--is-captain', \
            '--password', 'edcba', '--login', 'user2', '--avatar', fid0])
    fid1, fid2, fid3 = (json.loads(
        _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'file', str(i)])
            ) for i in range(1, 4))
    tid = json.loads(
        _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'task', '--text', '*empty*', \
            '--original-link', 'http://google.com', '--name', 'First task'])
        )
    c.execute('SELECT * FROM tasks')
    assert(c.fetchall() == [(tid, 'First task', 'N', 'http://google.com', None, '*empty*')])
    cid1 = json.loads(
        _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'comment', '--task-id', tid, \
                '--user-id', 'user1', '--text', '*empty*'])
        )
    cid2 = json.loads(
        _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'comment', '--user-id', 'user1', \
                '--text', 'one file', '--task-id', tid, '--file-id', fid1])
        )
    cid3 = json.loads(
        _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'comment', '--file-id', fid2, \
                '--text', 'two files', '--user-id', 'user2', '--file-id', fid3, '--task-id', tid])
        )
    c.execute('SELECT login, is_captain, avatar FROM users')
    assert(set(c.fetchall()) == {('user1', 'N', None), ('user2', 'Y', fid0)})
    c.execute('SELECT password FROM users')
    assert(bcrypt.checkpw(b'abcde', c.fetchone()[0].encode('utf-8')))
    assert(bcrypt.checkpw(b'edcba', c.fetchone()[0].encode('utf-8')))
    c.execute('SELECT * FROM tasks')
    assert(set(c.fetchall()) == {(tid, 'First task', 'N', 'http://google.com', None, '*empty*')})
    c.execute('SELECT * FROM solvings')
    assert(set(c.fetchall()) == set())
    c.execute('SELECT * FROM files')
    assert(set(c.fetchall()) == {(fid0, 'user2 avatar'), (fid1, '1'), (fid2, '2'), (fid3, '3')})
    c.execute('SELECT * FROM comments')
    assert(set(c.fetchall()) == {(cid1, tid, 'user1', '*empty*', json.dumps([])),
        (cid2, tid, 'user1', 'one file', json.dumps([fid1])),
        (cid3, tid, 'user2', 'two files', json.dumps([fid2, fid3]))
        })
    c.execute('SELECT COUNT(*) FROM session_data')
    assert(c.fetchone() == (0,))
    
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'user', 'user1', 'default'])
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'user', 'user1', 'captain'])
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'user', 'user2', 'captain'])
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'user', 'user2', 'default'])
    c.execute('SELECT is_captain FROM users ORDER BY login')
    assert(list(_parse_mysql_vomit(c.fetchall())) == ['Y', 'N'])
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'task', tid, 'unsolved'])
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'mark', 'task', tid, 'solved'])
    c.execute('SELECT is_solved FROM tasks')
    assert(c.fetchall() == [('Y',)])

    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'update_avatar', 'user1', fid2])
    c.execute('SELECT avatar FROM users ORDER BY login')
    assert(set(_parse_mysql_vomit(c.fetchall())) == {fid0, fid2})

    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'take_task', '--user-id', 'user1', \
            '--task-id', tid])
    c.execute('SELECT * FROM solvings')
    assert(set(c.fetchall()) == {('user1', tid)})
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'take_task', '--task-id', tid, \
            '--user-id', 'user2'])
    c.execute('SELECT * FROM solvings')
    assert(set(c.fetchall()) == {('user1', tid), ('user2', tid)})
    _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'reject_task', '--task-id', tid, \
            '--user-id', 'user1'])
    c.execute('SELECT * FROM solvings')
    assert(set(c.fetchall()) == {('user2', tid)})

    for entity, entity_id in zip(['user', 'comment', 'task', 'file'], ['user2', cid3, tid, fid0]):
        query = 'SELECT COUNT(*) FROM {}s'.format(entity)
        c.execute(query)
        before, = c.fetchone()
        ans = _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'rm', entity, entity_id])
        if entity_id == 'user1':
            assert(json.loads(ans) == fid0)
        elif entity_id == cid3:
            assert(json.loads(ans) == [fid2, fid3])
        elif entity_id == tid:
            assert(json.loads(ans) == [fid1]) # Because fid2 and fid3 will be remove before this moment
        c.execute(query)
        after, = c.fetchone()
        assert(before - after == 1)

    db.close()
    _run_and_check(['../src/command_line/main.py', 'cleanup', game_id])

def test_web_api():
    game_id = 'TeSTing'
    host = 'http://localhost:5000'
    _run_and_check(['../src/command_line/main.py', 'run', '--id', 'TeSTing', '--register-pass', '1', \
            '--captain-pass', '1', '--files-folder', './new', '--port', '5000'])
    r = requests.post(host + '/api/add_user', data={'login': 'user1', 'password': 'abcde', \
            'register_pass': '1'})
    assert(r.status_code == 200)
    r = requests.post(host + '/api/authorize', data={'login': 'user1', 'password': 'abcde'})
    assert(r.status_code == 200)
    cookies1 = r.cookies
    r = requests.post(host + '/api/add_file', data={'name': 'user 2 avatar'}, files={'file': \
            open(__file__, 'rb')}, cookies=cookies1)
    assert(r.status_code == 200)
    fid0 = r.json()
    r = requests.post(host + '/api/add_user', data={'password': 'edcba', 'login': 'user2', \
            'avatar': fid0, 'register_pass': '1', 'captain_pass': '1'})
    assert(r.status_code == 200)
    r = requests.post(host + '/api/authorize', data={'login': 'user2', 'password': 'edcba'})
    assert(r.status_code == 200)
    cookies2 = r.cookies
    fid1, fid2, fid3 = (requests.post(host + '/api/add_file', data={'name': str(i)}, files={'file': \
            open(__file__, 'rb')}, cookies=cookies2).json() for i in range(1, 4))
    tid = json.loads(
            _run_and_check(['../src/command_line/main.py', 'owo', game_id, 'add', 'task', '--text', '*empty*', \
                    '--original-link', 'http://google.com', '--name', 'First task'])
            )
    r = requests.get(host + '/api/get_tasks', cookies=cookies1)
    assert(r.status_code == 200)
    assert(len(r.json()) == 1)
    assert(r.json()[0] == {'id': tid, 'name': 'First task', 'is_solved': False, 'original_link': \
            'http://google.com', 'original_id': None, 'text': '*empty*', 'solvers': []})
    r = requests.post(host + '/api/add_comment', data={'task_id': tid, 'text': '*empty*'}, \
            cookies=cookies1)
    assert(r.status_code == 200)
    cid1 = r.json()
    # Checking can specify file id as a string:
    r = requests.post(host + '/api/add_comment', data={'text': 'one file', 'files_ids': fid1, \
            'task_id': tid}, cookies=cookies1) 
    assert(r.status_code == 200)
    cid2 = r.json()
    # Checking can specify files ids as a list
    r = requests.post(host + '/api/add_comment', data={'text': 'two files', 'files_ids': [fid2, fid3], \
            'task_id': tid}, cookies=cookies2)
    assert(r.status_code == 200)
    cid3 = r.json()
    r = requests.get(host + '/api/get_users', cookies=cookies2)
    assert(r.status_code == 200)
    assert(dsorted(r.json()) == dsorted([{'login': 'user1', 'is_captain': False, \
            'avatar': None, 'solving': []}, {'login': 'user2', 'is_captain': True, 'avatar': fid0, 'solving': []}]))
    r = requests.get(host + '/api/get_solvings', cookies=cookies1)
    assert(r.status_code == 200)
    assert(r.json() == [])
    r = requests.get(host + '/api/get_files', cookies=cookies2)
    assert(r.status_code == 200)
    assert(dsorted(r.json()) == dsorted([{'id': fid0, 'name': 'user 2 avatar'}, \
            {'id': fid1, 'name': '1'}, {'id': fid2, 'name': '2'}, {'id': fid3, 'name': '3'}]))
    r = requests.get(host + '/api/get_files', cookies=cookies1)
    assert(r.status_code == 200)
    assert(len(r.json()) == 4)
    for file_info in r.json():
        raw = open(__file__, 'rb').read()
        r = requests.get(host + '/api/get_file/' + file_info['id'], cookies=cookies2)
        assert(r.status_code == 200)
        assert(r.content == raw)
        r = requests.get(host + '/api/download_file/' + file_info['id'], cookies=cookies1)
        assert(r.status_code == 200)
        assert(r.content == raw)
    r = requests.get(host + '/api/get_comments', cookies=cookies2)
    assert(r.status_code == 200)
    assert(dsorted(r.json()) == dsorted([{'id': cid1, 'task_id': tid, 'user_id': 'user1', \
            'text': '*empty*', 'attached_files': []}, {'id': cid2, 'task_id': tid, 'user_id': 'user1', \
            'text': 'one file', 'attached_files': [fid1]}, {'id': cid3, 'task_id': tid, 'user_id': 'user2', \
            'text': 'two files', 'attached_files': [fid2, fid3]}]))
    r = requests.post(host + '/api/mark_user', data={'login': 'user1', 'new_type': 'default'}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.post(host + '/api/mark_user', data={'login': 'user1', 'new_type': 'captain'}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.post(host + '/api/mark_user', data={'login': 'user2', 'new_type': 'captain'}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.post(host + '/api/mark_user', data={'login': 'user2', 'new_type': 'default'}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.get(host + '/api/get_user_info/user1', cookies=cookies2)
    assert(r.status_code == 200)
    assert(r.json()['is_captain'])
    r = requests.get(host + '/api/get_user_info/user2', cookies=cookies1)
    assert(r.status_code == 200)
    assert(not r.json()['is_captain'])
    r = requests.post(host + '/api/mark_task', data={'id': tid, 'new_type': 'unsolved'}, \
            cookies=cookies1)
    assert(r.status_code == 200)
    r = requests.post(host + '/api/mark_task', data={'id': tid, 'new_type': 'solved'}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.get(host + '/api/get_task_info/' + tid, cookies=cookies1)
    assert(r.status_code == 200)
    assert(r.json()['is_solved'])
    r = requests.post(host + '/api/update_avatar', data={'avatar': fid2}, cookies=cookies1)
    assert(r.status_code == 200)
    r = requests.get(host + '/api/get_user_info/user1', cookies=cookies2)
    assert(r.status_code == 200)
    assert(r.json()['avatar'] == fid2)
    r = requests.get(host + '/api/get_comment_info/' + cid1, cookies=cookies1)
    assert(r.status_code == 200)
    assert(r.json() == {'id': cid1, 'task_id': tid, 'user_id': 'user1', 'text': '*empty*', \
            'attached_files': []})
    r = requests.post(host + '/api/take_task', data={'user_id': 'user1', 'task_id': tid}, \
            cookies=cookies1)
    assert(r.status_code == 200)
    r = requests.get(host + '/api/get_task_info/' + tid, cookies=cookies2)
    assert(r.status_code == 200)
    assert(r.json()['solvers'] == ['user1'])
    r = requests.post(host + '/api/take_task', data={'user_id': 'user2', 'task_id': tid}, \
            cookies=cookies2)
    assert(r.status_code == 200)
    r = requests.post(host + '/api/reject_task', data={'user_id': 'user1', 'task_id': tid}, \
            cookies=cookies1)
    assert(r.status_code == 200)
    r = requests.get(host + '/api/get_user_info/user2', cookies=cookies2)
    assert(r.status_code == 200)
    assert(r.json()['solving'] == [tid])
    r = requests.post(host + '/api/rm_comment', data={'id': cid3}, \
            cookies=cookies1)
    assert(r.status_code == 200)
    assert(sorted(r.json()) == sorted([fid2, fid3]))
    r = requests.get(host + '/api/get_comments', cookies=cookies2)
    assert(r.status_code == 200)
    assert(len(r.json()) == 2)
    assert(all(i['id'] in [cid1, cid2] for i in r.json()))
    _run_and_check(['../src/command_line/main.py', 'cleanup', game_id])

if __name__ == "__main__":
    ts = TestStation()
    ts.add_test(test_run_stop_rerun_cleanup)
    ts.add_test(test_owo)
    ts.add_test(test_web_api)
    ts.run_tests()
    exit(0)

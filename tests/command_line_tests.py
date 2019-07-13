from os import listdir, path
from sys import stderr
from subprocess import run, PIPE
from importlib.machinery import SourceFileLoader
import json

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
    p = run(cmd, stdout=PIPE, stderr=PIPE)
    if(p.returncode):
        print("Stdout:", p.stdout, file=stderr)
        print("Stderr:", p.stderr, file=stderr)
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
    c.execute('SELECT * FROM game_info')
    assert(c.fetchone() == (5000, path.abspath('./new'), '1', '2', None, None, None, '0'))

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
                '--user-id', 'user1', '--text', 'comment text'])
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
    assert(set(c.fetchall()) == {(cid1, tid, 'user1', 'comment text', json.dumps([])),
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

if __name__ == "__main__":
    ts = TestStation()
    ts.add_test(test_run_stop_rerun_cleanup)
    ts.add_test(test_owo)
    ts.run_tests()
    exit(0)

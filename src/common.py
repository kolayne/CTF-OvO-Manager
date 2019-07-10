from sys import stderr

from configparser import ConfigParser
import mysql.connector

def is_help_request(l:list) -> bool:
    """Function for checking if the given argv is a help request
    Parameters:
        l(list): Arguments list
    Returns:
        bool: True, if l is a help request, othewise False
    """
    return (len(l) == 2) and (l[1] in ['-h', '--help'])

def _load_mysql_auth_data() -> tuple:
    """Extracts mysql username and password from the conf file
    Returns:
        tuple: (username, password)
    """
    config = ConfigParser()
    config.read('/etc/ovo.conf')
    return (config['mysql']['username'],
            config['mysql']['password'])

def get_db_connection():
    mysql_username, mysql_password = _load_mysql_auth_data()
    return mysql.connector.connect(
            host='localhost',
            user=mysql_username,
            passwd=mysql_password
            )

def assert_ok_dbname(dbname:str):
    """Function for checking if dbname is an ok name for db
    Parameters:
        dbname(str): The name to be checked
    
    Throws ValueError if dbname is not a correct name for db
    """
    if(not all(map(lambda x: x.isalpha() or x.isdigit() or x == '_', dbname))):
        raise ValueError("The identificator can only contain letters, digits, or _ symbols")

if __name__ == "__main__":
    print("It's forbidden to run this file", file=stderr)
    exit(1)

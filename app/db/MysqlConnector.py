import pymysql
import pymysql.cursors

from host_data import DATABASE_HOST, DATABASE_PASSWORD, DATABASE_NAME, DATABASE_USER

class MysqlConnector():
    CURSOR_DEFAULT = pymysql.cursors.Cursor
    CURSOR_DICTIONARY = pymysql.cursors.DictCursor
    """ CURSOR_VARIANTS = {
        'default': pymysql.cursors.Cursor,
        'dictionary': pymysql.cursors.DictCursor,
    } """

    def __init__(self) -> None:
        self.connection = pymysql.connect(host=DATABASE_HOST, user=DATABASE_USER, passwd=DATABASE_PASSWORD, database=DATABASE_NAME)

    def get_cursor(self, cursor_type):
        if cursor_type is None:
            cursor_type = self.CURSOR_DEFAULT
        
        return self.connection.cursor(cursor=cursor_type)
        

    def close(self) -> None:
        try:
            self.connection.close()
        except:
            pass
from app.db.MysqlConnector import MysqlConnector

class StudentRepo:

    def __init__(self) -> None:
        self.db = MysqlConnector()

    def __del__(self):
        self.db.close()

    def get_student_by_serial_code(self, serial_code):
        cursor = self.db.get_cursor(MysqlConnector.CURSOR_DICTIONARY)

        cursor.execute("SELECT * FROM student WHERE ser_nomer = (%s) ", (serial_code))
        student = cursor.fetchall()
        self.db.close()

        if student == ():
            return None

        return student[0]
    
    def get_by_filters(self, date, student_id):
        cursor = cursor = self.db.get_cursor(MysqlConnector.CURSOR_DICTIONARY)

        cursor.execute("SELECT * FROM stud_access WHERE date = (%s) AND id_stud = (%s) ", (date, student_id))
        students = cursor.fetchall()
        self.db.close()

        if students == ():
            return None

        return students
from app.services.student.StudentRepo import StudentRepo

class StudentService:

    def __init__(self) -> None:
        self.repo = StudentRepo()
    
    def get_student_by_serial_code(self, serial_code):
        return self.repo.get_student_by_serial_code(serial_code=serial_code)
    def get_student_by_filters(self, date, student_id):
        return self.repo.get_by_filters(date=date, student_id=student_id)
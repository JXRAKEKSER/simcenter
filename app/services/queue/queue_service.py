class QueueService:


    def __init__(self) -> None:
        self.queue = {}

    def add_to_queue(self, student):
        target_room_queue = self.queue.get(student['room_number'])
        if target_room_queue is None:
            self.queue[student['room_number']] = [student]
            return
        
        self.queue[student['room_number']].append(student)

queueService = QueueService()


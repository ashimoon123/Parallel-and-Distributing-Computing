import queue
import logging

class TaskManager:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.active_tasks = {}
        
    def add_task(self, client_socket, task_id, filepath, config):
        task = {
            "task_id": task_id,
            "client_socket": client_socket,
            "filepath": filepath,
            "config": config,
            "status": "queued"
        }
        self.active_tasks[task_id] = task
        self.task_queue.put(task)
        logging.info(f"Task {task_id} added to queue. Queue size: {self.task_queue.qsize()}")
        
    def get_task(self):
        try:
            return self.task_queue.get(timeout=1)
        except queue.Empty:
            return None
            
    def mark_completed(self, task_id, output_path=None, error=None):
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if error:
                task["status"] = "failed"
                task["error"] = error
            else:
                task["status"] = "completed"
                task["output_path"] = output_path
            
            self.task_queue.task_done()

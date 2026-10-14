"""Excepciones de dominio, independientes de HTTP."""
from uuid import UUID


class TaskNotFoundError(Exception):
    def __init__(self, task_id: UUID):
        self.task_id = task_id
        super().__init__(f"No existe una tarea con id {task_id}.")

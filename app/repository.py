"""Almacenamiento en memoria (primera versión, sin base de datos)."""
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID

from app.models import Task


class InMemoryTaskRepository:
    """Repositorio simple y seguro entre hilos. Reemplazable por una BD real
    manteniendo la misma interfaz (add, get, update, list_all)."""

    def __init__(self) -> None:
        self._tasks: Dict[UUID, Task] = {}
        self._lock = Lock()

    def add(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: UUID) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.id] = task
        return task

    def list_all(self) -> List[Task]:
        with self._lock:
            return list(self._tasks.values())

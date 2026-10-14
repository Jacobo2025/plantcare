"""Lógica de negocio del calendario de cuidados."""
from datetime import date, datetime, timedelta, timezone
from typing import Callable, List, Optional
from uuid import UUID, uuid4

from app.exceptions import TaskNotFoundError
from app.models import (
    ReminderResponse,
    Task,
    TaskCreate,
    TaskResponse,
    TaskStatus,
)
from app.repository import InMemoryTaskRepository


class CareCalendarService:
    """Registra, consulta y completa tareas de cuidado de plantas.

    Args:
        repository: almacenamiento de tareas.
        today_provider: función que devuelve la fecha actual (inyectable
            para poder probar la lógica de vencimiento con fechas fijas).
    """

    def __init__(
        self,
        repository: Optional[InMemoryTaskRepository] = None,
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        self._repository = repository or InMemoryTaskRepository()
        self._today = today_provider

    # ---- Cálculo de estado (reglas 3, 4 y 5) ----------------------------
    def compute_status(self, task: Task) -> TaskStatus:
        if task.is_completed:
            return TaskStatus.COMPLETED
        if task.scheduled_date < self._today():
            return TaskStatus.OVERDUE
        return TaskStatus.PENDING

    def _to_response(self, task: Task) -> TaskResponse:
        return TaskResponse(**task.model_dump(), status=self.compute_status(task))

    # ---- Casos de uso -----------------------------------------------------
    def create_task(self, data: TaskCreate) -> TaskResponse:
        """Registra una tarea nueva. Los datos ya vienen validados por Pydantic."""
        task = Task(
            id=uuid4(),
            plant_name=data.plant_name,
            care_type=data.care_type,
            scheduled_date=data.scheduled_date,
            description=data.description,
            created_at=datetime.now(timezone.utc),
        )
        self._repository.add(task)
        return self._to_response(task)

    def get_task(self, task_id: UUID) -> TaskResponse:
        return self._to_response(self._get_or_raise(task_id))

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        plant_name: Optional[str] = None,
    ) -> List[TaskResponse]:
        """Lista el calendario ordenado por fecha, con filtros opcionales."""
        tasks = sorted(
            self._repository.list_all(),
            key=lambda t: (t.scheduled_date, t.created_at),
        )
        responses = [self._to_response(t) for t in tasks]
        if status is not None:
            responses = [r for r in responses if r.status == status]
        if plant_name:
            needle = plant_name.strip().lower()
            responses = [r for r in responses if r.plant_name.lower() == needle]
        return responses

    def complete_task(self, task_id: UUID) -> TaskResponse:
        """Marca la tarea como completada. Es idempotente: completar de nuevo
        conserva la fecha de la primera finalización."""
        task = self._get_or_raise(task_id)
        if not task.is_completed:
            task = task.model_copy(update={"completed_at": datetime.now(timezone.utc)})
            self._repository.update(task)
        return self._to_response(task)

    def list_reminders(self, days_ahead: int = 7) -> List[ReminderResponse]:
        """Tareas no completadas vencidas o que vencen en los próximos
        `days_ahead` días, de la más urgente a la menos urgente."""
        today = self._today()
        limit = today + timedelta(days=days_ahead)
        reminders = []
        for task in sorted(self._repository.list_all(), key=lambda t: t.scheduled_date):
            if task.is_completed or task.scheduled_date > limit:
                continue
            reminders.append(
                ReminderResponse(
                    **self._to_response(task).model_dump(),
                    days_until_due=(task.scheduled_date - today).days,
                )
            )
        return reminders

    # ---- Internos ---------------------------------------------------------
    def _get_or_raise(self, task_id: UUID) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

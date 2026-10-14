"""Pruebas unitarias de la lógica de negocio (sin HTTP)."""
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.exceptions import TaskNotFoundError
from app.models import CareType, TaskCreate, TaskStatus
from app.service import CareCalendarService

TODAY = date(2025, 6, 15)


@pytest.fixture
def service():
    return CareCalendarService(today_provider=lambda: TODAY)


def make(scheduled: date, plant="Monstera", care="riego"):
    return TaskCreate(plant_name=plant, care_type=care, scheduled_date=scheduled)


# --- Criterios de aceptación -------------------------------------------------
def test_valid_task_is_registered_as_pending(service):
    task = service.create_task(make(date(2025, 6, 20)))
    assert task.status == TaskStatus.PENDING
    assert service.get_task(task.id).plant_name == "Monstera"


def test_uncompleted_past_task_is_overdue(service):
    task = service.create_task(make(date(2025, 6, 14)))
    assert task.status == TaskStatus.OVERDUE
    assert service.list_tasks()[0].status == TaskStatus.OVERDUE


def test_completed_task_keeps_status_when_queried_again(service):
    task = service.create_task(make(date(2025, 6, 1)))  # ya vencida
    service.complete_task(task.id)
    assert service.get_task(task.id).status == TaskStatus.COMPLETED
    assert service.list_tasks()[0].status == TaskStatus.COMPLETED


# --- Reglas de negocio ---------------------------------------------------------
def test_task_due_today_is_pending(service):
    assert service.create_task(make(TODAY)).status == TaskStatus.PENDING


def test_complete_is_idempotent(service):
    task = service.create_task(make(TODAY))
    first = service.complete_task(task.id)
    second = service.complete_task(task.id)
    assert first.completed_at == second.completed_at


def test_complete_unknown_task_raises(service):
    with pytest.raises(TaskNotFoundError):
        service.complete_task(uuid4())


def test_filter_by_status_and_plant(service):
    service.create_task(make(date(2025, 6, 1), plant="Helecho"))
    service.create_task(make(date(2025, 7, 1), plant="Monstera"))
    assert len(service.list_tasks(status=TaskStatus.OVERDUE)) == 1
    assert service.list_tasks(plant_name="monstera")[0].plant_name == "Monstera"


def test_reminders_include_overdue_and_upcoming_only(service):
    service.create_task(make(date(2025, 6, 10)))              # vencida
    service.create_task(make(date(2025, 6, 18)))              # próxima
    service.create_task(make(date(2025, 8, 1)))               # lejana
    done = service.create_task(make(date(2025, 6, 16)))
    service.complete_task(done.id)                             # completada
    reminders = service.list_reminders(days_ahead=7)
    assert [r.days_until_due for r in reminders] == [-5, 3]


# --- Validaciones ----------------------------------------------------------------
@pytest.mark.parametrize("plant", ["", "   "])
def test_blank_plant_name_is_rejected(plant):
    with pytest.raises(ValidationError):
        make(TODAY, plant=plant)


def test_invalid_care_type_is_rejected():
    with pytest.raises(ValidationError):
        make(TODAY, care="fumigacion")


def test_missing_date_is_rejected():
    with pytest.raises(ValidationError):
        TaskCreate(plant_name="Ficus", care_type="poda")


def test_care_type_accepts_accents_and_case():
    assert make(TODAY, care="Fertilización").care_type == CareType.FERTILIZING

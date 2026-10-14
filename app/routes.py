"""Endpoints HTTP. Solo traducen HTTP <-> servicio; no contienen reglas de negocio."""
from functools import lru_cache
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.exceptions import TaskNotFoundError
from app.models import ReminderResponse, TaskCreate, TaskResponse, TaskStatus
from app.service import CareCalendarService

router = APIRouter()


@lru_cache
def get_service() -> CareCalendarService:
    """Instancia única del servicio (el almacenamiento vive en memoria)."""
    return CareCalendarService()


ServiceDep = Depends(get_service)


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar una tarea de cuidado")
def create_task(data: TaskCreate, service: CareCalendarService = ServiceDep):
    return service.create_task(data)


@router.get("/tasks", response_model=List[TaskResponse],
            summary="Consultar el calendario de cuidados")
def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filtrar por estado."),
    plant_name: Optional[str] = Query(None, description="Filtrar por planta."),
    service: CareCalendarService = ServiceDep,
):
    return service.list_tasks(status=status, plant_name=plant_name)


@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="Consultar una tarea")
def get_task(task_id: UUID, service: CareCalendarService = ServiceDep):
    try:
        return service.get_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse,
             summary="Marcar una tarea como completada")
def complete_task(task_id: UUID, service: CareCalendarService = ServiceDep):
    try:
        return service.complete_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/reminders", response_model=List[ReminderResponse],
            summary="Listar recordatorios (vencidas y próximas)")
def list_reminders(
    days_ahead: int = Query(7, ge=0, le=365, description="Días hacia adelante a incluir."),
    service: CareCalendarService = ServiceDep,
):
    return service.list_reminders(days_ahead=days_ahead)

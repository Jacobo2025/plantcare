"""Modelos de datos: enumeraciones, esquemas de entrada/salida y entidad interna."""
import unicodedata
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


class CareType(str, Enum):
    """Tipos de cuidado permitidos (regla de negocio 1)."""

    WATERING = "riego"
    FERTILIZING = "fertilizacion"
    PRUNING = "poda"


class TaskStatus(str, Enum):
    """Estados posibles de una tarea."""

    PENDING = "pendiente"
    OVERDUE = "vencida"
    COMPLETED = "completada"


PlantName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class TaskCreate(BaseModel):
    """Datos de entrada para registrar una tarea de cuidado."""

    plant_name: PlantName = Field(description="Nombre de la planta (obligatorio).")
    care_type: CareType = Field(description="riego, fertilizacion o poda.")
    scheduled_date: date = Field(description="Fecha programada (YYYY-MM-DD, obligatoria).")
    description: Optional[str] = Field(default=None, max_length=500)

    @field_validator("care_type", mode="before")
    @classmethod
    def _normalize_care_type(cls, value):
        """Acepta mayúsculas y tildes: 'Fertilización' -> 'fertilizacion'."""
        if isinstance(value, str):
            decomposed = unicodedata.normalize("NFD", value.strip().lower())
            return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        return value

    @field_validator("description")
    @classmethod
    def _blank_description_to_none(cls, value):
        if value is not None:
            value = value.strip()
        return value or None


class Task(BaseModel):
    """Entidad interna almacenada. El estado 'vencida' NO se guarda: se calcula."""

    id: UUID
    plant_name: str
    care_type: CareType
    scheduled_date: date
    description: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None


class TaskResponse(BaseModel):
    """Representación pública de una tarea, con su estado calculado."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plant_name: str
    care_type: CareType
    scheduled_date: date
    description: Optional[str] = None
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None


class ReminderResponse(TaskResponse):
    """Recordatorio: tarea con los días que faltan (negativo si ya venció)."""

    days_until_due: int

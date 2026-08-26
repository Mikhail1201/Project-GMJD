from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class IncidenteAmbiental(ModeloBase):
    id_incidente: int | None = None
    id_area: int | None = None
    id_alerta: int | None = None
    titulo: str | None = None
    descripcion: str | None = None
    fecha_inicio: Any = None
    fecha_fin: Any = None
    severidad: str | None = None
    causa: str | None = None
    acciones_realizadas: str | None = None
    id_estado: int | None = None
    responsable_id: int | None = None
    nombre_area: str | None = None
    nombre_responsable: str | None = None

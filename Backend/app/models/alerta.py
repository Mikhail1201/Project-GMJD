from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class Alerta(ModeloBase):
    id_alerta: int | None = None
    id_medicion: int | None = None
    id_area: int | None = None
    tipo_alerta: str | None = None
    nivel: str | None = None
    descripcion: str | None = None
    fecha_hora: Any = None
    id_estado: int | None = None
    atendida_por: int | None = None
    fecha_atencion: Any = None
    nombre_area: str | None = None
    nombre_atendio: str | None = None

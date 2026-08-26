from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class Mantenimiento(ModeloBase):
    id_mantenimiento: int | None = None
    id_area: int | None = None
    tipo: str | None = None
    descripcion: str | None = None
    fecha: Any = None
    responsable_id: int | None = None
    resultado: str | None = None
    proximo_mantenimiento: Any = None

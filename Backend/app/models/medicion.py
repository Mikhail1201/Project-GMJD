from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class Medicion(ModeloBase):
    id_medicion: int | None = None
    id_area: int | None = None
    id_parametro: int | None = None
    valor: Any = None
    fecha_hora: Any = None
    calidad_dato: str | None = None
    observacion: str | None = None

from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class ParametroAmbiental(ModeloBase):
    id_parametro: int | None = None
    nombre: str | None = None
    unidad: str | None = None
    descripcion: str | None = None
    limite_minimo: Any = None
    limite_maximo: Any = None
    nivel_riesgo: str | None = None

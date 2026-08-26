from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class LimiteAmbiental(ModeloBase):
    id_limite: int | None = None
    id_parametro: int | None = None
    id_area: int | None = None
    limite_minimo: Any = None
    limite_maximo: Any = None
    unidad: str | None = None
    fecha_inicio: Any = None
    fecha_fin: Any = None
    fuente_normativa: str | None = None

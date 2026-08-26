from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class PrediccionIA(ModeloBase):
    id_prediccion: int | None = None
    id_modelo: int | None = None
    id_area: int | None = None
    id_parametro: int | None = None
    fecha_prediccion: Any = None
    periodo_predicho: Any = None
    valor_predicho: Any = None
    nivel_riesgo: str | None = None
    probabilidad: Any = None
    recomendacion: str | None = None

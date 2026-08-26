from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class ModeloIA(ModeloBase):
    id_modelo: int | None = None
    nombre: str | None = None
    version: str | None = None
    tipo_modelo: str | None = None
    descripcion: str | None = None
    fecha_entrenamiento: Any = None
    precision_modelo: Any = None
    id_estado: int | None = None

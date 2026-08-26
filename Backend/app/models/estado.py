from dataclasses import dataclass

from app.models.base import ModeloBase


@dataclass
class Estado(ModeloBase):
    id_estado: int | None = None
    nombre: str | None = None

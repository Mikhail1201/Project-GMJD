from dataclasses import dataclass

from app.models.base import ModeloBase


@dataclass
class Rol(ModeloBase):
    id_rol: int | None = None
    nombre: str | None = None

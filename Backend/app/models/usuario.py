from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class Usuario(ModeloBase):
    id_usuario: int | None = None
    nombre: str | None = None
    apellido: str | None = None
    correo: str | None = None
    id_rol: int | None = None
    id_estado: int | None = None
    fecha_registro: Any = None
    auth_user_id: str | None = None

from dataclasses import dataclass

from app.models.base import ModeloBase


@dataclass
class Area(ModeloBase):
    id_area: int | None = None
    nombre: str | None = None
    descripcion: str | None = None
    ubicacion: str | None = None
    responsable_id: int | None = None
    id_estado: int | None = None
    responsable_nombre: str | None = None
    responsable_apellido: str | None = None

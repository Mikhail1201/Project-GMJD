from dataclasses import dataclass
from typing import Any

from app.models.base import ModeloBase


@dataclass
class Sensor(ModeloBase):
    id_sensor: int | None = None
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    id_area: int | None = None
    id_parametro: int | None = None
    ubicacion_detalle: str | None = None
    modelo: str | None = None
    fabricante: str | None = None
    numero_serie: str | None = None
    protocolo: str | None = None
    rango_minimo: Any = None
    rango_maximo: Any = None
    precision_sensor: Any = None
    frecuencia_muestreo_seg: int | None = None
    fecha_instalacion: Any = None
    fecha_ultima_calibracion: Any = None
    fecha_proxima_calibracion: Any = None
    es_principal: bool | None = None
    responsable_id: int | None = None
    id_estado: int | None = None
    # Campos que llegan de los JOIN del repositorio (no son columnas de la tabla)
    nombre_area: str | None = None
    nombre_parametro: str | None = None
    unidad_parametro: str | None = None
    nombre_responsable: str | None = None
    nombre_estado: str | None = None

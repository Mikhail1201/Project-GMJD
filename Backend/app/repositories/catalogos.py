from functools import lru_cache

from sqlalchemy import text

from app.core.database import engine


@lru_cache(maxsize=None)
def obtener_id_estado(nombre: str) -> int:
    query = text("SELECT id_estado FROM estados WHERE nombre = :nombre")
    with engine.connect() as con:
        fila = con.execute(query, {"nombre": nombre}).first()

    if fila is None:
        raise ValueError(f"El estado '{nombre}' no existe en la tabla estados")

    return fila[0]


@lru_cache(maxsize=None)
def obtener_id_rol(nombre: str) -> int:
    query = text("SELECT id_rol FROM roles WHERE nombre = :nombre")
    with engine.connect() as con:
        fila = con.execute(query, {"nombre": nombre}).first()

    if fila is None:
        raise ValueError(f"El rol '{nombre}' no existe en la tabla roles")

    return fila[0]

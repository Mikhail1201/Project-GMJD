from functools import lru_cache
from sqlalchemy import text

from extensions import engine


@lru_cache(maxsize=None)
def obtener_id_estado(nombre: str) -> int:
    """
    Busca el id_estado correspondiente a un nombre (ej: 'Activo', 'Eliminado').
    Se cachea en memoria porque la tabla 'estados' casi nunca cambia.
    """
    query = text("SELECT id_estado FROM estados WHERE nombre = :nombre")
    with engine.connect() as con:
        result = con.execute(query, {"nombre": nombre})
        fila = result.first()

    if fila is None:
        raise ValueError(f"El estado '{nombre}' no existe en la tabla estados")

    return fila[0]
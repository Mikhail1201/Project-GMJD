from functools import lru_cache
from sqlalchemy import text

from extensions import engine


@lru_cache(maxsize=None)
def obtener_id_rol(nombre: str) -> int:
    """
    Busca el id_rol correspondiente a un nombre (ej: 'Empleado', 'Admin').
    Cacheado en memoria porque la tabla 'roles' casi no cambia.
    """
    query = text("SELECT id_rol FROM roles WHERE nombre = :nombre")
    with engine.connect() as con:
        result = con.execute(query, {"nombre": nombre})
        fila = result.first()

    if fila is None:
        raise ValueError(f"El rol '{nombre}' no existe en la tabla roles")

    return fila[0]
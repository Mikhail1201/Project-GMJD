from sqlalchemy import text

from app.core.database import engine
from app.models.rol import Rol


class RolRepository:

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self) -> list[Rol]:
        query = "SELECT id_rol, nombre FROM roles ORDER BY id_rol"
        with self.engine.connect() as con:
            return [Rol.desde_fila(row._mapping) for row in con.execute(text(query))]

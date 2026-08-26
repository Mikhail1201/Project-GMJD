from sqlalchemy import text

from app.core.database import engine
from app.models.estado import Estado


class EstadoRepository:

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self) -> list[Estado]:
        query = "SELECT id_estado, nombre FROM estados ORDER BY id_estado"
        with self.engine.connect() as con:
            return [Estado.desde_fila(row._mapping) for row in con.execute(text(query))]

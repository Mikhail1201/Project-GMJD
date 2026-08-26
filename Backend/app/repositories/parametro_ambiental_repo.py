from sqlalchemy import text

from app.core.database import engine
from app.models.parametro_ambiental import ParametroAmbiental


class ParametroAmbientalRepository:
    COLUMNAS = "id_parametro, nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo"

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self) -> list[ParametroAmbiental]:
        query = f"SELECT {self.COLUMNAS} FROM parametros_ambientales ORDER BY id_parametro"
        with self.engine.connect() as con:
            return [ParametroAmbiental.desde_fila(row._mapping) for row in con.execute(text(query))]

    def obtener(self, id_parametro: int) -> ParametroAmbiental | None:
        query = f"SELECT {self.COLUMNAS} FROM parametros_ambientales WHERE id_parametro = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_parametro}).mappings().first()
        return ParametroAmbiental.desde_fila(fila)

    def crear(self, parametro: ParametroAmbiental) -> ParametroAmbiental:
        query = f"""
            INSERT INTO parametros_ambientales (nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo)
            VALUES (:nombre, :unidad, :descripcion, :limite_minimo, :limite_maximo, :nivel_riesgo)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "nombre": parametro.nombre,
            "unidad": parametro.unidad,
            "descripcion": parametro.descripcion,
            "limite_minimo": parametro.limite_minimo,
            "limite_maximo": parametro.limite_maximo,
            "nivel_riesgo": parametro.nivel_riesgo,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return ParametroAmbiental.desde_fila(fila)

    def actualizar(self, id_parametro: int, campos: dict) -> ParametroAmbiental | None:
        campos_permitidos = ["nombre", "unidad", "descripcion", "limite_minimo", "limite_maximo", "nivel_riesgo"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("No se enviaron campos válidos para actualizar")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE parametros_ambientales
            SET {set_clause}
            WHERE id_parametro = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_parametro
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return ParametroAmbiental.desde_fila(fila)

    def eliminar(self, id_parametro: int) -> bool:
        query = "DELETE FROM parametros_ambientales WHERE id_parametro = :id RETURNING id_parametro"
        with self.engine.begin() as con:
            fila = con.execute(text(query), {"id": id_parametro}).mappings().first()
        return fila is not None

from sqlalchemy import text

from app.core.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from app.core.database import engine
from app.models.modelo_ia import ModeloIA
from app.repositories.catalogos import obtener_id_estado


class ModeloIARepository:
    COLUMNAS = """id_modelo, nombre, version, tipo_modelo, descripcion,
               fecha_entrenamiento, precision_modelo, id_estado"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminados: bool = False) -> list[ModeloIA]:
        query = f"SELECT {self.COLUMNAS} FROM modelos_ia"
        params = {}
        if not incluir_eliminados:
            query += " WHERE id_estado != :estado_eliminado"
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        query += " ORDER BY id_modelo"

        with self.engine.connect() as con:
            return [ModeloIA.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_modelo: int) -> ModeloIA | None:
        query = f"SELECT {self.COLUMNAS} FROM modelos_ia WHERE id_modelo = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_modelo}).mappings().first()
        return ModeloIA.desde_fila(fila)

    def crear(self, modelo: ModeloIA) -> ModeloIA:
        query = f"""
            INSERT INTO modelos_ia
                (nombre, version, tipo_modelo, descripcion, fecha_entrenamiento, precision_modelo, id_estado)
            VALUES
                (:nombre, :version, :tipo_modelo, :descripcion, :fecha_entrenamiento, :precision_modelo, :id_estado)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "nombre": modelo.nombre,
            "version": modelo.version,
            "tipo_modelo": modelo.tipo_modelo,
            "descripcion": modelo.descripcion,
            "fecha_entrenamiento": modelo.fecha_entrenamiento,
            "precision_modelo": modelo.precision_modelo,
            "id_estado": modelo.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return ModeloIA.desde_fila(fila)

    def actualizar(self, id_modelo: int, campos: dict) -> ModeloIA | None:
        campos_permitidos = [
            "nombre", "version", "tipo_modelo", "descripcion",
            "fecha_entrenamiento", "precision_modelo", "id_estado"
        ]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("No se enviaron campos válidos para actualizar")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE modelos_ia
            SET {set_clause}
            WHERE id_modelo = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_modelo
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return ModeloIA.desde_fila(fila)

    def eliminar(self, id_modelo: int) -> bool:
        query = """
            UPDATE modelos_ia
            SET id_estado = :estado_eliminado
            WHERE id_modelo = :id
            RETURNING id_modelo
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_modelo,
            }).mappings().first()
        return fila is not None

from sqlalchemy import text

from app.core.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from app.core.database import engine
from app.models.area import Area
from app.repositories.catalogos import obtener_id_estado


class AreaRepository:
    COLUMNAS = """a.id_area, a.nombre, a.descripcion, a.ubicacion,
               a.responsable_id, u.nombre AS responsable_nombre,
               u.apellido AS responsable_apellido, a.id_estado"""
    JOINS = "FROM areas a LEFT JOIN usuarios u ON u.id_usuario = a.responsable_id"

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminadas: bool = False) -> list[Area]:
        query = f"SELECT {self.COLUMNAS} {self.JOINS}"
        params = {}
        if not incluir_eliminadas:
            query += " WHERE a.id_estado != :estado_eliminado"
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        query += " ORDER BY a.id_area"

        with self.engine.connect() as con:
            return [Area.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_area: int) -> Area | None:
        query = f"SELECT {self.COLUMNAS} {self.JOINS} WHERE a.id_area = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_area}).mappings().first()
        return Area.desde_fila(fila)

    def crear(self, area: Area) -> Area:
        query = """
            INSERT INTO areas (nombre, descripcion, ubicacion, responsable_id, id_estado)
            VALUES (:nombre, :descripcion, :ubicacion, :responsable_id, :id_estado)
            RETURNING id_area, nombre, descripcion, ubicacion, responsable_id, id_estado
        """
        params = {
            "nombre": area.nombre,
            "descripcion": area.descripcion,
            "ubicacion": area.ubicacion,
            "responsable_id": area.responsable_id,
            "id_estado": area.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Area.desde_fila(fila)

    def actualizar(self, id_area: int, campos: dict) -> Area | None:
        campos_permitidos = ["nombre", "descripcion", "ubicacion", "responsable_id", "id_estado"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("No se enviaron campos válidos para actualizar")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE areas
            SET {set_clause}
            WHERE id_area = :id
            RETURNING id_area, nombre, descripcion, ubicacion, responsable_id, id_estado
        """
        actualizaciones["id"] = id_area
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Area.desde_fila(fila)

    def eliminar(self, id_area: int) -> bool:
        query = """
            UPDATE areas
            SET id_estado = :estado_eliminado
            WHERE id_area = :id
            RETURNING id_area
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_area,
            }).mappings().first()
        return fila is not None

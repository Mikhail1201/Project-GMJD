from sqlalchemy import text

from app.core.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from app.core.database import engine
from app.models.alerta import Alerta
from app.repositories.catalogos import obtener_id_estado

NIVELES_VALIDOS = ["bajo", "medio", "alto", "critico"]


class AlertaRepository:
    COLUMNAS = """a.id_alerta, a.id_medicion, a.id_area, ar.nombre AS nombre_area,
               a.tipo_alerta, a.nivel, a.descripcion, a.fecha_hora, a.id_estado,
               a.atendida_por, u.nombre AS nombre_atendio, a.fecha_atencion"""
    JOINS = """FROM alertas a
        JOIN areas ar ON ar.id_area = a.id_area
        LEFT JOIN usuarios u ON u.id_usuario = a.atendida_por"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminadas: bool = False, id_area=None,
               nivel=None, solo_sin_atender: bool = False) -> list[Alerta]:
        filtros = []
        params = {}

        if not incluir_eliminadas:
            filtros.append("a.id_estado != :estado_eliminado")
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        if id_area:
            filtros.append("a.id_area = :id_area")
            params["id_area"] = id_area
        if nivel:
            filtros.append("a.nivel = :nivel")
            params["nivel"] = nivel
        if solo_sin_atender:
            filtros.append("a.atendida_por IS NULL")

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        query = f"""
            SELECT {self.COLUMNAS}
            {self.JOINS}
            {where_clause}
            ORDER BY a.fecha_hora DESC
        """
        with self.engine.connect() as con:
            return [Alerta.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_alerta: int) -> Alerta | None:
        query = f"SELECT {self.COLUMNAS} {self.JOINS} WHERE a.id_alerta = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_alerta}).mappings().first()
        return Alerta.desde_fila(fila)

    def crear(self, alerta: Alerta) -> Alerta:
        if alerta.nivel not in NIVELES_VALIDOS:
            raise ValueError(f"nivel debe ser una de: {', '.join(NIVELES_VALIDOS)}")

        query = f"""
            INSERT INTO alertas (id_medicion, id_area, tipo_alerta, nivel, descripcion, fecha_hora, id_estado)
            VALUES (:id_medicion, :id_area, :tipo_alerta, :nivel, :descripcion,
                    COALESCE(:fecha_hora, CURRENT_TIMESTAMP), :id_estado)
            RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                      fecha_hora, id_estado, atendida_por, fecha_atencion
        """
        params = {
            "id_medicion": alerta.id_medicion,
            "id_area": alerta.id_area,
            "tipo_alerta": alerta.tipo_alerta,
            "nivel": alerta.nivel,
            "descripcion": alerta.descripcion,
            "fecha_hora": alerta.fecha_hora,
            "id_estado": alerta.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Alerta.desde_fila(fila)

    def actualizar(self, id_alerta: int, campos: dict) -> Alerta | None:
        campos_permitidos = ["tipo_alerta", "nivel", "descripcion"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError(
                "Solo se puede actualizar 'tipo_alerta', 'nivel' o 'descripcion'. "
                "Para marcarla como atendida usa /atender."
            )

        if "nivel" in actualizaciones and actualizaciones["nivel"] not in NIVELES_VALIDOS:
            raise ValueError(f"nivel debe ser una de: {', '.join(NIVELES_VALIDOS)}")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE alertas
            SET {set_clause}
            WHERE id_alerta = :id
            RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                      fecha_hora, id_estado, atendida_por, fecha_atencion
        """
        actualizaciones["id"] = id_alerta
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Alerta.desde_fila(fila)

    def atender(self, id_alerta: int, atendida_por: int) -> Alerta | None:
        query = f"""
            UPDATE alertas
            SET atendida_por = :atendida_por, fecha_atencion = CURRENT_TIMESTAMP
            WHERE id_alerta = :id AND atendida_por IS NULL
            RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                      fecha_hora, id_estado, atendida_por, fecha_atencion
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {"atendida_por": atendida_por, "id": id_alerta}).mappings().first()
        return Alerta.desde_fila(fila)

    def eliminar(self, id_alerta: int) -> bool:
        query = """
            UPDATE alertas
            SET id_estado = :estado_eliminado
            WHERE id_alerta = :id
            RETURNING id_alerta
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_alerta,
            }).mappings().first()
        return fila is not None

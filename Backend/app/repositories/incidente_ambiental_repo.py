from sqlalchemy import text

from app.core.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from app.core.database import engine
from app.models.incidente_ambiental import IncidenteAmbiental
from app.repositories.catalogos import obtener_id_estado

SEVERIDADES_VALIDAS = ["baja", "media", "alta", "critica"]


class IncidenteAmbientalRepository:
    COLUMNAS = """i.id_incidente, i.id_area, ar.nombre AS nombre_area, i.id_alerta,
               i.titulo, i.descripcion, i.fecha_inicio, i.fecha_fin, i.severidad,
               i.causa, i.acciones_realizadas, i.id_estado,
               i.responsable_id, u.nombre AS nombre_responsable"""
    JOINS = """FROM incidentes_ambientales i
        JOIN areas ar ON ar.id_area = i.id_area
        LEFT JOIN usuarios u ON u.id_usuario = i.responsable_id"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminados: bool = False, id_area=None,
               severidad=None, solo_abiertos: bool = False) -> list[IncidenteAmbiental]:
        filtros = []
        params = {}

        if not incluir_eliminados:
            filtros.append("i.id_estado != :estado_eliminado")
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        if id_area:
            filtros.append("i.id_area = :id_area")
            params["id_area"] = id_area
        if severidad:
            filtros.append("i.severidad = :severidad")
            params["severidad"] = severidad
        if solo_abiertos:
            filtros.append("i.fecha_fin IS NULL")

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        query = f"""
            SELECT {self.COLUMNAS}
            {self.JOINS}
            {where_clause}
            ORDER BY i.fecha_inicio DESC
        """
        with self.engine.connect() as con:
            return [IncidenteAmbiental.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_incidente: int) -> IncidenteAmbiental | None:
        query = f"SELECT {self.COLUMNAS} {self.JOINS} WHERE i.id_incidente = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_incidente}).mappings().first()
        return IncidenteAmbiental.desde_fila(fila)

    def crear(self, incidente: IncidenteAmbiental) -> IncidenteAmbiental:
        if incidente.severidad not in SEVERIDADES_VALIDAS:
            raise ValueError(f"severidad debe ser una de: {', '.join(SEVERIDADES_VALIDAS)}")

        query = f"""
            INSERT INTO incidentes_ambientales
                (id_area, id_alerta, titulo, descripcion, fecha_inicio, severidad,
                 causa, id_estado, responsable_id)
            VALUES
                (:id_area, :id_alerta, :titulo, :descripcion, COALESCE(:fecha_inicio, CURRENT_TIMESTAMP),
                 :severidad, :causa, :id_estado, :responsable_id)
            RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                      fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
        """
        params = {
            "id_area": incidente.id_area,
            "id_alerta": incidente.id_alerta,
            "titulo": incidente.titulo,
            "descripcion": incidente.descripcion,
            "fecha_inicio": incidente.fecha_inicio,
            "severidad": incidente.severidad,
            "causa": incidente.causa,
            "id_estado": incidente.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
            "responsable_id": incidente.responsable_id,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return IncidenteAmbiental.desde_fila(fila)

    def actualizar(self, id_incidente: int, campos: dict) -> IncidenteAmbiental | None:
        campos_permitidos = ["titulo", "descripcion", "severidad", "causa", "responsable_id"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError(
                "Solo se puede actualizar 'titulo', 'descripcion', 'severidad', 'causa' "
                "o 'responsable_id'. Para cerrar el incidente usa /resolver."
            )

        if "severidad" in actualizaciones and actualizaciones["severidad"] not in SEVERIDADES_VALIDAS:
            raise ValueError(f"severidad debe ser una de: {', '.join(SEVERIDADES_VALIDAS)}")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE incidentes_ambientales
            SET {set_clause}
            WHERE id_incidente = :id
            RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                      fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
        """
        actualizaciones["id"] = id_incidente
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return IncidenteAmbiental.desde_fila(fila)

    def resolver(self, id_incidente: int, acciones_realizadas: str) -> IncidenteAmbiental | None:
        query = f"""
            UPDATE incidentes_ambientales
            SET fecha_fin = CURRENT_TIMESTAMP, acciones_realizadas = :acciones_realizadas
            WHERE id_incidente = :id AND fecha_fin IS NULL
            RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                      fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "acciones_realizadas": acciones_realizadas,
                "id": id_incidente,
            }).mappings().first()
        return IncidenteAmbiental.desde_fila(fila)

    def eliminar(self, id_incidente: int) -> bool:
        query = """
            UPDATE incidentes_ambientales
            SET id_estado = :estado_eliminado
            WHERE id_incidente = :id
            RETURNING id_incidente
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_incidente,
            }).mappings().first()
        return fila is not None

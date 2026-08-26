from sqlalchemy import text

from app.core.database import engine
from app.models.mantenimiento import Mantenimiento

TIPOS_VALIDOS = ["preventivo", "correctivo", "predictivo"]


class MantenimientoRepository:
    COLUMNAS = """id_mantenimiento, id_area, tipo, descripcion, fecha,
               responsable_id, resultado, proximo_mantenimiento"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, id_area=None, responsable_id=None, tipo=None,
               fecha_desde=None, fecha_hasta=None) -> list[Mantenimiento]:
        filtros = []
        params = {}

        if id_area:
            filtros.append("id_area = :id_area")
            params["id_area"] = id_area
        if responsable_id:
            filtros.append("responsable_id = :responsable_id")
            params["responsable_id"] = responsable_id
        if tipo:
            filtros.append("tipo = :tipo")
            params["tipo"] = tipo
        if fecha_desde:
            filtros.append("fecha >= :fecha_desde")
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filtros.append("fecha <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        query = f"""
            SELECT {self.COLUMNAS}
            FROM mantenimientos
            {where_clause}
            ORDER BY fecha DESC
        """
        with self.engine.connect() as con:
            return [Mantenimiento.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_mantenimiento: int) -> Mantenimiento | None:
        query = f"SELECT {self.COLUMNAS} FROM mantenimientos WHERE id_mantenimiento = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_mantenimiento}).mappings().first()
        return Mantenimiento.desde_fila(fila)

    def crear(self, mantenimiento: Mantenimiento) -> Mantenimiento:
        if mantenimiento.tipo not in TIPOS_VALIDOS:
            raise ValueError(f"tipo debe ser una de: {', '.join(TIPOS_VALIDOS)}")

        query = f"""
            INSERT INTO mantenimientos
                (id_area, tipo, descripcion, fecha, responsable_id, resultado, proximo_mantenimiento)
            VALUES
                (:id_area, :tipo, :descripcion, COALESCE(:fecha, CURRENT_TIMESTAMP),
                 :responsable_id, :resultado, :proximo_mantenimiento)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "id_area": mantenimiento.id_area,
            "tipo": mantenimiento.tipo,
            "descripcion": mantenimiento.descripcion,
            "fecha": mantenimiento.fecha,
            "responsable_id": mantenimiento.responsable_id,
            "resultado": mantenimiento.resultado,
            "proximo_mantenimiento": mantenimiento.proximo_mantenimiento,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Mantenimiento.desde_fila(fila)

    def actualizar(self, id_mantenimiento: int, campos: dict) -> Mantenimiento | None:
        campos_permitidos = ["resultado", "proximo_mantenimiento", "descripcion"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("Solo se puede actualizar 'resultado', 'proximo_mantenimiento' o 'descripcion'")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE mantenimientos
            SET {set_clause}
            WHERE id_mantenimiento = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_mantenimiento
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Mantenimiento.desde_fila(fila)

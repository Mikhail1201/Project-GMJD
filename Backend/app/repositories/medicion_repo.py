from sqlalchemy import text

from app.core.database import engine
from app.models.medicion import Medicion

CALIDADES_VALIDAS = ["valida", "sospechosa", "invalida"]


class MedicionRepository:
    COLUMNAS = "id_medicion, id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion"

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, pagina: int = 1, por_pagina: int = 50,
               id_area=None, id_parametro=None, calidad_dato=None,
               fecha_desde=None, fecha_hasta=None) -> tuple[list[Medicion], int]:
        filtros = []
        params = {}

        if id_area:
            filtros.append("id_area = :id_area")
            params["id_area"] = id_area
        if id_parametro:
            filtros.append("id_parametro = :id_parametro")
            params["id_parametro"] = id_parametro
        if calidad_dato:
            filtros.append("calidad_dato = :calidad_dato")
            params["calidad_dato"] = calidad_dato
        if fecha_desde:
            filtros.append("fecha_hora >= :fecha_desde")
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filtros.append("fecha_hora <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

        query_datos = f"""
            SELECT {self.COLUMNAS}
            FROM mediciones
            {where_clause}
            ORDER BY fecha_hora DESC
            LIMIT :limite OFFSET :offset
        """
        query_total = f"SELECT COUNT(*) AS total FROM mediciones {where_clause}"

        params_paginados = {**params, "limite": por_pagina, "offset": (pagina - 1) * por_pagina}

        with self.engine.connect() as con:
            filas = [Medicion.desde_fila(row._mapping) for row in con.execute(text(query_datos), params_paginados)]
            total = con.execute(text(query_total), params).scalar()

        return filas, total

    def obtener(self, id_medicion: int) -> Medicion | None:
        query = f"SELECT {self.COLUMNAS} FROM mediciones WHERE id_medicion = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_medicion}).mappings().first()
        return Medicion.desde_fila(fila)

    def crear(self, medicion: Medicion) -> Medicion:
        if medicion.calidad_dato is None:
            medicion.calidad_dato = "valida"
        if medicion.calidad_dato not in CALIDADES_VALIDAS:
            raise ValueError(f"calidad_dato debe ser una de: {', '.join(CALIDADES_VALIDAS)}")

        query = f"""
            INSERT INTO mediciones (id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion)
            VALUES (:id_area, :id_parametro, :valor, COALESCE(:fecha_hora, CURRENT_TIMESTAMP), :calidad_dato, :observacion)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "id_area": medicion.id_area,
            "id_parametro": medicion.id_parametro,
            "valor": medicion.valor,
            "fecha_hora": medicion.fecha_hora,
            "calidad_dato": medicion.calidad_dato,
            "observacion": medicion.observacion,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Medicion.desde_fila(fila)

    def actualizar(self, id_medicion: int, campos: dict) -> Medicion | None:
        campos_permitidos = ["calidad_dato", "observacion"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("Solo se puede actualizar 'calidad_dato' u 'observacion' en una medición")

        if "calidad_dato" in actualizaciones and actualizaciones["calidad_dato"] not in CALIDADES_VALIDAS:
            raise ValueError(f"calidad_dato debe ser una de: {', '.join(CALIDADES_VALIDAS)}")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE mediciones
            SET {set_clause}
            WHERE id_medicion = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_medicion
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Medicion.desde_fila(fila)

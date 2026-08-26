from sqlalchemy import text

from app.core.database import engine
from app.models.prediccion_ia import PrediccionIA

NIVELES_RIESGO_VALIDOS = ["bajo", "medio", "alto", "critico"]


class PrediccionIARepository:
    COLUMNAS = """id_prediccion, id_modelo, id_area, id_parametro, fecha_prediccion,
               periodo_predicho, valor_predicho, nivel_riesgo, probabilidad, recomendacion"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, pagina: int = 1, por_pagina: int = 50,
               id_modelo=None, id_area=None, id_parametro=None,
               nivel_riesgo=None, fecha_desde=None, fecha_hasta=None) -> tuple[list[PrediccionIA], int]:
        filtros = []
        params = {}

        if id_modelo:
            filtros.append("id_modelo = :id_modelo")
            params["id_modelo"] = id_modelo
        if id_area:
            filtros.append("id_area = :id_area")
            params["id_area"] = id_area
        if id_parametro:
            filtros.append("id_parametro = :id_parametro")
            params["id_parametro"] = id_parametro
        if nivel_riesgo:
            filtros.append("nivel_riesgo = :nivel_riesgo")
            params["nivel_riesgo"] = nivel_riesgo
        if fecha_desde:
            filtros.append("periodo_predicho >= :fecha_desde")
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            filtros.append("periodo_predicho <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

        query_datos = f"""
            SELECT {self.COLUMNAS}
            FROM predicciones_ia
            {where_clause}
            ORDER BY periodo_predicho DESC
            LIMIT :limite OFFSET :offset
        """
        query_total = f"SELECT COUNT(*) AS total FROM predicciones_ia {where_clause}"

        params_paginados = {**params, "limite": por_pagina, "offset": (pagina - 1) * por_pagina}

        with self.engine.connect() as con:
            filas = [PrediccionIA.desde_fila(row._mapping) for row in con.execute(text(query_datos), params_paginados)]
            total = con.execute(text(query_total), params).scalar()

        return filas, total

    def obtener(self, id_prediccion: int) -> PrediccionIA | None:
        query = f"SELECT {self.COLUMNAS} FROM predicciones_ia WHERE id_prediccion = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_prediccion}).mappings().first()
        return PrediccionIA.desde_fila(fila)

    def crear(self, prediccion: PrediccionIA) -> PrediccionIA:
        if prediccion.nivel_riesgo not in NIVELES_RIESGO_VALIDOS:
            raise ValueError(f"nivel_riesgo debe ser una de: {', '.join(NIVELES_RIESGO_VALIDOS)}")

        query = f"""
            INSERT INTO predicciones_ia
                (id_modelo, id_area, id_parametro, fecha_prediccion, periodo_predicho,
                 valor_predicho, nivel_riesgo, probabilidad, recomendacion)
            VALUES
                (:id_modelo, :id_area, :id_parametro, COALESCE(:fecha_prediccion, CURRENT_TIMESTAMP),
                 :periodo_predicho, :valor_predicho, :nivel_riesgo, :probabilidad, :recomendacion)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "id_modelo": prediccion.id_modelo,
            "id_area": prediccion.id_area,
            "id_parametro": prediccion.id_parametro,
            "fecha_prediccion": prediccion.fecha_prediccion,
            "periodo_predicho": prediccion.periodo_predicho,
            "valor_predicho": prediccion.valor_predicho,
            "nivel_riesgo": prediccion.nivel_riesgo,
            "probabilidad": prediccion.probabilidad,
            "recomendacion": prediccion.recomendacion,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return PrediccionIA.desde_fila(fila)

    def actualizar(self, id_prediccion: int, campos: dict) -> PrediccionIA | None:
        campos_permitidos = ["recomendacion"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("Solo se puede actualizar 'recomendacion' en una predicción")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE predicciones_ia
            SET {set_clause}
            WHERE id_prediccion = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_prediccion
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return PrediccionIA.desde_fila(fila)

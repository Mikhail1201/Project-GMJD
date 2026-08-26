from sqlalchemy import text

from app.core.database import engine
from app.models.limite_ambiental import LimiteAmbiental


class LimiteAmbientalRepository:
    COLUMNAS = """id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
               unidad, fecha_inicio, fecha_fin, fuente_normativa"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_historico: bool = False,
               id_area=None, id_parametro=None) -> list[LimiteAmbiental]:
        filtros = []
        params = {}

        if not incluir_historico:
            filtros.append("fecha_fin IS NULL")
        if id_area:
            filtros.append("id_area = :id_area")
            params["id_area"] = id_area
        if id_parametro:
            filtros.append("id_parametro = :id_parametro")
            params["id_parametro"] = id_parametro

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        query = f"""
            SELECT {self.COLUMNAS}
            FROM limites_ambientales
            {where_clause}
            ORDER BY id_area, id_parametro, fecha_inicio DESC
        """
        with self.engine.connect() as con:
            return [LimiteAmbiental.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_limite: int) -> LimiteAmbiental | None:
        query = f"SELECT {self.COLUMNAS} FROM limites_ambientales WHERE id_limite = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_limite}).mappings().first()
        return LimiteAmbiental.desde_fila(fila)

    def crear(self, limite: LimiteAmbiental, fecha_inicio=None) -> LimiteAmbiental:
        query_cerrar = """
            UPDATE limites_ambientales
            SET fecha_fin = COALESCE(:fecha_inicio, CURRENT_DATE)
            WHERE id_parametro = :id_parametro AND id_area = :id_area AND fecha_fin IS NULL
        """
        query_insertar = f"""
            INSERT INTO limites_ambientales
                (id_parametro, id_area, limite_minimo, limite_maximo, unidad, fecha_inicio, fuente_normativa)
            VALUES
                (:id_parametro, :id_area, :limite_minimo, :limite_maximo, :unidad,
                 COALESCE(:fecha_inicio, CURRENT_DATE), :fuente_normativa)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "id_parametro": limite.id_parametro,
            "id_area": limite.id_area,
            "limite_minimo": limite.limite_minimo,
            "limite_maximo": limite.limite_maximo,
            "unidad": limite.unidad,
            "fecha_inicio": fecha_inicio,
            "fuente_normativa": limite.fuente_normativa,
        }
        with self.engine.begin() as con:
            con.execute(text(query_cerrar), params)
            fila = con.execute(text(query_insertar), params).mappings().first()
        return LimiteAmbiental.desde_fila(fila)

    def actualizar(self, id_limite: int, campos: dict) -> LimiteAmbiental | None:
        campos_permitidos = ["limite_minimo", "limite_maximo", "unidad", "fuente_normativa"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError(
                "Solo se pueden actualizar 'limite_minimo', 'limite_maximo', "
                "'unidad' o 'fuente_normativa'. Para cambiar fechas usa /cerrar o crea una nueva versión."
            )

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE limites_ambientales
            SET {set_clause}
            WHERE id_limite = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_limite
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return LimiteAmbiental.desde_fila(fila)

    def cerrar(self, id_limite: int, fecha_fin=None) -> LimiteAmbiental | None:
        query = f"""
            UPDATE limites_ambientales
            SET fecha_fin = COALESCE(:fecha_fin, CURRENT_DATE)
            WHERE id_limite = :id AND fecha_fin IS NULL
            RETURNING {self.COLUMNAS}
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {"fecha_fin": fecha_fin, "id": id_limite}).mappings().first()
        return LimiteAmbiental.desde_fila(fila)

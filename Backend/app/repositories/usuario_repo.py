from sqlalchemy import text

from app.core.constants import (
    NOMBRE_ESTADO_ACTIVO,
    NOMBRE_ESTADO_ELIMINADO,
    NOMBRE_ROL_EMPLEADO,
)
from app.core.database import engine
from app.models.usuario import Usuario
from app.repositories.catalogos import obtener_id_estado, obtener_id_rol


class UsuarioRepository:
    COLUMNAS = "id_usuario, nombre, apellido, correo, id_rol, id_estado, fecha_registro, auth_user_id"

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminados: bool = False) -> list[Usuario]:
        query = f"SELECT {self.COLUMNAS} FROM usuarios"
        params = {}
        if not incluir_eliminados:
            query += " WHERE id_estado != :estado_eliminado"
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        query += " ORDER BY id_usuario"

        with self.engine.connect() as con:
            return [Usuario.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_usuario: int) -> Usuario | None:
        query = f"SELECT {self.COLUMNAS} FROM usuarios WHERE id_usuario = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_usuario}).mappings().first()
        return Usuario.desde_fila(fila)

    def crear(self, usuario: Usuario, auth_user_id: str) -> Usuario:
        query = f"""
            INSERT INTO usuarios (nombre, apellido, correo, id_rol, id_estado, auth_user_id)
            VALUES (:nombre, :apellido, :correo, :id_rol, :id_estado, :auth_user_id)
            RETURNING {self.COLUMNAS}
        """
        params = {
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "correo": usuario.correo,
            "id_rol": usuario.id_rol or obtener_id_rol(NOMBRE_ROL_EMPLEADO),
            "id_estado": usuario.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
            "auth_user_id": auth_user_id,
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Usuario.desde_fila(fila)

    def actualizar(self, id_usuario: int, campos: dict) -> Usuario | None:
        campos_permitidos = ["nombre", "apellido", "correo", "id_rol", "id_estado"]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("No se enviaron campos válidos para actualizar")

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE usuarios
            SET {set_clause}
            WHERE id_usuario = :id
            RETURNING {self.COLUMNAS}
        """
        actualizaciones["id"] = id_usuario
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Usuario.desde_fila(fila)

    def eliminar(self, id_usuario: int) -> bool:
        query = """
            UPDATE usuarios
            SET id_estado = :estado_eliminado
            WHERE id_usuario = :id
            RETURNING id_usuario
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_usuario,
            }).mappings().first()
        return fila is not None

from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from api.estados.helpers import obtener_id_estado
from api.auth_admin.client import crear_usuario_auth
from api.constants import NOMBRE_ROL_EMPLEADO, NOMBRE_ESTADO_ACTIVO
from api.roles.helpers import obtener_id_rol

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')


# ---------- READ (listar todos) ----------
@usuarios_bp.get('/')
def listar_usuarios():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'

    query = """
        SELECT id_usuario, nombre, apellido, correo, id_rol, id_estado, fecha_registro
        FROM usuarios
    """
    params = {}
    if not incluir_eliminados:
        query += " WHERE id_estado != :estado_eliminado"
        params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
    query += " ORDER BY id_usuario"

    with engine.connect() as con:
        result = con.execute(text(query), params)
        usuarios = [dict(row._mapping) for row in result]

    return jsonify(usuarios), 200


# ---------- READ (uno solo) ----------
@usuarios_bp.get('/<int:id_usuario>')
def obtener_usuario(id_usuario):
    query = """
        SELECT id_usuario, nombre, apellido, correo, id_rol, id_estado, fecha_registro
        FROM usuarios
        WHERE id_usuario = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_usuario})
        usuario = result.mappings().first()

    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify(dict(usuario)), 200


# ---------- CREATE ----------
@usuarios_bp.post('/')
def crear_usuario():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "apellido", "correo"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if not data.get("password"):
        return jsonify({"error": "El campo 'password' es requerido"}), 400

    nombre_completo = f"{data['nombre']} {data['apellido']}"
    password_temporal = data["password"]

    try:
        usuario_auth = crear_usuario_auth(
            email=data["correo"],
            password=password_temporal,
            name=nombre_completo,
        )
    except Exception as e:
        return jsonify({"error": f"No se pudo crear el usuario en Neon Auth: {e}"}), 502

    query = """
        INSERT INTO usuarios (nombre, apellido, correo, id_rol, id_estado, auth_user_id)
        VALUES (:nombre, :apellido, :correo, :id_rol, :id_estado, :auth_user_id)
        RETURNING id_usuario, nombre, apellido, correo, id_rol, id_estado, auth_user_id
    """
    params = {
        "nombre": data["nombre"],
        "apellido": data["apellido"],
        "correo": data["correo"],
        "id_rol": data.get("id_rol", obtener_id_rol(NOMBRE_ROL_EMPLEADO)),
        "id_estado": data.get("id_estado", obtener_id_estado(NOMBRE_ESTADO_ACTIVO)),
        "auth_user_id": usuario_auth["id"],
    }

    with engine.begin() as con:
        result = con.execute(text(query), params)
        nuevo_usuario = result.mappings().first()

    return jsonify(dict(nuevo_usuario)), 201

# ---------- UPDATE ----------
@usuarios_bp.put('/<int:id_usuario>')
def actualizar_usuario(id_usuario):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["nombre", "apellido", "correo", "id_rol", "id_estado"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "No se enviaron campos válidos para actualizar"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE usuarios
        SET {set_clause}
        WHERE id_usuario = :id
        RETURNING id_usuario, nombre, apellido, correo, id_rol, id_estado, fecha_registro
    """
    actualizaciones["id"] = id_usuario

    try:
        with engine.begin() as con:
            result = con.execute(text(query), actualizaciones)
            usuario_actualizado = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "Correo ya registrado o rol/estado inválido"}), 409

    if usuario_actualizado is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify(dict(usuario_actualizado)), 200


# ---------- DELETE (soft delete) ----------
@usuarios_bp.delete('/<int:id_usuario>')
def eliminar_usuario(id_usuario):
    query = """
        UPDATE usuarios
        SET id_estado = :estado_eliminado
        WHERE id_usuario = :id
        RETURNING id_usuario
    """
    with engine.begin() as con:
        estado_eliminado = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        result = con.execute(text(query), {"estado_eliminado": estado_eliminado, "id": id_usuario})
        usuario = result.mappings().first()

    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({"mensaje": "Usuario desactivado correctamente"}), 200

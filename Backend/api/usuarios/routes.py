from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import ESTADO_ACTIVO, ESTADO_ELIMINADO

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
        params["estado_eliminado"] = ESTADO_ELIMINADO
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

    campos_requeridos = ["nombre", "apellido", "correo", "password_hash", "id_rol"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    query = """
        INSERT INTO usuarios (nombre, apellido, correo, password_hash, id_rol, id_estado)
        VALUES (:nombre, :apellido, :correo, :password_hash, :id_rol, :id_estado)
        RETURNING id_usuario, nombre, apellido, correo, id_rol, id_estado, fecha_registro
    """
    params = {
        "nombre": data["nombre"],
        "apellido": data["apellido"],
        "correo": data["correo"],
        "password_hash": data["password_hash"],  # recuerda hashear ANTES de llegar aquí
        "id_rol": data["id_rol"],
        "id_estado": data.get("id_estado", ESTADO_ACTIVO),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nuevo_usuario = result.mappings().first()
    except IntegrityError:
        # salta si el correo ya existe (UNIQUE) o si id_rol/id_estado no existen (FK)
        return jsonify({"error": "Correo ya registrado o rol/estado inválido"}), 409

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
        result = con.execute(text(query), {"estado_eliminado": ESTADO_ELIMINADO, "id": id_usuario})
        usuario = result.mappings().first()

    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    return jsonify({"mensaje": "Usuario desactivado correctamente"}), 200

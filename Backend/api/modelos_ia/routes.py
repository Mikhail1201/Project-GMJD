# api/modelos_ia/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from api.estados.helpers import obtener_id_estado

modelos_ia_bp = Blueprint('modelos_ia', __name__, url_prefix='/api/modelos-ia')


# ---------- READ (listar todos) ----------
@modelos_ia_bp.get('/')
def listar_modelos():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'

    query = """
        SELECT id_modelo, nombre, version, tipo_modelo, descripcion,
               fecha_entrenamiento, precision_modelo, id_estado
        FROM modelos_ia
    """
    params = {}
    if not incluir_eliminados:
        query += " WHERE id_estado != :estado_eliminado"
        params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
    query += " ORDER BY id_modelo"

    with engine.connect() as con:
        result = con.execute(text(query), params)
        modelos = [dict(row._mapping) for row in result]

    return jsonify(modelos), 200


# ---------- READ (uno solo) ----------
@modelos_ia_bp.get('/<int:id_modelo>')
def obtener_modelo(id_modelo):
    query = """
        SELECT id_modelo, nombre, version, tipo_modelo, descripcion,
               fecha_entrenamiento, precision_modelo, id_estado
        FROM modelos_ia
        WHERE id_modelo = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_modelo})
        modelo = result.mappings().first()

    if modelo is None:
        return jsonify({"error": "Modelo de IA no encontrado"}), 404

    return jsonify(dict(modelo)), 200


# ---------- CREATE ----------
@modelos_ia_bp.post('/')
def crear_modelo():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "version", "tipo_modelo"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    query = """
        INSERT INTO modelos_ia
            (nombre, version, tipo_modelo, descripcion, fecha_entrenamiento, precision_modelo, id_estado)
        VALUES
            (:nombre, :version, :tipo_modelo, :descripcion, :fecha_entrenamiento, :precision_modelo, :id_estado)
        RETURNING id_modelo, nombre, version, tipo_modelo, descripcion,
                  fecha_entrenamiento, precision_modelo, id_estado
    """
    params = {
        "nombre": data["nombre"],
        "version": data["version"],
        "tipo_modelo": data["tipo_modelo"],
        "descripcion": data.get("descripcion"),
        "fecha_entrenamiento": data.get("fecha_entrenamiento"),
        "precision_modelo": data.get("precision_modelo"),
        "id_estado": data.get("id_estado", obtener_id_estado(NOMBRE_ESTADO_ACTIVO)),
    }

    with engine.begin() as con:
        result = con.execute(text(query), params)
        nuevo_modelo = result.mappings().first()

    return jsonify(dict(nuevo_modelo)), 201


# ---------- UPDATE ----------
@modelos_ia_bp.put('/<int:id_modelo>')
def actualizar_modelo(id_modelo):
    data = request.get_json(silent=True) or {}

    campos_permitidos = [
        "nombre", "version", "tipo_modelo", "descripcion",
        "fecha_entrenamiento", "precision_modelo", "id_estado"
    ]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "No se enviaron campos válidos para actualizar"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE modelos_ia
        SET {set_clause}
        WHERE id_modelo = :id
        RETURNING id_modelo, nombre, version, tipo_modelo, descripcion,
                  fecha_entrenamiento, precision_modelo, id_estado
    """
    actualizaciones["id"] = id_modelo

    try:
        with engine.begin() as con:
            result = con.execute(text(query), actualizaciones)
            modelo_actualizado = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_estado inválido"}), 409

    if modelo_actualizado is None:
        return jsonify({"error": "Modelo de IA no encontrado"}), 404

    return jsonify(dict(modelo_actualizado)), 200


# ---------- DELETE (soft delete) ----------
@modelos_ia_bp.delete('/<int:id_modelo>')
def eliminar_modelo(id_modelo):
    query = """
        UPDATE modelos_ia
        SET id_estado = :estado_eliminado
        WHERE id_modelo = :id
        RETURNING id_modelo
    """
    with engine.begin() as con:
        estado_eliminado = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        result = con.execute(text(query), {"estado_eliminado": estado_eliminado, "id": id_modelo})
        modelo = result.mappings().first()

    if modelo is None:
        return jsonify({"error": "Modelo de IA no encontrado"}), 404

    return jsonify({"mensaje": "Modelo de IA desactivado correctamente"}), 200
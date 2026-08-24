from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO

areas_bp = Blueprint('areas', __name__, url_prefix='/api/areas')


# ---------- READ (listar todas) ----------
@areas_bp.get('/')
def listar_areas():
    incluir_eliminadas = request.args.get('incluir_eliminadas', 'false').lower() == 'true'

    query = """
        SELECT a.id_area, a.nombre, a.descripcion, a.ubicacion,
               a.responsable_id, u.nombre AS responsable_nombre,
               u.apellido AS responsable_apellido, a.id_estado
        FROM areas a
        LEFT JOIN usuarios u ON u.id_usuario = a.responsable_id
    """
    params = {}
    if not incluir_eliminadas:
        query += " WHERE a.id_estado != :estado_eliminado"
        params["estado_eliminado"] = NOMBRE_ESTADO_ELIMINADO
    query += " ORDER BY a.id_area"

    with engine.connect() as con:
        result = con.execute(text(query), params)
        areas = [dict(row._mapping) for row in result]

    return jsonify(areas), 200


# ---------- READ (una sola) ----------
@areas_bp.get('/<int:id_area>')
def obtener_area(id_area):
    query = """
        SELECT a.id_area, a.nombre, a.descripcion, a.ubicacion,
               a.responsable_id, u.nombre AS responsable_nombre,
               u.apellido AS responsable_apellido, a.id_estado
        FROM areas a
        LEFT JOIN usuarios u ON u.id_usuario = a.responsable_id
        WHERE a.id_area = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_area})
        area = result.mappings().first()

    if area is None:
        return jsonify({"error": "Área no encontrada"}), 404

    return jsonify(dict(area)), 200


# ---------- CREATE ----------
@areas_bp.post('/')
def crear_area():
    data = request.get_json(silent=True) or {}

    if not data.get("nombre"):
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400

    query = """
        INSERT INTO areas (nombre, descripcion, ubicacion, responsable_id, id_estado)
        VALUES (:nombre, :descripcion, :ubicacion, :responsable_id, :id_estado)
        RETURNING id_area, nombre, descripcion, ubicacion, responsable_id, id_estado
    """
    params = {
        "nombre": data["nombre"],
        "descripcion": data.get("descripcion"),
        "ubicacion": data.get("ubicacion"),
        "responsable_id": data.get("responsable_id"),
        "id_estado": data.get("id_estado", NOMBRE_ESTADO_ACTIVO),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nueva_area = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "responsable_id o id_estado inválido"}), 409

    return jsonify(dict(nueva_area)), 201


# ---------- UPDATE ----------
@areas_bp.put('/<int:id_area>')
def actualizar_area(id_area):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["nombre", "descripcion", "ubicacion", "responsable_id", "id_estado"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "No se enviaron campos válidos para actualizar"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE areas
        SET {set_clause}
        WHERE id_area = :id
        RETURNING id_area, nombre, descripcion, ubicacion, responsable_id, id_estado
    """
    actualizaciones["id"] = id_area

    try:
        with engine.begin() as con:
            result = con.execute(text(query), actualizaciones)
            area_actualizada = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "responsable_id o id_estado inválido"}), 409

    if area_actualizada is None:
        return jsonify({"error": "Área no encontrada"}), 404

    return jsonify(dict(area_actualizada)), 200


# ---------- DELETE (soft delete) ----------
@areas_bp.delete('/<int:id_area>')
def eliminar_area(id_area):
    query = """
        UPDATE areas
        SET id_estado = :estado_eliminado
        WHERE id_area = :id
        RETURNING id_area
    """
    with engine.begin() as con:
        result = con.execute(text(query), {"estado_eliminado": NOMBRE_ESTADO_ELIMINADO, "id": id_area})
        area = result.mappings().first()

    if area is None:
        return jsonify({"error": "Área no encontrada"}), 404

    return jsonify({"mensaje": "Área desactivada correctamente"}), 200
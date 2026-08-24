# api/alertas/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from api.estados.helpers import obtener_id_estado

alertas_bp = Blueprint('alertas', __name__, url_prefix='/api/alertas')

NIVELES_VALIDOS = ["bajo", "medio", "alto", "critico"]


# ---------- READ (listar, con filtros) ----------
@alertas_bp.get('/')
def listar_alertas():
    incluir_eliminadas = request.args.get('incluir_eliminadas', 'false').lower() == 'true'
    id_area = request.args.get('id_area')
    nivel = request.args.get('nivel')
    solo_sin_atender = request.args.get('solo_sin_atender', 'false').lower() == 'true'

    filtros = []
    params = {}

    if not incluir_eliminadas:
        filtros.append("a.id_estado != :estado_eliminado")
        params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
    if id_area:
        filtros.append("a.id_area = :id_area")
        params["id_area"] = id_area
    if nivel:
        filtros.append("a.nivel = :nivel")
        params["nivel"] = nivel
    if solo_sin_atender:
        filtros.append("a.atendida_por IS NULL")

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT a.id_alerta, a.id_medicion, a.id_area, ar.nombre AS nombre_area,
               a.tipo_alerta, a.nivel, a.descripcion, a.fecha_hora, a.id_estado,
               a.atendida_por, u.nombre AS nombre_atendio, a.fecha_atencion
        FROM alertas a
        JOIN areas ar ON ar.id_area = a.id_area
        LEFT JOIN usuarios u ON u.id_usuario = a.atendida_por
        {where_clause}
        ORDER BY a.fecha_hora DESC
    """
    with engine.connect() as con:
        result = con.execute(text(query), params)
        alertas = [dict(row._mapping) for row in result]

    return jsonify(alertas), 200


# ---------- READ (una sola) ----------
@alertas_bp.get('/<int:id_alerta>')
def obtener_alerta(id_alerta):
    query = """
        SELECT a.id_alerta, a.id_medicion, a.id_area, ar.nombre AS nombre_area,
               a.tipo_alerta, a.nivel, a.descripcion, a.fecha_hora, a.id_estado,
               a.atendida_por, u.nombre AS nombre_atendio, a.fecha_atencion
        FROM alertas a
        JOIN areas ar ON ar.id_area = a.id_area
        LEFT JOIN usuarios u ON u.id_usuario = a.atendida_por
        WHERE a.id_alerta = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_alerta})
        alerta = result.mappings().first()

    if alerta is None:
        return jsonify({"error": "Alerta no encontrada"}), 404

    return jsonify(dict(alerta)), 200


# ---------- CREATE ----------
@alertas_bp.post('/')
def crear_alerta():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_medicion", "id_area", "tipo_alerta", "nivel", "descripcion"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data["nivel"] not in NIVELES_VALIDOS:
        return jsonify({"error": f"nivel debe ser una de: {', '.join(NIVELES_VALIDOS)}"}), 400

    query = """
        INSERT INTO alertas (id_medicion, id_area, tipo_alerta, nivel, descripcion, fecha_hora, id_estado)
        VALUES (:id_medicion, :id_area, :tipo_alerta, :nivel, :descripcion,
                COALESCE(:fecha_hora, CURRENT_TIMESTAMP), :id_estado)
        RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                  fecha_hora, id_estado, atendida_por, fecha_atencion
    """
    params = {
        "id_medicion": data["id_medicion"],
        "id_area": data["id_area"],
        "tipo_alerta": data["tipo_alerta"],
        "nivel": data["nivel"],
        "descripcion": data["descripcion"],
        "fecha_hora": data.get("fecha_hora"),
        "id_estado": data.get("id_estado", obtener_id_estado(NOMBRE_ESTADO_ACTIVO)),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nueva_alerta = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_medicion, id_area o id_estado inválido"}), 409

    return jsonify(dict(nueva_alerta)), 201


# ---------- UPDATE (datos de la alerta, no atención ni estado) ----------
@alertas_bp.put('/<int:id_alerta>')
def actualizar_alerta(id_alerta):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["tipo_alerta", "nivel", "descripcion"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({
            "error": "Solo se puede actualizar 'tipo_alerta', 'nivel' o 'descripcion'. "
                     "Para marcarla como atendida usa /atender."
        }), 400

    if "nivel" in actualizaciones and actualizaciones["nivel"] not in NIVELES_VALIDOS:
        return jsonify({"error": f"nivel debe ser una de: {', '.join(NIVELES_VALIDOS)}"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE alertas
        SET {set_clause}
        WHERE id_alerta = :id
        RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                  fecha_hora, id_estado, atendida_por, fecha_atencion
    """
    actualizaciones["id"] = id_alerta

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        alerta_actualizada = result.mappings().first()

    if alerta_actualizada is None:
        return jsonify({"error": "Alerta no encontrada"}), 404

    return jsonify(dict(alerta_actualizada)), 200


# ---------- ATENDER (marca quién y cuándo se atendió) ----------
@alertas_bp.put('/<int:id_alerta>/atender')
def atender_alerta(id_alerta):
    data = request.get_json(silent=True) or {}

    if not data.get("atendida_por"):
        return jsonify({"error": "El campo 'atendida_por' (id_usuario) es requerido"}), 400

    query = """
        UPDATE alertas
        SET atendida_por = :atendida_por, fecha_atencion = CURRENT_TIMESTAMP
        WHERE id_alerta = :id AND atendida_por IS NULL
        RETURNING id_alerta, id_medicion, id_area, tipo_alerta, nivel, descripcion,
                  fecha_hora, id_estado, atendida_por, fecha_atencion
    """
    try:
        with engine.begin() as con:
            result = con.execute(text(query), {"atendida_por": data["atendida_por"], "id": id_alerta})
            alerta = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "atendida_por no corresponde a un usuario válido"}), 409

    if alerta is None:
        return jsonify({"error": "Alerta no encontrada o ya estaba atendida"}), 404

    return jsonify(dict(alerta)), 200


# ---------- DELETE (soft delete) ----------
@alertas_bp.delete('/<int:id_alerta>')
def eliminar_alerta(id_alerta):
    query = """
        UPDATE alertas
        SET id_estado = :estado_eliminado
        WHERE id_alerta = :id
        RETURNING id_alerta
    """
    with engine.begin() as con:
        estado_eliminado = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        result = con.execute(text(query), {"estado_eliminado": estado_eliminado, "id": id_alerta})
        alerta = result.mappings().first()

    if alerta is None:
        return jsonify({"error": "Alerta no encontrada"}), 404

    return jsonify({"mensaje": "Alerta desactivada correctamente"}), 200
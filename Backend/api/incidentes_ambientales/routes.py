# api/incidentes_ambientales/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine
from api.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from api.estados.helpers import obtener_id_estado

incidentes_bp = Blueprint('incidentes_ambientales', __name__, url_prefix='/api/incidentes-ambientales')

SEVERIDADES_VALIDAS = ["baja", "media", "alta", "critica"]


# ---------- READ (listar, con filtros) ----------
@incidentes_bp.get('/')
def listar_incidentes():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'
    id_area = request.args.get('id_area')
    severidad = request.args.get('severidad')
    solo_abiertos = request.args.get('solo_abiertos', 'false').lower() == 'true'

    filtros = []
    params = {}

    if not incluir_eliminados:
        filtros.append("i.id_estado != :estado_eliminado")
        params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
    if id_area:
        filtros.append("i.id_area = :id_area")
        params["id_area"] = id_area
    if severidad:
        filtros.append("i.severidad = :severidad")
        params["severidad"] = severidad
    if solo_abiertos:
        filtros.append("i.fecha_fin IS NULL")

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT i.id_incidente, i.id_area, ar.nombre AS nombre_area, i.id_alerta,
               i.titulo, i.descripcion, i.fecha_inicio, i.fecha_fin, i.severidad,
               i.causa, i.acciones_realizadas, i.id_estado,
               i.responsable_id, u.nombre AS nombre_responsable
        FROM incidentes_ambientales i
        JOIN areas ar ON ar.id_area = i.id_area
        LEFT JOIN usuarios u ON u.id_usuario = i.responsable_id
        {where_clause}
        ORDER BY i.fecha_inicio DESC
    """
    with engine.connect() as con:
        result = con.execute(text(query), params)
        incidentes = [dict(row._mapping) for row in result]

    return jsonify(incidentes), 200


# ---------- READ (uno solo) ----------
@incidentes_bp.get('/<int:id_incidente>')
def obtener_incidente(id_incidente):
    query = """
        SELECT i.id_incidente, i.id_area, ar.nombre AS nombre_area, i.id_alerta,
               i.titulo, i.descripcion, i.fecha_inicio, i.fecha_fin, i.severidad,
               i.causa, i.acciones_realizadas, i.id_estado,
               i.responsable_id, u.nombre AS nombre_responsable
        FROM incidentes_ambientales i
        JOIN areas ar ON ar.id_area = i.id_area
        LEFT JOIN usuarios u ON u.id_usuario = i.responsable_id
        WHERE i.id_incidente = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_incidente})
        incidente = result.mappings().first()

    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404

    return jsonify(dict(incidente)), 200


# ---------- CREATE ----------
@incidentes_bp.post('/')
def crear_incidente():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "titulo", "descripcion", "severidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data["severidad"] not in SEVERIDADES_VALIDAS:
        return jsonify({"error": f"severidad debe ser una de: {', '.join(SEVERIDADES_VALIDAS)}"}), 400

    query = """
        INSERT INTO incidentes_ambientales
            (id_area, id_alerta, titulo, descripcion, fecha_inicio, severidad,
             causa, id_estado, responsable_id)
        VALUES
            (:id_area, :id_alerta, :titulo, :descripcion, COALESCE(:fecha_inicio, CURRENT_TIMESTAMP),
             :severidad, :causa, :id_estado, :responsable_id)
        RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                  fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
    """
    params = {
        "id_area": data["id_area"],
        "id_alerta": data.get("id_alerta"),
        "titulo": data["titulo"],
        "descripcion": data["descripcion"],
        "fecha_inicio": data.get("fecha_inicio"),
        "severidad": data["severidad"],
        "causa": data.get("causa"),
        "id_estado": data.get("id_estado", obtener_id_estado(NOMBRE_ESTADO_ACTIVO)),
        "responsable_id": data.get("responsable_id"),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nuevo_incidente = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_area, id_alerta, id_estado o responsable_id inválido"}), 409

    return jsonify(dict(nuevo_incidente)), 201


# ---------- UPDATE (datos del incidente, no cierre) ----------
@incidentes_bp.put('/<int:id_incidente>')
def actualizar_incidente(id_incidente):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["titulo", "descripcion", "severidad", "causa", "responsable_id"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({
            "error": "Solo se puede actualizar 'titulo', 'descripcion', 'severidad', 'causa' "
                     "o 'responsable_id'. Para cerrar el incidente usa /resolver."
        }), 400

    if "severidad" in actualizaciones and actualizaciones["severidad"] not in SEVERIDADES_VALIDAS:
        return jsonify({"error": f"severidad debe ser una de: {', '.join(SEVERIDADES_VALIDAS)}"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE incidentes_ambientales
        SET {set_clause}
        WHERE id_incidente = :id
        RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                  fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
    """
    actualizaciones["id"] = id_incidente

    try:
        with engine.begin() as con:
            result = con.execute(text(query), actualizaciones)
            incidente_actualizado = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "responsable_id inválido"}), 409

    if incidente_actualizado is None:
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404

    return jsonify(dict(incidente_actualizado)), 200


# ---------- RESOLVER (cierra el incidente con fecha y acciones) ----------
@incidentes_bp.put('/<int:id_incidente>/resolver')
def resolver_incidente(id_incidente):
    data = request.get_json(silent=True) or {}

    if not data.get("acciones_realizadas"):
        return jsonify({"error": "El campo 'acciones_realizadas' es requerido para resolver el incidente"}), 400

    query = """
        UPDATE incidentes_ambientales
        SET fecha_fin = CURRENT_TIMESTAMP, acciones_realizadas = :acciones_realizadas
        WHERE id_incidente = :id AND fecha_fin IS NULL
        RETURNING id_incidente, id_area, id_alerta, titulo, descripcion, fecha_inicio,
                  fecha_fin, severidad, causa, acciones_realizadas, id_estado, responsable_id
    """
    with engine.begin() as con:
        result = con.execute(
            text(query),
            {"acciones_realizadas": data["acciones_realizadas"], "id": id_incidente}
        )
        incidente = result.mappings().first()

    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado o ya estaba resuelto"}), 404

    return jsonify(dict(incidente)), 200


# ---------- DELETE (soft delete) ----------
@incidentes_bp.delete('/<int:id_incidente>')
def eliminar_incidente(id_incidente):
    query = """
        UPDATE incidentes_ambientales
        SET id_estado = :estado_eliminado
        WHERE id_incidente = :id
        RETURNING id_incidente
    """
    with engine.begin() as con:
        estado_eliminado = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        result = con.execute(text(query), {"estado_eliminado": estado_eliminado, "id": id_incidente})
        incidente = result.mappings().first()

    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404

    return jsonify({"mensaje": "Incidente ambiental desactivado correctamente"}), 200
# api/mantenimientos/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine

mantenimientos_bp = Blueprint('mantenimientos', __name__, url_prefix='/api/mantenimientos')

TIPOS_VALIDOS = ["preventivo", "correctivo", "predictivo"]


# ---------- READ (listar, con filtros) ----------
@mantenimientos_bp.get('/')
def listar_mantenimientos():
    id_area = request.args.get('id_area')
    responsable_id = request.args.get('responsable_id')
    tipo = request.args.get('tipo')
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')

    filtros = []
    params = {}

    if id_area:
        filtros.append("id_area = :id_area")
        params["id_area"] = id_area
    if responsable_id:
        filtros.append("responsable_id = :responsable_id")
        params["responsable_id"] = responsable_id
    if tipo:
        filtros.append("tipo = :tipo")
        params["tipo"] = tipo
    if fecha_desde:
        filtros.append("fecha >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros.append("fecha <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT id_mantenimiento, id_area, tipo, descripcion, fecha,
               responsable_id, resultado, proximo_mantenimiento
        FROM mantenimientos
        {where_clause}
        ORDER BY fecha DESC
    """
    with engine.connect() as con:
        result = con.execute(text(query), params)
        mantenimientos = [dict(row._mapping) for row in result]

    return jsonify(mantenimientos), 200


# ---------- READ (uno solo) ----------
@mantenimientos_bp.get('/<int:id_mantenimiento>')
def obtener_mantenimiento(id_mantenimiento):
    query = """
        SELECT id_mantenimiento, id_area, tipo, descripcion, fecha,
               responsable_id, resultado, proximo_mantenimiento
        FROM mantenimientos
        WHERE id_mantenimiento = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_mantenimiento})
        mantenimiento = result.mappings().first()

    if mantenimiento is None:
        return jsonify({"error": "Mantenimiento no encontrado"}), 404

    return jsonify(dict(mantenimiento)), 200


# ---------- CREATE ----------
@mantenimientos_bp.post('/')
def crear_mantenimiento():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "tipo", "descripcion"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data["tipo"] not in TIPOS_VALIDOS:
        return jsonify({"error": f"tipo debe ser una de: {', '.join(TIPOS_VALIDOS)}"}), 400

    query = """
        INSERT INTO mantenimientos
            (id_area, tipo, descripcion, fecha, responsable_id, resultado, proximo_mantenimiento)
        VALUES
            (:id_area, :tipo, :descripcion, COALESCE(:fecha, CURRENT_TIMESTAMP),
             :responsable_id, :resultado, :proximo_mantenimiento)
        RETURNING id_mantenimiento, id_area, tipo, descripcion, fecha,
                  responsable_id, resultado, proximo_mantenimiento
    """
    params = {
        "id_area": data["id_area"],
        "tipo": data["tipo"],
        "descripcion": data["descripcion"],
        "fecha": data.get("fecha"),
        "responsable_id": data.get("responsable_id"),
        "resultado": data.get("resultado"),
        "proximo_mantenimiento": data.get("proximo_mantenimiento"),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nuevo_mantenimiento = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_area o responsable_id inválido"}), 409

    return jsonify(dict(nuevo_mantenimiento)), 201


# ---------- UPDATE (solo resultado / próximo mantenimiento / descripción) ----------
@mantenimientos_bp.put('/<int:id_mantenimiento>')
def actualizar_mantenimiento(id_mantenimiento):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["resultado", "proximo_mantenimiento", "descripcion"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({
            "error": "Solo se puede actualizar 'resultado', 'proximo_mantenimiento' o 'descripcion'"
        }), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE mantenimientos
        SET {set_clause}
        WHERE id_mantenimiento = :id
        RETURNING id_mantenimiento, id_area, tipo, descripcion, fecha,
                  responsable_id, resultado, proximo_mantenimiento
    """
    actualizaciones["id"] = id_mantenimiento

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        mantenimiento_actualizado = result.mappings().first()

    if mantenimiento_actualizado is None:
        return jsonify({"error": "Mantenimiento no encontrado"}), 404

    return jsonify(dict(mantenimiento_actualizado)), 200


# No hay DELETE: mantenimientos es un log append-only.
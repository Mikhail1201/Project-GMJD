# api/mediciones/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine

mediciones_bp = Blueprint('mediciones', __name__, url_prefix='/api/mediciones')

CALIDADES_VALIDAS = ["valida", "sospechosa", "invalida"]


# ---------- READ (listar, paginado) ----------
@mediciones_bp.get('/')
def listar_mediciones():
    try:
        pagina = max(int(request.args.get('pagina', 1)), 1)
        por_pagina = min(max(int(request.args.get('por_pagina', 50)), 1), 200)
    except ValueError:
        return jsonify({"error": "'pagina' y 'por_pagina' deben ser enteros"}), 400

    id_area = request.args.get('id_area')
    id_parametro = request.args.get('id_parametro')
    calidad_dato = request.args.get('calidad_dato')
    fecha_desde = request.args.get('fecha_desde')  # ISO: YYYY-MM-DD
    fecha_hasta = request.args.get('fecha_hasta')

    filtros = []
    params = {}

    if id_area:
        filtros.append("id_area = :id_area")
        params["id_area"] = id_area
    if id_parametro:
        filtros.append("id_parametro = :id_parametro")
        params["id_parametro"] = id_parametro
    if calidad_dato:
        filtros.append("calidad_dato = :calidad_dato")
        params["calidad_dato"] = calidad_dato
    if fecha_desde:
        filtros.append("fecha_hora >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros.append("fecha_hora <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query_datos = f"""
        SELECT id_medicion, id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion
        FROM mediciones
        {where_clause}
        ORDER BY fecha_hora DESC
        LIMIT :limite OFFSET :offset
    """
    query_total = f"SELECT COUNT(*) AS total FROM mediciones {where_clause}"

    params_paginados = {**params, "limite": por_pagina, "offset": (pagina - 1) * por_pagina}

    with engine.connect() as con:
        result = con.execute(text(query_datos), params_paginados)
        mediciones = [dict(row._mapping) for row in result]

        total = con.execute(text(query_total), params).scalar()

    return jsonify({
        "datos": mediciones,
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina if total else 0,
        }
    }), 200


# ---------- READ (una sola) ----------
@mediciones_bp.get('/<int:id_medicion>')
def obtener_medicion(id_medicion):
    query = """
        SELECT id_medicion, id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion
        FROM mediciones
        WHERE id_medicion = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_medicion})
        medicion = result.mappings().first()

    if medicion is None:
        return jsonify({"error": "Medición no encontrada"}), 404

    return jsonify(dict(medicion)), 200


# ---------- CREATE ----------
@mediciones_bp.post('/')
def crear_medicion():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "id_parametro", "valor"]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    calidad_dato = data.get("calidad_dato", "valida")
    if calidad_dato not in CALIDADES_VALIDAS:
        return jsonify({"error": f"calidad_dato debe ser una de: {', '.join(CALIDADES_VALIDAS)}"}), 400

    query = """
        INSERT INTO mediciones (id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion)
        VALUES (:id_area, :id_parametro, :valor, COALESCE(:fecha_hora, CURRENT_TIMESTAMP), :calidad_dato, :observacion)
        RETURNING id_medicion, id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion
    """
    params = {
        "id_area": data["id_area"],
        "id_parametro": data["id_parametro"],
        "valor": data["valor"],
        "fecha_hora": data.get("fecha_hora"),
        "calidad_dato": calidad_dato,
        "observacion": data.get("observacion"),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nueva_medicion = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_area o id_parametro inválido"}), 409

    return jsonify(dict(nueva_medicion)), 201


# ---------- UPDATE (solo calidad_dato / observacion — log append-only) ----------
@mediciones_bp.put('/<int:id_medicion>')
def actualizar_medicion(id_medicion):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["calidad_dato", "observacion"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "Solo se puede actualizar 'calidad_dato' u 'observacion' en una medición"}), 400

    if "calidad_dato" in actualizaciones and actualizaciones["calidad_dato"] not in CALIDADES_VALIDAS:
        return jsonify({"error": f"calidad_dato debe ser una de: {', '.join(CALIDADES_VALIDAS)}"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE mediciones
        SET {set_clause}
        WHERE id_medicion = :id
        RETURNING id_medicion, id_area, id_parametro, valor, fecha_hora, calidad_dato, observacion
    """
    actualizaciones["id"] = id_medicion

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        medicion_actualizada = result.mappings().first()

    if medicion_actualizada is None:
        return jsonify({"error": "Medición no encontrada"}), 404

    return jsonify(dict(medicion_actualizada)), 200


# No hay DELETE: mediciones es un log append-only.
# Para invalidar un dato erróneo, usar PUT y poner calidad_dato = "invalida".
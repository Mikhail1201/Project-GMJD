# api/predicciones_ia/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine

predicciones_bp = Blueprint('predicciones_ia', __name__, url_prefix='/api/predicciones-ia')

NIVELES_RIESGO_VALIDOS = ["bajo", "medio", "alto", "critico"]


# ---------- READ (listar, paginado) ----------
@predicciones_bp.get('/')
def listar_predicciones():
    try:
        pagina = max(int(request.args.get('pagina', 1)), 1)
        por_pagina = min(max(int(request.args.get('por_pagina', 50)), 1), 200)
    except ValueError:
        return jsonify({"error": "'pagina' y 'por_pagina' deben ser enteros"}), 400

    id_modelo = request.args.get('id_modelo')
    id_area = request.args.get('id_area')
    id_parametro = request.args.get('id_parametro')
    nivel_riesgo = request.args.get('nivel_riesgo')
    fecha_desde = request.args.get('fecha_desde')  # sobre periodo_predicho
    fecha_hasta = request.args.get('fecha_hasta')

    filtros = []
    params = {}

    if id_modelo:
        filtros.append("id_modelo = :id_modelo")
        params["id_modelo"] = id_modelo
    if id_area:
        filtros.append("id_area = :id_area")
        params["id_area"] = id_area
    if id_parametro:
        filtros.append("id_parametro = :id_parametro")
        params["id_parametro"] = id_parametro
    if nivel_riesgo:
        filtros.append("nivel_riesgo = :nivel_riesgo")
        params["nivel_riesgo"] = nivel_riesgo
    if fecha_desde:
        filtros.append("periodo_predicho >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        filtros.append("periodo_predicho <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query_datos = f"""
        SELECT id_prediccion, id_modelo, id_area, id_parametro, fecha_prediccion,
               periodo_predicho, valor_predicho, nivel_riesgo, probabilidad, recomendacion
        FROM predicciones_ia
        {where_clause}
        ORDER BY periodo_predicho DESC
        LIMIT :limite OFFSET :offset
    """
    query_total = f"SELECT COUNT(*) AS total FROM predicciones_ia {where_clause}"

    params_paginados = {**params, "limite": por_pagina, "offset": (pagina - 1) * por_pagina}

    with engine.connect() as con:
        result = con.execute(text(query_datos), params_paginados)
        predicciones = [dict(row._mapping) for row in result]

        total = con.execute(text(query_total), params).scalar()

    return jsonify({
        "datos": predicciones,
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina if total else 0,
        }
    }), 200


# ---------- READ (una sola) ----------
@predicciones_bp.get('/<int:id_prediccion>')
def obtener_prediccion(id_prediccion):
    query = """
        SELECT id_prediccion, id_modelo, id_area, id_parametro, fecha_prediccion,
               periodo_predicho, valor_predicho, nivel_riesgo, probabilidad, recomendacion
        FROM predicciones_ia
        WHERE id_prediccion = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_prediccion})
        prediccion = result.mappings().first()

    if prediccion is None:
        return jsonify({"error": "Predicción no encontrada"}), 404

    return jsonify(dict(prediccion)), 200


# ---------- CREATE ----------
@predicciones_bp.post('/')
def crear_prediccion():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_modelo", "id_area", "id_parametro", "periodo_predicho", "valor_predicho", "nivel_riesgo"]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data["nivel_riesgo"] not in NIVELES_RIESGO_VALIDOS:
        return jsonify({"error": f"nivel_riesgo debe ser una de: {', '.join(NIVELES_RIESGO_VALIDOS)}"}), 400

    query = """
        INSERT INTO predicciones_ia
            (id_modelo, id_area, id_parametro, fecha_prediccion, periodo_predicho,
             valor_predicho, nivel_riesgo, probabilidad, recomendacion)
        VALUES
            (:id_modelo, :id_area, :id_parametro, COALESCE(:fecha_prediccion, CURRENT_TIMESTAMP),
             :periodo_predicho, :valor_predicho, :nivel_riesgo, :probabilidad, :recomendacion)
        RETURNING id_prediccion, id_modelo, id_area, id_parametro, fecha_prediccion,
                  periodo_predicho, valor_predicho, nivel_riesgo, probabilidad, recomendacion
    """
    params = {
        "id_modelo": data["id_modelo"],
        "id_area": data["id_area"],
        "id_parametro": data["id_parametro"],
        "fecha_prediccion": data.get("fecha_prediccion"),
        "periodo_predicho": data["periodo_predicho"],
        "valor_predicho": data["valor_predicho"],
        "nivel_riesgo": data["nivel_riesgo"],
        "probabilidad": data.get("probabilidad"),
        "recomendacion": data.get("recomendacion"),
    }

    try:
        with engine.begin() as con:
            result = con.execute(text(query), params)
            nueva_prediccion = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_modelo, id_area o id_parametro inválido"}), 409

    return jsonify(dict(nueva_prediccion)), 201


# ---------- UPDATE (solo recomendacion — log append-only) ----------
@predicciones_bp.put('/<int:id_prediccion>')
def actualizar_prediccion(id_prediccion):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["recomendacion"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "Solo se puede actualizar 'recomendacion' en una predicción"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE predicciones_ia
        SET {set_clause}
        WHERE id_prediccion = :id
        RETURNING id_prediccion, id_modelo, id_area, id_parametro, fecha_prediccion,
                  periodo_predicho, valor_predicho, nivel_riesgo, probabilidad, recomendacion
    """
    actualizaciones["id"] = id_prediccion

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        prediccion_actualizada = result.mappings().first()

    if prediccion_actualizada is None:
        return jsonify({"error": "Predicción no encontrada"}), 404

    return jsonify(dict(prediccion_actualizada)), 200


# No hay DELETE: predicciones_ia es un log append-only.
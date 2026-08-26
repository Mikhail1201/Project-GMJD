from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.prediccion_ia import PrediccionIA
from app.repositories.prediccion_ia_repo import PrediccionIARepository

predicciones_bp = Blueprint('predicciones_ia', __name__, url_prefix='/api/predicciones-ia')
repo = PrediccionIARepository()


@predicciones_bp.get('/')
def listar_predicciones():
    try:
        pagina = max(int(request.args.get('pagina', 1)), 1)
        por_pagina = min(max(int(request.args.get('por_pagina', 50)), 1), 200)
    except ValueError:
        return jsonify({"error": "'pagina' y 'por_pagina' deben ser enteros"}), 400

    predicciones, total = repo.listar(
        pagina=pagina,
        por_pagina=por_pagina,
        id_modelo=request.args.get('id_modelo'),
        id_area=request.args.get('id_area'),
        id_parametro=request.args.get('id_parametro'),
        nivel_riesgo=request.args.get('nivel_riesgo'),
        fecha_desde=request.args.get('fecha_desde'),
        fecha_hasta=request.args.get('fecha_hasta'),
    )

    return jsonify({
        "datos": [p.a_dict() for p in predicciones],
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina if total else 0,
        }
    }), 200


@predicciones_bp.get('/<int:id_prediccion>')
def obtener_prediccion(id_prediccion):
    prediccion = repo.obtener(id_prediccion)
    if prediccion is None:
        return jsonify({"error": "Predicción no encontrada"}), 404
    return jsonify(prediccion.a_dict()), 200


@predicciones_bp.post('/')
def crear_prediccion():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_modelo", "id_area", "id_parametro", "periodo_predicho", "valor_predicho", "nivel_riesgo"]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    prediccion = PrediccionIA(
        id_modelo=data["id_modelo"],
        id_area=data["id_area"],
        id_parametro=data["id_parametro"],
        fecha_prediccion=data.get("fecha_prediccion"),
        periodo_predicho=data["periodo_predicho"],
        valor_predicho=data["valor_predicho"],
        nivel_riesgo=data["nivel_riesgo"],
        probabilidad=data.get("probabilidad"),
        recomendacion=data.get("recomendacion"),
    )

    try:
        nueva = repo.crear(prediccion)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_modelo, id_area o id_parametro inválido"}), 409

    return jsonify(nueva.a_dict()), 201


@predicciones_bp.put('/<int:id_prediccion>')
def actualizar_prediccion(id_prediccion):
    data = request.get_json(silent=True) or {}

    try:
        prediccion = repo.actualizar(id_prediccion, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if prediccion is None:
        return jsonify({"error": "Predicción no encontrada"}), 404

    return jsonify(prediccion.a_dict()), 200

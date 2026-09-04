from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.medicion import Medicion
from app.repositories.medicion_repo import MedicionRepository

mediciones_bp = Blueprint('mediciones', __name__, url_prefix='/api/mediciones')
repo = MedicionRepository()


@mediciones_bp.get('/')
def listar_mediciones():
    try:
        pagina = max(int(request.args.get('pagina', 1)), 1)
        por_pagina = min(max(int(request.args.get('por_pagina', 50)), 1), 200)
    except ValueError:
        return jsonify({"error": "'pagina' y 'por_pagina' deben ser enteros"}), 400

    mediciones, total = repo.listar(
        pagina=pagina,
        por_pagina=por_pagina,
        id_area=request.args.get('id_area'),
        id_parametro=request.args.get('id_parametro'),
        calidad_dato=request.args.get('calidad_dato'),
        id_sensor=request.args.get('id_sensor'),
        fecha_desde=request.args.get('fecha_desde'),
        fecha_hasta=request.args.get('fecha_hasta'),
    )

    return jsonify({
        "datos": [m.a_dict() for m in mediciones],
        "paginacion": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total": total,
            "total_paginas": (total + por_pagina - 1) // por_pagina if total else 0,
        }
    }), 200


@mediciones_bp.get('/<int:id_medicion>')
def obtener_medicion(id_medicion):
    medicion = repo.obtener(id_medicion)
    if medicion is None:
        return jsonify({"error": "Medición no encontrada"}), 404
    return jsonify(medicion.a_dict()), 200


@mediciones_bp.post('/')
def crear_medicion():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "id_parametro", "valor"]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    medicion = Medicion(
        id_area=data["id_area"],
        id_parametro=data["id_parametro"],
        valor=data["valor"],
        fecha_hora=data.get("fecha_hora"),
        calidad_dato=data.get("calidad_dato"),
        observacion=data.get("observacion"),
        # Opcional: si no viene, el repositorio resuelve el sensor principal
        # del (id_area, id_parametro) — es lo que pasa con el ESP32.
        id_sensor=data.get("id_sensor"),
    )

    try:
        nueva = repo.crear(medicion)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_area o id_parametro inválido"}), 409

    return jsonify(nueva.a_dict()), 201


@mediciones_bp.put('/<int:id_medicion>')
def actualizar_medicion(id_medicion):
    data = request.get_json(silent=True) or {}

    try:
        medicion = repo.actualizar(id_medicion, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if medicion is None:
        return jsonify({"error": "Medición no encontrada"}), 404

    return jsonify(medicion.a_dict()), 200

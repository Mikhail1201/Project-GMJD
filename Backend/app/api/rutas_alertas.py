from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.alerta import Alerta
from app.repositories.alerta_repo import AlertaRepository

alertas_bp = Blueprint('alertas', __name__, url_prefix='/api/alertas')
repo = AlertaRepository()


@alertas_bp.get('/')
def listar_alertas():
    alertas = repo.listar(
        incluir_eliminadas=request.args.get('incluir_eliminadas', 'false').lower() == 'true',
        id_area=request.args.get('id_area'),
        nivel=request.args.get('nivel'),
        solo_sin_atender=request.args.get('solo_sin_atender', 'false').lower() == 'true',
    )
    return jsonify([a.a_dict() for a in alertas]), 200


@alertas_bp.get('/<int:id_alerta>')
def obtener_alerta(id_alerta):
    alerta = repo.obtener(id_alerta)
    if alerta is None:
        return jsonify({"error": "Alerta no encontrada"}), 404
    return jsonify(alerta.a_dict()), 200


@alertas_bp.post('/')
def crear_alerta():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_medicion", "id_area", "tipo_alerta", "nivel", "descripcion"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    alerta = Alerta(
        id_medicion=data["id_medicion"],
        id_area=data["id_area"],
        tipo_alerta=data["tipo_alerta"],
        nivel=data["nivel"],
        descripcion=data["descripcion"],
        fecha_hora=data.get("fecha_hora"),
        id_estado=data.get("id_estado"),
    )

    try:
        nueva = repo.crear(alerta)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_medicion, id_area o id_estado inválido"}), 409

    return jsonify(nueva.a_dict()), 201


@alertas_bp.put('/<int:id_alerta>')
def actualizar_alerta(id_alerta):
    data = request.get_json(silent=True) or {}

    try:
        alerta = repo.actualizar(id_alerta, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if alerta is None:
        return jsonify({"error": "Alerta no encontrada"}), 404

    return jsonify(alerta.a_dict()), 200


@alertas_bp.put('/<int:id_alerta>/atender')
def atender_alerta(id_alerta):
    data = request.get_json(silent=True) or {}

    if not data.get("atendida_por"):
        return jsonify({"error": "El campo 'atendida_por' (id_usuario) es requerido"}), 400

    try:
        alerta = repo.atender(id_alerta, data["atendida_por"])
    except IntegrityError:
        return jsonify({"error": "atendida_por no corresponde a un usuario válido"}), 409

    if alerta is None:
        return jsonify({"error": "Alerta no encontrada o ya estaba atendida"}), 404

    return jsonify(alerta.a_dict()), 200


@alertas_bp.delete('/<int:id_alerta>')
def eliminar_alerta(id_alerta):
    if not repo.eliminar(id_alerta):
        return jsonify({"error": "Alerta no encontrada"}), 404
    return jsonify({"mensaje": "Alerta desactivada correctamente"}), 200

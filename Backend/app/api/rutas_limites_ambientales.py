from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.limite_ambiental import LimiteAmbiental
from app.repositories.limite_ambiental_repo import LimiteAmbientalRepository

limites_bp = Blueprint('limites_ambientales', __name__, url_prefix='/api/limites-ambientales')
repo = LimiteAmbientalRepository()


@limites_bp.get('/')
def listar_limites():
    incluir_historico = request.args.get('incluir_historico', 'false').lower() == 'true'
    limites = repo.listar(
        incluir_historico=incluir_historico,
        id_area=request.args.get('id_area'),
        id_parametro=request.args.get('id_parametro'),
    )
    return jsonify([l.a_dict() for l in limites]), 200


@limites_bp.get('/<int:id_limite>')
def obtener_limite(id_limite):
    limite = repo.obtener(id_limite)
    if limite is None:
        return jsonify({"error": "Límite ambiental no encontrado"}), 404
    return jsonify(limite.a_dict()), 200


@limites_bp.post('/')
def crear_limite():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_parametro", "id_area", "unidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data.get("limite_minimo") is None and data.get("limite_maximo") is None:
        return jsonify({"error": "Debe especificar al menos limite_minimo o limite_maximo"}), 400

    limite = LimiteAmbiental(
        id_parametro=data["id_parametro"],
        id_area=data["id_area"],
        limite_minimo=data.get("limite_minimo"),
        limite_maximo=data.get("limite_maximo"),
        unidad=data["unidad"],
        fuente_normativa=data.get("fuente_normativa"),
    )

    try:
        nuevo = repo.crear(limite, fecha_inicio=data.get("fecha_inicio"))
    except IntegrityError:
        return jsonify({"error": "id_parametro o id_area inválido"}), 409

    return jsonify(nuevo.a_dict()), 201


@limites_bp.put('/<int:id_limite>')
def actualizar_limite(id_limite):
    data = request.get_json(silent=True) or {}

    try:
        limite = repo.actualizar(id_limite, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if limite is None:
        return jsonify({"error": "Límite ambiental no encontrado"}), 404

    return jsonify(limite.a_dict()), 200


@limites_bp.put('/<int:id_limite>/cerrar')
def cerrar_limite(id_limite):
    data = request.get_json(silent=True) or {}
    limite = repo.cerrar(id_limite, fecha_fin=data.get("fecha_fin"))

    if limite is None:
        return jsonify({"error": "Límite ambiental no encontrado o ya estaba cerrado"}), 404

    return jsonify(limite.a_dict()), 200

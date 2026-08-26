from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.parametro_ambiental import ParametroAmbiental
from app.repositories.parametro_ambiental_repo import ParametroAmbientalRepository

parametros_bp = Blueprint('parametros_ambientales', __name__, url_prefix='/api/parametros-ambientales')
repo = ParametroAmbientalRepository()


@parametros_bp.get('/')
def listar_parametros():
    return jsonify([p.a_dict() for p in repo.listar()]), 200


@parametros_bp.get('/<int:id_parametro>')
def obtener_parametro(id_parametro):
    parametro = repo.obtener(id_parametro)
    if parametro is None:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404
    return jsonify(parametro.a_dict()), 200


@parametros_bp.post('/')
def crear_parametro():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "unidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    parametro = ParametroAmbiental(
        nombre=data["nombre"],
        unidad=data["unidad"],
        descripcion=data.get("descripcion"),
        limite_minimo=data.get("limite_minimo"),
        limite_maximo=data.get("limite_maximo"),
        nivel_riesgo=data.get("nivel_riesgo"),
    )

    nuevo = repo.crear(parametro)
    return jsonify(nuevo.a_dict()), 201


@parametros_bp.put('/<int:id_parametro>')
def actualizar_parametro(id_parametro):
    data = request.get_json(silent=True) or {}

    try:
        parametro = repo.actualizar(id_parametro, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if parametro is None:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404

    return jsonify(parametro.a_dict()), 200


@parametros_bp.delete('/<int:id_parametro>')
def eliminar_parametro(id_parametro):
    try:
        eliminado = repo.eliminar(id_parametro)
    except IntegrityError:
        return jsonify({
            "error": "No se puede eliminar: el parámetro está en uso por mediciones, "
                     "límites ambientales o predicciones existentes"
        }), 409

    if not eliminado:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404

    return jsonify({"mensaje": "Parámetro ambiental eliminado correctamente"}), 200

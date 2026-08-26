from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.modelo_ia import ModeloIA
from app.repositories.modelo_ia_repo import ModeloIARepository

modelos_ia_bp = Blueprint('modelos_ia', __name__, url_prefix='/api/modelos-ia')
repo = ModeloIARepository()


@modelos_ia_bp.get('/')
def listar_modelos():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'
    return jsonify([m.a_dict() for m in repo.listar(incluir_eliminados)]), 200


@modelos_ia_bp.get('/<int:id_modelo>')
def obtener_modelo(id_modelo):
    modelo = repo.obtener(id_modelo)
    if modelo is None:
        return jsonify({"error": "Modelo de IA no encontrado"}), 404
    return jsonify(modelo.a_dict()), 200


@modelos_ia_bp.post('/')
def crear_modelo():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "version", "tipo_modelo"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    modelo = ModeloIA(
        nombre=data["nombre"],
        version=data["version"],
        tipo_modelo=data["tipo_modelo"],
        descripcion=data.get("descripcion"),
        fecha_entrenamiento=data.get("fecha_entrenamiento"),
        precision_modelo=data.get("precision_modelo"),
        id_estado=data.get("id_estado"),
    )

    nuevo = repo.crear(modelo)
    return jsonify(nuevo.a_dict()), 201


@modelos_ia_bp.put('/<int:id_modelo>')
def actualizar_modelo(id_modelo):
    data = request.get_json(silent=True) or {}

    try:
        modelo = repo.actualizar(id_modelo, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_estado inválido"}), 409

    if modelo is None:
        return jsonify({"error": "Modelo de IA no encontrado"}), 404

    return jsonify(modelo.a_dict()), 200


@modelos_ia_bp.delete('/<int:id_modelo>')
def eliminar_modelo(id_modelo):
    if not repo.eliminar(id_modelo):
        return jsonify({"error": "Modelo de IA no encontrado"}), 404
    return jsonify({"mensaje": "Modelo de IA desactivado correctamente"}), 200

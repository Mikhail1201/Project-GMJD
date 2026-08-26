from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.area import Area
from app.repositories.area_repo import AreaRepository

areas_bp = Blueprint('areas', __name__, url_prefix='/api/areas')
repo = AreaRepository()


@areas_bp.get('/')
def listar_areas():
    incluir_eliminadas = request.args.get('incluir_eliminadas', 'false').lower() == 'true'
    return jsonify([a.a_dict() for a in repo.listar(incluir_eliminadas)]), 200


@areas_bp.get('/<int:id_area>')
def obtener_area(id_area):
    area = repo.obtener(id_area)
    if area is None:
        return jsonify({"error": "Área no encontrada"}), 404
    return jsonify(area.a_dict()), 200


@areas_bp.post('/')
def crear_area():
    data = request.get_json(silent=True) or {}

    if not data.get("nombre"):
        return jsonify({"error": "El campo 'nombre' es requerido"}), 400

    area = Area(
        nombre=data["nombre"],
        descripcion=data.get("descripcion"),
        ubicacion=data.get("ubicacion"),
        responsable_id=data.get("responsable_id"),
        id_estado=data.get("id_estado"),
    )

    try:
        nueva = repo.crear(area)
    except IntegrityError:
        return jsonify({"error": "responsable_id o id_estado inválido"}), 409

    return jsonify(nueva.a_dict()), 201


@areas_bp.put('/<int:id_area>')
def actualizar_area(id_area):
    data = request.get_json(silent=True) or {}

    try:
        area = repo.actualizar(id_area, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "responsable_id o id_estado inválido"}), 409

    if area is None:
        return jsonify({"error": "Área no encontrada"}), 404

    return jsonify(area.a_dict()), 200


@areas_bp.delete('/<int:id_area>')
def eliminar_area(id_area):
    if not repo.eliminar(id_area):
        return jsonify({"error": "Área no encontrada"}), 404
    return jsonify({"mensaje": "Área desactivada correctamente"}), 200

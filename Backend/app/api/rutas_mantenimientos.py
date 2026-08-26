from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.mantenimiento import Mantenimiento
from app.repositories.mantenimiento_repo import MantenimientoRepository

mantenimientos_bp = Blueprint('mantenimientos', __name__, url_prefix='/api/mantenimientos')
repo = MantenimientoRepository()


@mantenimientos_bp.get('/')
def listar_mantenimientos():
    mantenimientos = repo.listar(
        id_area=request.args.get('id_area'),
        responsable_id=request.args.get('responsable_id'),
        tipo=request.args.get('tipo'),
        fecha_desde=request.args.get('fecha_desde'),
        fecha_hasta=request.args.get('fecha_hasta'),
    )
    return jsonify([m.a_dict() for m in mantenimientos]), 200


@mantenimientos_bp.get('/<int:id_mantenimiento>')
def obtener_mantenimiento(id_mantenimiento):
    mantenimiento = repo.obtener(id_mantenimiento)
    if mantenimiento is None:
        return jsonify({"error": "Mantenimiento no encontrado"}), 404
    return jsonify(mantenimiento.a_dict()), 200


@mantenimientos_bp.post('/')
def crear_mantenimiento():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "tipo", "descripcion"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    mantenimiento = Mantenimiento(
        id_area=data["id_area"],
        tipo=data["tipo"],
        descripcion=data["descripcion"],
        fecha=data.get("fecha"),
        responsable_id=data.get("responsable_id"),
        resultado=data.get("resultado"),
        proximo_mantenimiento=data.get("proximo_mantenimiento"),
    )

    try:
        nuevo = repo.crear(mantenimiento)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_area o responsable_id inválido"}), 409

    return jsonify(nuevo.a_dict()), 201


@mantenimientos_bp.put('/<int:id_mantenimiento>')
def actualizar_mantenimiento(id_mantenimiento):
    data = request.get_json(silent=True) or {}

    try:
        mantenimiento = repo.actualizar(id_mantenimiento, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if mantenimiento is None:
        return jsonify({"error": "Mantenimiento no encontrado"}), 404

    return jsonify(mantenimiento.a_dict()), 200

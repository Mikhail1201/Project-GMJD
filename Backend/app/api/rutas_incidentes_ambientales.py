from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.incidente_ambiental import IncidenteAmbiental
from app.repositories.incidente_ambiental_repo import IncidenteAmbientalRepository

incidentes_bp = Blueprint('incidentes_ambientales', __name__, url_prefix='/api/incidentes-ambientales')
repo = IncidenteAmbientalRepository()


@incidentes_bp.get('/')
def listar_incidentes():
    incidentes = repo.listar(
        incluir_eliminados=request.args.get('incluir_eliminados', 'false').lower() == 'true',
        id_area=request.args.get('id_area'),
        severidad=request.args.get('severidad'),
        solo_abiertos=request.args.get('solo_abiertos', 'false').lower() == 'true',
    )
    return jsonify([i.a_dict() for i in incidentes]), 200


@incidentes_bp.get('/<int:id_incidente>')
def obtener_incidente(id_incidente):
    incidente = repo.obtener(id_incidente)
    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404
    return jsonify(incidente.a_dict()), 200


@incidentes_bp.post('/')
def crear_incidente():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_area", "titulo", "descripcion", "severidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    incidente = IncidenteAmbiental(
        id_area=data["id_area"],
        id_alerta=data.get("id_alerta"),
        titulo=data["titulo"],
        descripcion=data["descripcion"],
        fecha_inicio=data.get("fecha_inicio"),
        severidad=data["severidad"],
        causa=data.get("causa"),
        id_estado=data.get("id_estado"),
        responsable_id=data.get("responsable_id"),
    )

    try:
        nuevo = repo.crear(incidente)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "id_area, id_alerta, id_estado o responsable_id inválido"}), 409

    return jsonify(nuevo.a_dict()), 201


@incidentes_bp.put('/<int:id_incidente>')
def actualizar_incidente(id_incidente):
    data = request.get_json(silent=True) or {}

    try:
        incidente = repo.actualizar(id_incidente, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": "responsable_id inválido"}), 409

    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404

    return jsonify(incidente.a_dict()), 200


@incidentes_bp.put('/<int:id_incidente>/resolver')
def resolver_incidente(id_incidente):
    data = request.get_json(silent=True) or {}

    if not data.get("acciones_realizadas"):
        return jsonify({"error": "El campo 'acciones_realizadas' es requerido para resolver el incidente"}), 400

    incidente = repo.resolver(id_incidente, data["acciones_realizadas"])

    if incidente is None:
        return jsonify({"error": "Incidente ambiental no encontrado o ya estaba resuelto"}), 404

    return jsonify(incidente.a_dict()), 200


@incidentes_bp.delete('/<int:id_incidente>')
def eliminar_incidente(id_incidente):
    if not repo.eliminar(id_incidente):
        return jsonify({"error": "Incidente ambiental no encontrado"}), 404
    return jsonify({"mensaje": "Incidente ambiental desactivado correctamente"}), 200

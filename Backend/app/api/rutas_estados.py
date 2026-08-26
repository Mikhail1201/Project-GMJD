from flask import Blueprint, jsonify

from app.repositories.estado_repo import EstadoRepository

estados_bp = Blueprint('estados', __name__, url_prefix='/api/estados')
repo = EstadoRepository()


@estados_bp.get('/')
def listar_estados():
    return jsonify([e.a_dict() for e in repo.listar()]), 200

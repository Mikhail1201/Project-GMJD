from flask import Blueprint, jsonify

from app.repositories.rol_repo import RolRepository

roles_bp = Blueprint('roles', __name__, url_prefix='/api/roles')
repo = RolRepository()


@roles_bp.get('/')
def listar_roles():
    return jsonify([r.a_dict() for r in repo.listar()]), 200

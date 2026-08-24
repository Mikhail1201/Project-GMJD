from flask import Blueprint, jsonify
from sqlalchemy import text

from extensions import engine

roles_bp = Blueprint('roles', __name__, url_prefix='/api/roles')


@roles_bp.get('/')
def listar_roles():
    query = "SELECT id_rol, nombre FROM roles ORDER BY id_rol"
    with engine.connect() as con:
        result = con.execute(text(query))
        roles = [dict(row._mapping) for row in result]

    return jsonify(roles), 200
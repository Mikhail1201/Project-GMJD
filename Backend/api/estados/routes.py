from flask import Blueprint, jsonify
from sqlalchemy import text

from extensions import engine

estados_bp = Blueprint('estados', __name__, url_prefix='/api/estados')


@estados_bp.get('/')
def listar_estados():
    query = "SELECT id_estado, nombre FROM estados ORDER BY id_estado"
    with engine.connect() as con:
        result = con.execute(text(query))
        estados = [dict(row._mapping) for row in result]

    return jsonify(estados), 200
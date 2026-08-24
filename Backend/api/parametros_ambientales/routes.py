# api/parametros_ambientales/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine

parametros_bp = Blueprint('parametros_ambientales', __name__, url_prefix='/api/parametros-ambientales')


# ---------- READ (listar todos) ----------
@parametros_bp.get('/')
def listar_parametros():
    query = """
        SELECT id_parametro, nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo
        FROM parametros_ambientales
        ORDER BY id_parametro
    """
    with engine.connect() as con:
        result = con.execute(text(query))
        parametros = [dict(row._mapping) for row in result]

    return jsonify(parametros), 200


# ---------- READ (uno solo) ----------
@parametros_bp.get('/<int:id_parametro>')
def obtener_parametro(id_parametro):
    query = """
        SELECT id_parametro, nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo
        FROM parametros_ambientales
        WHERE id_parametro = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_parametro})
        parametro = result.mappings().first()

    if parametro is None:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404

    return jsonify(dict(parametro)), 200


# ---------- CREATE ----------
@parametros_bp.post('/')
def crear_parametro():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["nombre", "unidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    query = """
        INSERT INTO parametros_ambientales (nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo)
        VALUES (:nombre, :unidad, :descripcion, :limite_minimo, :limite_maximo, :nivel_riesgo)
        RETURNING id_parametro, nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo
    """
    params = {
        "nombre": data["nombre"],
        "unidad": data["unidad"],
        "descripcion": data.get("descripcion"),
        "limite_minimo": data.get("limite_minimo"),
        "limite_maximo": data.get("limite_maximo"),
        "nivel_riesgo": data.get("nivel_riesgo"),
    }

    with engine.begin() as con:
        result = con.execute(text(query), params)
        nuevo_parametro = result.mappings().first()

    return jsonify(dict(nuevo_parametro)), 201


# ---------- UPDATE ----------
@parametros_bp.put('/<int:id_parametro>')
def actualizar_parametro(id_parametro):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["nombre", "unidad", "descripcion", "limite_minimo", "limite_maximo", "nivel_riesgo"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({"error": "No se enviaron campos válidos para actualizar"}), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE parametros_ambientales
        SET {set_clause}
        WHERE id_parametro = :id
        RETURNING id_parametro, nombre, unidad, descripcion, limite_minimo, limite_maximo, nivel_riesgo
    """
    actualizaciones["id"] = id_parametro

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        parametro_actualizado = result.mappings().first()

    if parametro_actualizado is None:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404

    return jsonify(dict(parametro_actualizado)), 200


# ---------- DELETE (real, con validación de FK) ----------
@parametros_bp.delete('/<int:id_parametro>')
def eliminar_parametro(id_parametro):
    query = "DELETE FROM parametros_ambientales WHERE id_parametro = :id RETURNING id_parametro"

    try:
        with engine.begin() as con:
            result = con.execute(text(query), {"id": id_parametro})
            parametro = result.mappings().first()
    except IntegrityError:
        return jsonify({
            "error": "No se puede eliminar: el parámetro está en uso por mediciones, "
                     "límites ambientales o predicciones existentes"
        }), 409

    if parametro is None:
        return jsonify({"error": "Parámetro ambiental no encontrado"}), 404

    return jsonify({"mensaje": "Parámetro ambiental eliminado correctamente"}), 200
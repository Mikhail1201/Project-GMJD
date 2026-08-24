# api/limites_ambientales/routes.py
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from extensions import engine

limites_bp = Blueprint('limites_ambientales', __name__, url_prefix='/api/limites-ambientales')


# ---------- READ (listar, por defecto solo vigentes) ----------
@limites_bp.get('/')
def listar_limites():
    incluir_historico = request.args.get('incluir_historico', 'false').lower() == 'true'
    id_area = request.args.get('id_area')
    id_parametro = request.args.get('id_parametro')

    filtros = []
    params = {}

    if not incluir_historico:
        filtros.append("fecha_fin IS NULL")
    if id_area:
        filtros.append("id_area = :id_area")
        params["id_area"] = id_area
    if id_parametro:
        filtros.append("id_parametro = :id_parametro")
        params["id_parametro"] = id_parametro

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""

    query = f"""
        SELECT id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
               unidad, fecha_inicio, fecha_fin, fuente_normativa
        FROM limites_ambientales
        {where_clause}
        ORDER BY id_area, id_parametro, fecha_inicio DESC
    """
    with engine.connect() as con:
        result = con.execute(text(query), params)
        limites = [dict(row._mapping) for row in result]

    return jsonify(limites), 200


# ---------- READ (uno solo) ----------
@limites_bp.get('/<int:id_limite>')
def obtener_limite(id_limite):
    query = """
        SELECT id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
               unidad, fecha_inicio, fecha_fin, fuente_normativa
        FROM limites_ambientales
        WHERE id_limite = :id
    """
    with engine.connect() as con:
        result = con.execute(text(query), {"id": id_limite})
        limite = result.mappings().first()

    if limite is None:
        return jsonify({"error": "Límite ambiental no encontrado"}), 404

    return jsonify(dict(limite)), 200


# ---------- CREATE (nueva versión: cierra la vigente anterior si existe) ----------
@limites_bp.post('/')
def crear_limite():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["id_parametro", "id_area", "unidad"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    if data.get("limite_minimo") is None and data.get("limite_maximo") is None:
        return jsonify({"error": "Debe especificar al menos limite_minimo o limite_maximo"}), 400

    fecha_inicio = data.get("fecha_inicio")  # si no viene, se usa CURRENT_DATE

    query_cerrar = """
        UPDATE limites_ambientales
        SET fecha_fin = COALESCE(:fecha_inicio, CURRENT_DATE)
        WHERE id_parametro = :id_parametro AND id_area = :id_area AND fecha_fin IS NULL
    """
    query_insertar = """
        INSERT INTO limites_ambientales
            (id_parametro, id_area, limite_minimo, limite_maximo, unidad, fecha_inicio, fuente_normativa)
        VALUES
            (:id_parametro, :id_area, :limite_minimo, :limite_maximo, :unidad,
             COALESCE(:fecha_inicio, CURRENT_DATE), :fuente_normativa)
        RETURNING id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
                  unidad, fecha_inicio, fecha_fin, fuente_normativa
    """
    params = {
        "id_parametro": data["id_parametro"],
        "id_area": data["id_area"],
        "limite_minimo": data.get("limite_minimo"),
        "limite_maximo": data.get("limite_maximo"),
        "unidad": data["unidad"],
        "fecha_inicio": fecha_inicio,
        "fuente_normativa": data.get("fuente_normativa"),
    }

    try:
        with engine.begin() as con:
            # Un solo begin() => cerrar el anterior + insertar el nuevo es atómico
            con.execute(text(query_cerrar), params)
            result = con.execute(text(query_insertar), params)
            nuevo_limite = result.mappings().first()
    except IntegrityError:
        return jsonify({"error": "id_parametro o id_area inválido"}), 409

    return jsonify(dict(nuevo_limite)), 201


# ---------- UPDATE (solo corrige datos, no fechas) ----------
@limites_bp.put('/<int:id_limite>')
def actualizar_limite(id_limite):
    data = request.get_json(silent=True) or {}

    campos_permitidos = ["limite_minimo", "limite_maximo", "unidad", "fuente_normativa"]
    actualizaciones = {k: v for k, v in data.items() if k in campos_permitidos}

    if not actualizaciones:
        return jsonify({
            "error": "Solo se pueden actualizar 'limite_minimo', 'limite_maximo', "
                     "'unidad' o 'fuente_normativa'. Para cambiar fechas usa /cerrar o crea una nueva versión."
        }), 400

    set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
    query = f"""
        UPDATE limites_ambientales
        SET {set_clause}
        WHERE id_limite = :id
        RETURNING id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
                  unidad, fecha_inicio, fecha_fin, fuente_normativa
    """
    actualizaciones["id"] = id_limite

    with engine.begin() as con:
        result = con.execute(text(query), actualizaciones)
        limite_actualizado = result.mappings().first()

    if limite_actualizado is None:
        return jsonify({"error": "Límite ambiental no encontrado"}), 404

    return jsonify(dict(limite_actualizado)), 200


# ---------- CERRAR (da de baja un límite vigente, sin reemplazarlo) ----------
@limites_bp.put('/<int:id_limite>/cerrar')
def cerrar_limite(id_limite):
    data = request.get_json(silent=True) or {}
    fecha_fin = data.get("fecha_fin")  # si no viene, se usa CURRENT_DATE

    query = """
        UPDATE limites_ambientales
        SET fecha_fin = COALESCE(:fecha_fin, CURRENT_DATE)
        WHERE id_limite = :id AND fecha_fin IS NULL
        RETURNING id_limite, id_parametro, id_area, limite_minimo, limite_maximo,
                  unidad, fecha_inicio, fecha_fin, fuente_normativa
    """
    with engine.begin() as con:
        result = con.execute(text(query), {"fecha_fin": fecha_fin, "id": id_limite})
        limite = result.mappings().first()

    if limite is None:
        return jsonify({"error": "Límite ambiental no encontrado o ya estaba cerrado"}), 404

    return jsonify(dict(limite)), 200


# No hay DELETE: limites_ambientales es histórico versionado, no se borra.
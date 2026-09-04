from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.models.sensor import Sensor
from app.repositories.sensor_repo import SensorRepository

sensores_bp = Blueprint('sensores', __name__, url_prefix='/api/sensores')
repo = SensorRepository()

MENSAJE_FK = ("id_area, id_parametro, responsable_id o id_estado invalido, "
              "o el codigo/numero de serie ya existe")


@sensores_bp.get('/')
def listar_sensores():
    incluir_eliminados = request.args.get('incluir_eliminados', 'false').lower() == 'true'
    solo_principales = request.args.get('solo_principales', 'false').lower() == 'true'
    calibracion_vencida = request.args.get('calibracion_vencida', 'false').lower() == 'true'

    sensores = repo.listar(
        incluir_eliminados=incluir_eliminados,
        id_area=request.args.get('id_area'),
        id_parametro=request.args.get('id_parametro'),
        id_estado=request.args.get('id_estado'),
        responsable_id=request.args.get('responsable_id'),
        solo_principales=solo_principales,
        calibracion_vencida=calibracion_vencida,
        busqueda=request.args.get('busqueda'),
    )
    return jsonify([s.a_dict() for s in sensores]), 200


@sensores_bp.get('/resolver')
def resolver_sensor():
    """Devuelve el sensor principal de un (area, parametro). Es el mismo
    criterio que usa el backend para completar mediciones.id_sensor."""
    id_area = request.args.get('id_area')
    id_parametro = request.args.get('id_parametro')

    if not id_area or not id_parametro:
        return jsonify({"error": "Se requieren 'id_area' e 'id_parametro'"}), 400

    sensor = repo.obtener_principal(id_area, id_parametro)
    if sensor is None:
        return jsonify({"error": "No hay un sensor principal para esa area y parametro"}), 404

    return jsonify(sensor.a_dict()), 200


@sensores_bp.get('/<int:id_sensor>')
def obtener_sensor(id_sensor):
    sensor = repo.obtener(id_sensor)
    if sensor is None:
        return jsonify({"error": "Sensor no encontrado"}), 404
    return jsonify(sensor.a_dict()), 200


@sensores_bp.post('/')
def crear_sensor():
    data = request.get_json(silent=True) or {}

    campos_requeridos = ["codigo", "nombre", "id_area", "id_parametro"]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos requeridos: {', '.join(faltantes)}"}), 400

    sensor = Sensor(
        codigo=data["codigo"],
        nombre=data["nombre"],
        descripcion=data.get("descripcion"),
        id_area=data["id_area"],
        id_parametro=data["id_parametro"],
        ubicacion_detalle=data.get("ubicacion_detalle"),
        modelo=data.get("modelo"),
        fabricante=data.get("fabricante"),
        numero_serie=data.get("numero_serie"),
        protocolo=data.get("protocolo"),
        rango_minimo=data.get("rango_minimo"),
        rango_maximo=data.get("rango_maximo"),
        precision_sensor=data.get("precision_sensor"),
        frecuencia_muestreo_seg=data.get("frecuencia_muestreo_seg"),
        fecha_instalacion=data.get("fecha_instalacion"),
        fecha_ultima_calibracion=data.get("fecha_ultima_calibracion"),
        fecha_proxima_calibracion=data.get("fecha_proxima_calibracion"),
        responsable_id=data.get("responsable_id"),
        id_estado=data.get("id_estado"),
    )

    try:
        nuevo = repo.crear(sensor)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": MENSAJE_FK}), 409

    return jsonify(nuevo.a_dict()), 201


@sensores_bp.put('/<int:id_sensor>')
def actualizar_sensor(id_sensor):
    data = request.get_json(silent=True) or {}

    try:
        sensor = repo.actualizar(id_sensor, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        return jsonify({"error": MENSAJE_FK}), 409

    if sensor is None:
        return jsonify({"error": "Sensor no encontrado"}), 404

    return jsonify(sensor.a_dict()), 200


@sensores_bp.put('/<int:id_sensor>/principal')
def marcar_principal(id_sensor):
    try:
        sensor = repo.marcar_principal(id_sensor)
    except IntegrityError:
        return jsonify({"error": "No se pudo marcar como principal"}), 409

    if sensor is None:
        return jsonify({"error": "Sensor no encontrado"}), 404

    return jsonify(sensor.a_dict()), 200


@sensores_bp.put('/<int:id_sensor>/calibracion')
def registrar_calibracion(id_sensor):
    data = request.get_json(silent=True) or {}

    try:
        sensor = repo.registrar_calibracion(
            id_sensor,
            fecha=data.get("fecha"),
            meses_proxima=data.get("meses_proxima", 12),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if sensor is None:
        return jsonify({"error": "Sensor no encontrado"}), 404

    return jsonify(sensor.a_dict()), 200


@sensores_bp.delete('/<int:id_sensor>')
def eliminar_sensor(id_sensor):
    if not repo.eliminar(id_sensor):
        return jsonify({"error": "Sensor no encontrado"}), 404
    return jsonify({"mensaje": "Sensor desactivado correctamente"}), 200

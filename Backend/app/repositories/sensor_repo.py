from sqlalchemy import text

from app.core.constants import NOMBRE_ESTADO_ACTIVO, NOMBRE_ESTADO_ELIMINADO
from app.core.database import engine
from app.models.sensor import Sensor
from app.repositories.catalogos import obtener_id_estado

PROTOCOLOS_VALIDOS = [
    "1-Wire", "I2C", "SPI", "Analogico", "4-20 mA",
    "Modbus RTU", "Modbus TCP", "RS-232", "RS-485", "USB", "Wi-Fi",
]

# Columnas reales de la tabla (sin los alias de los JOIN): se usan en los
# RETURNING de INSERT/UPDATE, donde no hay JOIN disponible.
COLUMNAS_TABLA = """id_sensor, codigo, nombre, descripcion, id_area, id_parametro,
                 ubicacion_detalle, modelo, fabricante, numero_serie, protocolo,
                 rango_minimo, rango_maximo, precision_sensor, frecuencia_muestreo_seg,
                 fecha_instalacion, fecha_ultima_calibracion, fecha_proxima_calibracion,
                 es_principal, responsable_id, id_estado"""


def resolver_id_sensor(con, id_area, id_parametro) -> int | None:
    """Devuelve el id_sensor 'principal' de ese (area, parametro), o None.

    Recibe una conexion YA ABIERTA para participar de la misma transaccion
    que el INSERT que la llama (ver MedicionRepository.crear). Gracias a esto
    el ESP32 no necesita saber que sensor le corresponde: manda id_area e
    id_parametro como siempre, y el backend completa la relacion.
    """
    fila = con.execute(text("""
        SELECT id_sensor
        FROM sensores
        WHERE id_area = :id_area AND id_parametro = :id_parametro AND es_principal
    """), {"id_area": id_area, "id_parametro": id_parametro}).first()

    return fila[0] if fila else None


class SensorRepository:
    COLUMNAS = """s.id_sensor, s.codigo, s.nombre, s.descripcion,
               s.id_area, ar.nombre AS nombre_area,
               s.id_parametro, p.nombre AS nombre_parametro,
               p.unidad AS unidad_parametro,
               s.ubicacion_detalle, s.modelo, s.fabricante, s.numero_serie,
               s.protocolo, s.rango_minimo, s.rango_maximo, s.precision_sensor,
               s.frecuencia_muestreo_seg, s.fecha_instalacion,
               s.fecha_ultima_calibracion, s.fecha_proxima_calibracion,
               s.es_principal, s.responsable_id,
               u.nombre || ' ' || u.apellido AS nombre_responsable,
               s.id_estado, e.nombre AS nombre_estado"""

    JOINS = """FROM sensores s
        JOIN areas ar                 ON ar.id_area = s.id_area
        JOIN parametros_ambientales p ON p.id_parametro = s.id_parametro
        JOIN estados e                ON e.id_estado = s.id_estado
        LEFT JOIN usuarios u          ON u.id_usuario = s.responsable_id"""

    def __init__(self, db_engine=None):
        self.engine = db_engine or engine

    def listar(self, incluir_eliminados: bool = False, id_area=None,
               id_parametro=None, id_estado=None, responsable_id=None,
               solo_principales: bool = False, calibracion_vencida: bool = False,
               busqueda=None) -> list[Sensor]:
        filtros = []
        params = {}

        if not incluir_eliminados:
            filtros.append("s.id_estado != :estado_eliminado")
            params["estado_eliminado"] = obtener_id_estado(NOMBRE_ESTADO_ELIMINADO)
        if id_area:
            filtros.append("s.id_area = :id_area")
            params["id_area"] = id_area
        if id_parametro:
            filtros.append("s.id_parametro = :id_parametro")
            params["id_parametro"] = id_parametro
        if id_estado:
            filtros.append("s.id_estado = :id_estado")
            params["id_estado"] = id_estado
        if responsable_id:
            filtros.append("s.responsable_id = :responsable_id")
            params["responsable_id"] = responsable_id
        if solo_principales:
            filtros.append("s.es_principal")
        if calibracion_vencida:
            filtros.append("s.fecha_proxima_calibracion < CURRENT_TIMESTAMP")
        if busqueda:
            filtros.append(
                "(s.codigo ILIKE :busqueda OR s.nombre ILIKE :busqueda"
                " OR s.numero_serie ILIKE :busqueda OR s.modelo ILIKE :busqueda"
                " OR s.fabricante ILIKE :busqueda)"
            )
            params["busqueda"] = f"%{busqueda}%"

        where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ""
        query = f"""
            SELECT {self.COLUMNAS}
            {self.JOINS}
            {where_clause}
            ORDER BY s.id_area, s.id_parametro, s.codigo
        """
        with self.engine.connect() as con:
            return [Sensor.desde_fila(row._mapping) for row in con.execute(text(query), params)]

    def obtener(self, id_sensor: int) -> Sensor | None:
        query = f"SELECT {self.COLUMNAS} {self.JOINS} WHERE s.id_sensor = :id"
        with self.engine.connect() as con:
            fila = con.execute(text(query), {"id": id_sensor}).mappings().first()
        return Sensor.desde_fila(fila)

    def obtener_principal(self, id_area: int, id_parametro: int) -> Sensor | None:
        query = f"""
            SELECT {self.COLUMNAS} {self.JOINS}
            WHERE s.id_area = :id_area AND s.id_parametro = :id_parametro
              AND s.es_principal
        """
        with self.engine.connect() as con:
            fila = con.execute(
                text(query), {"id_area": id_area, "id_parametro": id_parametro}
            ).mappings().first()
        return Sensor.desde_fila(fila)

    def crear(self, sensor: Sensor) -> Sensor:
        self._validar(sensor.protocolo, sensor.rango_minimo, sensor.rango_maximo)

        query = f"""
            INSERT INTO sensores (
                codigo, nombre, descripcion, id_area, id_parametro, ubicacion_detalle,
                modelo, fabricante, numero_serie, protocolo,
                rango_minimo, rango_maximo, precision_sensor, frecuencia_muestreo_seg,
                fecha_instalacion, fecha_ultima_calibracion, fecha_proxima_calibracion,
                responsable_id, id_estado
            ) VALUES (
                :codigo, :nombre, :descripcion, :id_area, :id_parametro, :ubicacion_detalle,
                :modelo, :fabricante, :numero_serie, :protocolo,
                :rango_minimo, :rango_maximo, :precision_sensor, :frecuencia_muestreo_seg,
                COALESCE(:fecha_instalacion, CURRENT_TIMESTAMP),
                :fecha_ultima_calibracion, :fecha_proxima_calibracion,
                :responsable_id, :id_estado
            )
            RETURNING {COLUMNAS_TABLA}
        """
        params = {
            "codigo": sensor.codigo,
            "nombre": sensor.nombre,
            "descripcion": sensor.descripcion,
            "id_area": sensor.id_area,
            "id_parametro": sensor.id_parametro,
            "ubicacion_detalle": sensor.ubicacion_detalle,
            "modelo": sensor.modelo,
            "fabricante": sensor.fabricante,
            "numero_serie": sensor.numero_serie,
            "protocolo": sensor.protocolo,
            "rango_minimo": sensor.rango_minimo,
            "rango_maximo": sensor.rango_maximo,
            "precision_sensor": sensor.precision_sensor,
            "frecuencia_muestreo_seg": sensor.frecuencia_muestreo_seg,
            "fecha_instalacion": sensor.fecha_instalacion,
            "fecha_ultima_calibracion": sensor.fecha_ultima_calibracion,
            "fecha_proxima_calibracion": sensor.fecha_proxima_calibracion,
            "responsable_id": sensor.responsable_id,
            "id_estado": sensor.id_estado or obtener_id_estado(NOMBRE_ESTADO_ACTIVO),
        }
        with self.engine.begin() as con:
            fila = con.execute(text(query), params).mappings().first()
        return Sensor.desde_fila(fila)

    def actualizar(self, id_sensor: int, campos: dict) -> Sensor | None:
        # es_principal NO esta aqui a proposito: se cambia solo con
        # marcar_principal(), que limpia el principal anterior en la misma
        # transaccion. Si se pudiera editar aqui, el indice unico parcial
        # ux_sensores_principal_area_param reventaria con IntegrityError.
        campos_permitidos = [
            "codigo", "nombre", "descripcion", "id_area", "id_parametro",
            "ubicacion_detalle", "modelo", "fabricante", "numero_serie", "protocolo",
            "rango_minimo", "rango_maximo", "precision_sensor",
            "frecuencia_muestreo_seg", "fecha_ultima_calibracion",
            "fecha_proxima_calibracion", "responsable_id", "id_estado",
        ]
        actualizaciones = {k: v for k, v in campos.items() if k in campos_permitidos}
        if not actualizaciones:
            raise ValueError("No se enviaron campos validos para actualizar")

        self._validar(
            actualizaciones.get("protocolo"),
            actualizaciones.get("rango_minimo"),
            actualizaciones.get("rango_maximo"),
        )

        set_clause = ", ".join(f"{campo} = :{campo}" for campo in actualizaciones)
        query = f"""
            UPDATE sensores
            SET {set_clause}
            WHERE id_sensor = :id
            RETURNING {COLUMNAS_TABLA}
        """
        actualizaciones["id"] = id_sensor
        with self.engine.begin() as con:
            fila = con.execute(text(query), actualizaciones).mappings().first()
        return Sensor.desde_fila(fila)

    def marcar_principal(self, id_sensor: int) -> Sensor | None:
        """Marca el sensor como principal de su (area, parametro) y quita la
        marca del que la tuviera. Ambos UPDATE van en la misma transaccion
        porque el indice unico parcial no admite dos principales a la vez."""
        query_limpiar = """
            UPDATE sensores
            SET es_principal = false
            WHERE es_principal
              AND id_sensor <> :id
              AND (id_area, id_parametro) = (
                  SELECT id_area, id_parametro FROM sensores WHERE id_sensor = :id
              )
        """
        query_marcar = f"""
            UPDATE sensores
            SET es_principal = true
            WHERE id_sensor = :id
            RETURNING {COLUMNAS_TABLA}
        """
        with self.engine.begin() as con:
            con.execute(text(query_limpiar), {"id": id_sensor})
            fila = con.execute(text(query_marcar), {"id": id_sensor}).mappings().first()
        return Sensor.desde_fila(fila)

    def registrar_calibracion(self, id_sensor: int, fecha=None,
                              meses_proxima: int = 12) -> Sensor | None:
        try:
            meses_proxima = int(meses_proxima)
        except (TypeError, ValueError):
            raise ValueError("'meses_proxima' debe ser un numero entero de meses")

        if meses_proxima <= 0:
            raise ValueError("'meses_proxima' debe ser mayor que cero")

        query = f"""
            UPDATE sensores
            SET fecha_ultima_calibracion  = COALESCE(:fecha, CURRENT_TIMESTAMP),
                fecha_proxima_calibracion = COALESCE(:fecha, CURRENT_TIMESTAMP)
                                            + make_interval(months => :meses)
            WHERE id_sensor = :id
            RETURNING {COLUMNAS_TABLA}
        """
        with self.engine.begin() as con:
            fila = con.execute(
                text(query), {"id": id_sensor, "fecha": fecha, "meses": meses_proxima}
            ).mappings().first()
        return Sensor.desde_fila(fila)

    def eliminar(self, id_sensor: int) -> bool:
        """Soft delete. Ademas quita es_principal para que un sensor dado de
        baja deje de capturar las mediciones nuevas."""
        query = """
            UPDATE sensores
            SET id_estado = :estado_eliminado,
                es_principal = false
            WHERE id_sensor = :id
            RETURNING id_sensor
        """
        with self.engine.begin() as con:
            fila = con.execute(text(query), {
                "estado_eliminado": obtener_id_estado(NOMBRE_ESTADO_ELIMINADO),
                "id": id_sensor,
            }).mappings().first()
        return fila is not None

    @staticmethod
    def _validar(protocolo, rango_minimo, rango_maximo):
        if protocolo is not None and protocolo not in PROTOCOLOS_VALIDOS:
            raise ValueError(f"protocolo debe ser uno de: {', '.join(PROTOCOLOS_VALIDOS)}")

        if rango_minimo is not None and rango_maximo is not None:
            try:
                if float(rango_minimo) > float(rango_maximo):
                    raise ValueError("'rango_minimo' no puede ser mayor que 'rango_maximo'")
            except (TypeError, ValueError) as e:
                if isinstance(e, ValueError) and "rango_minimo" in str(e):
                    raise
                raise ValueError("'rango_minimo' y 'rango_maximo' deben ser numericos")

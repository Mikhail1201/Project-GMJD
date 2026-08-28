"""
====================================================================
PROYECTO: SISTEMA DE MONITOREO AMBIENTAL - MONÓMEROS S.A.
MODULO: FIRMWARE DE TELEMETRÍA Y ADQUISICIÓN DE DATOS (ESP32)
INTEGRANTES: GRUPO 8
LENGUAJE: MICROPYTHON CON ARQUITECTURA ORIENTADA A OBJETOS (POO)
====================================================================
"""

import network
import urequests
import ujson
import utime
from machine import Pin, I2C, ADC
import dht
from i2c_lcd import I2cLcd


# ==================================================================
# CONFIGURACIÓN GENERAL
# ==================================================================

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# --------------------------------------------------------------
# CONEXION AL BACKEND LOCAL
# --------------------------------------------------------------
#
# host.wokwi.internal es un hostname especial que el simulador de
# Wokwi (web y extension de VS Code) resuelve automaticamente hacia
# el "localhost" real de la maquina donde corre la simulacion. Ya no
# hace falta LocalTunnel ni ninguna URL publica: solo se necesita el
# backend Flask corriendo en esa misma maquina, escuchando en todas
# las interfaces (0.0.0.0), no solo en 127.0.0.1:
#
# Windows:
#
# Flask:
#   flask --app app run --host=0.0.0.0 --port=8000
#
# --------------------------------------------------------------

API_BASE_URL = "http://host.wokwi.internal:8000/api"

# --------------------------------------------------------------
# VALORES VALIDOS DE calidad_dato (ver Backend/app/repositories/
# medicion_repo.py -> CALIDADES_VALIDAS). Cualquier otro valor que
# no sea uno de estos tres, el backend lo rechaza con error 400.
# --------------------------------------------------------------

CALIDAD_VALIDA = "valida"
CALIDAD_SOSPECHOSA = "sospechosa"
CALIDAD_INVALIDA = "invalida"


# ==================================================================
# PARTE 1: GESTOR DE RED
# ==================================================================

class NetworkManager:
    """Gestiona la conexión Wi-Fi del ESP32."""

    def __init__(self, ssid: str, password: str):

        self.ssid = ssid
        self.password = password

        self.wlan = network.WLAN(
            network.STA_IF
        )

    def connect(self):

        print()
        print("[RED] Activando Wi-Fi...")

        self.wlan.active(True)

        if self.wlan.isconnected():

            print(
                "[RED] Wi-Fi ya estaba conectado."
            )

            print(
                "[RED] IP:",
                self.wlan.ifconfig()[0]
            )

            return True

        print(
            "[RED] Conectando a:",
            self.ssid
        )

        try:

            self.wlan.connect(
                self.ssid,
                self.password
            )

        except Exception as e:

            print(
                "[RED] Error iniciando Wi-Fi:",
                repr(e)
            )

            return False

        intentos = 0

        while (
            not self.wlan.isconnected()
            and intentos < 40
        ):

            intentos += 1

            print(
                "[RED] Esperando Wi-Fi...",
                intentos
            )

            utime.sleep_ms(500)

        if self.wlan.isconnected():

            config = self.wlan.ifconfig()

            print()
            print(
                "[RED] Conexión establecida."
            )

            print(
                "[RED] IP      :",
                config[0]
            )

            print(
                "[RED] MASK    :",
                config[1]
            )

            print(
                "[RED] GATEWAY :",
                config[2]
            )

            print(
                "[RED] DNS     :",
                config[3]
            )

            return True

        print()
        print(
            "[RED] ERROR: No se pudo conectar a Wi-Fi."
        )

        return False

    def is_connected(self):

        try:

            return self.wlan.isconnected()

        except Exception:

            return False


# ==================================================================
# PARTE 2: SENSOR AMBIENTAL
# ==================================================================

class EnvironmentalSensors:
    """Gestiona DHT22 (temperatura/humedad) y MQ-2 (gas, wokwi-gas-sensor)."""

    # ADC de 12 bits (0-4095) sobre un rango de 0-3.3V.
    ADC_MAX = 4095

    # Rango de referencia en ppm que ya usaban las alertas y el resto
    # del sistema (mismo rango que la version anterior simulada con
    # urandom): 15 ppm = "aire limpio" / linea base, 650 ppm = tope
    # del sensor. El limite de alerta de MonomerosController.LIMIT_GAS_MAX
    # (400) cae comodamente dentro de este rango.
    GAS_PPM_MIN = 15.0
    GAS_PPM_MAX = 650.0

    def __init__(self, pin_dht: int, pin_gas: int):

        self.dht_device = dht.DHT22(
            Pin(pin_dht)
        )

        self.gas_adc = ADC(
            Pin(pin_gas)
        )

        # ADC1 (GPIO32-39): atenuacion de 11dB para leer todo el
        # rango 0-3.3V (por defecto solo llega limpio hasta ~1.1V).
        self.gas_adc.atten(
            ADC.ATTN_11DB
        )

        # Se calibra despues, con calibrar_linea_base() — ver el
        # porque en ese metodo.
        self.gas_baseline_raw = 0

    def calibrar_linea_base(self):

        # ------------------------------------------------------
        # CALIBRACION EN "AIRE LIMPIO"
        #
        # El sensor de gas de Wokwi (como un MQ-2 real) NO entrega
        # 0V con poco gas: tiene un voltaje base propio en reposo.
        # Por eso no sirve asumir una escala fija (0V=0ppm,
        # 3.3V=maximo); en vez de eso, se toma una lectura de
        # referencia y luego el ppm se calcula en funcion de cuanto
        # se aleja la lectura actual de esa base. Es exactamente
        # como se calibra un MQ-2 real (R0 en aire limpio).
        #
        # IMPORTANTE: esto se llama DESPUES de conectar el Wi-Fi
        # (no en __init__, que corre antes). El Wi-Fi activo mete
        # interferencia de RF al ADC del ESP32 y baja las lecturas
        # de forma sistematica; si la base se calibra con el radio
        # apagado y despues se compara contra lecturas con el radio
        # prendido, TODO sale por debajo de la base sin importar el
        # gas real (eso fue exactamente el bug reportado: base=2543
        # con Wi-Fi apagado, lecturas 1800-2300 con Wi-Fi activo).
        # ------------------------------------------------------

        self.gas_baseline_raw = self._leer_gas_adc_promedio()

    def _leer_gas_adc_promedio(self, muestras: int = 30):

        # El ADC del ESP32 en los pines 32-39 es ruidoso, sobre todo
        # con el Wi-Fi activo (interferencia de RF): una sola lectura
        # puede variar bastante entre llamadas aunque nada cambie
        # fisicamente. Promediar varias muestras seguidas suaviza
        # ese ruido para que el valor refleje el gas real y no el
        # ruido del ADC.

        total = 0

        for _ in range(muestras):

            total += self.gas_adc.read()

        return total / muestras

    def read_telemetry(self):

        # ----------------------------------------------------------
        # DHT22
        # ----------------------------------------------------------

        # calidad_ambiente describe la lectura de temperatura/humedad:
        # "valida" si el DHT22 respondio de verdad, "invalida" si tuvo
        # que usarse el valor de respaldo (no es una lectura real del
        # sensor, sino un numero fijo para que el sistema no se caiga).
        calidad_ambiente = CALIDAD_VALIDA

        try:

            self.dht_device.measure()

            temp_c = self.dht_device.temperature()
            hum_pct = self.dht_device.humidity()

            # Validación básica
            if (
                temp_c is None
                or hum_pct is None
            ):

                raise Exception(
                    "DHT22 devolvió valores inválidos"
                )

            print(
                "[SENSOR] DHT22 -> T={:.2f} C H={:.2f} %".format(
                    temp_c,
                    hum_pct
                )
            )

        except Exception as e:

            print(
                "[SENSOR] Error DHT22:",
                repr(e)
            )

            # Valores de respaldo: NO son una lectura real, por eso se
            # marcan como "invalida" en vez de "valida".
            temp_c = 25.0
            hum_pct = 50.0
            calidad_ambiente = CALIDAD_INVALIDA

        # ----------------------------------------------------------
        # GAS (MQ-2 real por ADC, calibrado contra la linea base)
        # ----------------------------------------------------------

        gas_raw = self._leer_gas_adc_promedio()

        # AUTO-CERO: si aparece una lectura mas baja que la linea
        # base actual, la base baja hasta ahi. Esto compensa que el
        # sensor derive/baje con el tiempo despues del arranque (la
        # foto de calibracion inicial puede quedar mas alta de lo
        # normal y bloquear todo para siempre si no se ajusta sola).
        if gas_raw < self.gas_baseline_raw:

            self.gas_baseline_raw = gas_raw

        rango_disponible = (
            self.ADC_MAX
            - self.gas_baseline_raw
        )

        if rango_disponible <= 0:

            fraccion = 0.0

        else:

            fraccion = (
                (gas_raw - self.gas_baseline_raw)
                / rango_disponible
            )

            # Limitar entre 0 y 1 (por debajo de la linea base o por
            # encima del maximo del ADC no deben dar valores fuera
            # de rango).
            if fraccion < 0.0:

                fraccion = 0.0

            elif fraccion > 1.0:

                fraccion = 1.0

        gas_ppm = (
            self.GAS_PPM_MIN
            + fraccion
            * (self.GAS_PPM_MAX - self.GAS_PPM_MIN)
        )

        # calidad_gas: si el ADC queda pegado en 0 o en el maximo, lo
        # mas probable es que el sensor este desconectado o mal
        # cableado, no que de verdad haya ese nivel de gas.
        if gas_raw <= 0 or gas_raw >= self.ADC_MAX:

            calidad_gas = CALIDAD_SOSPECHOSA

        else:

            calidad_gas = CALIDAD_VALIDA

        return (
            temp_c,
            hum_pct,
            gas_ppm,
            calidad_ambiente,
            calidad_gas
        )


# ==================================================================
# PARTE 3: INTERFAZ DE USUARIO
# ==================================================================

class UserInterfaceManager:
    """Gestiona LCD, LEDs y botones."""

    def __init__(
        self,
        sda_pin: int,
        scl_pin: int,
        led_green_pin: int,
        led_red_pin: int
    ):

        i2c = I2C(
            0,
            scl=Pin(scl_pin),
            sda=Pin(sda_pin),
            freq=400000
        )

        self.lcd = I2cLcd(
            i2c,
            0x27,
            2,
            16
        )

        self.led_green = Pin(
            led_green_pin,
            Pin.OUT
        )

        self.led_red = Pin(
            led_red_pin,
            Pin.OUT
        )

        self.screen_mode = 0

    def show_splash_screen(self):

        try:

            self.lcd.clear()

            self.lcd.move_to(0, 0)

            self.lcd.putstr(
                "MONOMEROS - G8  "
            )

            self.lcd.move_to(0, 1)

            self.lcd.putstr(
                "Sistema IoT 2026"
            )

            utime.sleep_ms(1500)

            self.lcd.clear()

        except Exception as e:

            print(
                "[LCD] Error:",
                repr(e)
            )

    def toggle_screen_mode(self):

        self.screen_mode = (
            self.screen_mode + 1
        ) % 2

        try:

            self.lcd.clear()

        except Exception:

            pass

        print(
            "[UI] Modo LCD:",
            self.screen_mode
        )

    def update_indicators(
        self,
        is_critical: bool
    ):

        if is_critical:

            self.led_red.value(1)
            self.led_green.value(0)

        else:

            self.led_red.value(0)
            self.led_green.value(1)

    def show_manual_send_notice(self):

        try:

            self.lcd.clear()

            self.lcd.move_to(0, 0)

            self.lcd.putstr(
                ">> ENVIO MANUAL "
            )

            self.lcd.move_to(0, 1)

            self.lcd.putstr(
                "TRANSMITIENDO..."
            )

            utime.sleep_ms(600)

            self.lcd.clear()

        except Exception as e:

            print(
                "[LCD] Error:",
                repr(e)
            )

    def mostrar_area_confirmada(self, id_area: int):

        try:

            self.lcd.clear()

            self.lcd.move_to(0, 0)

            self.lcd.putstr(
                "AREA CONFIRMADA:"
            )

            self.lcd.move_to(0, 1)

            self.lcd.putstr(
                "ID = {}".format(
                    id_area
                )
            )

            utime.sleep_ms(1000)

            self.lcd.clear()

        except Exception as e:

            print(
                "[LCD] Error:",
                repr(e)
            )

    def mostrar_entrada_area(self, buffer: str):

        # Se llama en vivo mientras se teclea (sin sleep_ms, para no
        # bloquear el loop): cada digito nuevo se ve de inmediato,
        # antes de presionar "#". No hace lcd.clear() completo, solo
        # reescribe ambas lineas ya rellenas a 16 espacios, para que
        # no queden restos de la pantalla normal (T:.. / Gas:..).
        try:

            self.lcd.move_to(0, 0)

            self.lcd.putstr(
                "INGRESA AREA:   "
            )

            self.lcd.move_to(0, 1)

            self.lcd.putstr(
                "{:<16}".format(
                    buffer + "_"
                )
            )

        except Exception as e:

            print(
                "[LCD] Error:",
                repr(e)
            )

    def render_display(
        self,
        temp: float,
        hum: float,
        gas: float,
        is_critical: bool
    ):

        try:

            if self.screen_mode == 0:

                self.lcd.move_to(0, 0)

                self.lcd.putstr(
                    "T:{:.1f}C H:{:.1f}% ".format(
                        temp,
                        hum
                    )
                )

                self.lcd.move_to(0, 1)

                self.lcd.putstr(
                    "Gas:{:.1f}PPM   ".format(
                        gas
                    )
                )

            else:

                self.lcd.move_to(0, 0)

                self.lcd.putstr(
                    "ESTADO PLANTA:  "
                )

                self.lcd.move_to(0, 1)

                if is_critical:

                    self.lcd.putstr(
                        "!EMERGENCIA GAS!"
                    )

                else:

                    self.lcd.putstr(
                        "OPERACION NORMAL"
                    )

        except Exception as e:

            print(
                "[LCD] Error:",
                repr(e)
            )


# ==================================================================
# PARTE 3.5: SELECTOR DE AREA (TECLADO MATRICIAL 4x4)
# ==================================================================

class AreaSelector:
    """Lee un teclado matricial (wokwi-membrane-keypad, 4x4) y deja
    escribir el id_area directamente por teclado, en vez de calcular
    binario con switches.

    Uso: se teclean 1 o 2 digitos con el numero del area y se
    confirma con "#". Si el numero cae dentro del rango real de la
    tabla "areas" (ver Backend -> GET /api/areas/), se actualiza el
    area activa; si no, se rechaza y se mantiene la anterior. La
    tecla "*" borra lo que se lleva tecleado (por si te equivocas).

    escanear() se llama en cada vuelta del loop principal (barre
    filas/columnas, con anti-rebote simple). leer_area() solo
    devuelve el ultimo valor confirmado con "#" — no bloquea nunca
    esperando tecla.
    """

    FILAS = ["1", "2", "3", "A", "4", "5", "6", "B",
             "7", "8", "9", "C", "*", "0", "#", "D"]

    def __init__(
        self,
        pines_filas: list,
        pines_columnas: list,
        area_minima: int,
        area_maxima: int,
        area_por_defecto: int,
        al_confirmar=None,
        al_escribir=None
    ):

        self.filas = [
            Pin(pin, Pin.OUT)
            for pin in pines_filas
        ]

        for fila in self.filas:

            fila.value(1)

        self.columnas = [
            Pin(pin, Pin.IN, Pin.PULL_UP)
            for pin in pines_columnas
        ]

        self.area_minima = area_minima
        self.area_maxima = area_maxima
        self.area_actual = area_por_defecto

        # Funcion opcional que se llama con el id_area cada vez que
        # se confirma con "#" (sin importar si es igual o distinta a
        # la anterior) — para dar feedback visible (ej. en el LCD)
        # de que la tecla si se registro.
        self.al_confirmar = al_confirmar

        # Funcion opcional que se llama con el buffer actual (texto
        # que se lleva tecleado) cada vez que cambia, para mostrarlo
        # en vivo en el LCD mientras se escribe, antes de confirmar
        # con "#".
        self.al_escribir = al_escribir

        self._buffer = ""
        self._tecla_anterior = None

    def _leer_tecla(self):

        # Barrido clasico de matriz: se pone en LOW una fila a la
        # vez (las demas en HIGH) y se revisa que columna quedo en
        # LOW (por el pull-up, una columna sin tecla presionada se
        # queda en HIGH).
        for i, fila in enumerate(self.filas):

            fila.value(0)

            for j, columna in enumerate(self.columnas):

                if columna.value() == 0:

                    fila.value(1)

                    return self.FILAS[i * 4 + j]

            fila.value(1)

        return None

    def escanear(self):

        tecla = self._leer_tecla()

        # Anti-rebote simple: solo procesar el FLANCO de presionar
        # (nada -> tecla), no mientras se mantiene apretada.
        if tecla == self._tecla_anterior:

            return

        self._tecla_anterior = tecla

        if tecla is None:

            return

        if tecla == "*":

            self._buffer = ""

            self._avisar_buffer()

        elif tecla == "#":

            self._confirmar_area()

        elif tecla in "0123456789":

            # Maximo 2 digitos (areas van de 1 a 99): al llegar al
            # tercero, se reinicia el buffer con el nuevo digito en
            # vez de seguir acumulando sin sentido.
            if len(self._buffer) >= 2:

                self._buffer = tecla

            else:

                self._buffer += tecla

            self._avisar_buffer()

        # A/B/C/D no se usan para nada (el keypad de Wokwi las trae
        # por defecto); se ignoran silenciosamente.

    def _avisar_buffer(self):

        if self.al_escribir is not None:

            self.al_escribir(
                self._buffer
            )

    def esta_escribiendo(self):

        return len(self._buffer) > 0

    def buffer_actual(self):

        return self._buffer

    def _confirmar_area(self):

        if not self._buffer:

            return

        try:

            valor = int(self._buffer)

        except ValueError:

            valor = -1

        if self.area_minima <= valor <= self.area_maxima:

            self.area_actual = valor

            if self.al_confirmar is not None:

                self.al_confirmar(
                    self.area_actual
                )

        self._buffer = ""

    def leer_area(self):

        return self.area_actual


# ==================================================================
# PARTE 4: CONTROLADOR PRINCIPAL
# ==================================================================

class MonomerosController:
    """Controlador principal del sistema IoT."""

    # --------------------------------------------------------------
    # UMBRALES (minimo y maximo para los 3 parametros que manda el
    # ESP32). Estos valores son EXACTAMENTE los que ya tiene
    # configurados la tabla parametros_ambientales en la base de
    # datos (ver GET /api/parametros-ambientales/) para que la
    # alerta del ESP32 coincida con lo que la app de escritorio
    # dibuja en los gauges como "zona segura".
    # --------------------------------------------------------------

    LIMIT_TEMP_MIN = 15.0
    LIMIT_TEMP_MAX = 45.0

    LIMIT_HUM_MIN = 20.0
    LIMIT_HUM_MAX = 90.0

    LIMIT_GAS_MIN = 0.0
    LIMIT_GAS_MAX = 400.0

    # --------------------------------------------------------------
    # IDs DE ÁREA
    #
    # Ya no es fijo: se lee del DIP switch del diagrama (ver
    # AreaSelector) en cada ciclo, dentro de este rango. Ajusta
    # AREA_MAXIMA si tu tabla "areas" tiene mas o menos filas
    # (ver GET /api/areas/).
    # --------------------------------------------------------------

    AREA_MINIMA = 1
    AREA_MAXIMA = 20
    AREA_POR_DEFECTO = 1

    # --------------------------------------------------------------
    # IDs DE PARÁMETROS
    #
    # IMPORTANTE:
    # Verifica que coincidan con tu tabla parametros.
    # --------------------------------------------------------------

    PARAM_TEMPERATURA = 1
    PARAM_HUMEDAD = 2
    PARAM_GAS = 3

    def __init__(
        self,
        api_base_url: str
    ):

        self.api_base_url = (
            api_base_url.rstrip("/")
        )

        # ----------------------------------------------------------
        # RED
        # ----------------------------------------------------------

        self.network = NetworkManager(
            WIFI_SSID,
            WIFI_PASSWORD
        )

        # ----------------------------------------------------------
        # SENSORES
        # ----------------------------------------------------------

        self.sensors = EnvironmentalSensors(
            pin_dht=15,
            pin_gas=34
        )

        # ----------------------------------------------------------
        # UI
        # ----------------------------------------------------------

        self.ui = UserInterfaceManager(
            sda_pin=21,
            scl_pin=22,
            led_green_pin=2,
            led_red_pin=4
        )

        # ----------------------------------------------------------
        # SELECTOR DE AREA (teclado matricial, ver diagram.json:
        # keypad1). al_confirmar apunta al LCD para dar feedback
        # visible en el circuito, no solo en la consola.
        # ----------------------------------------------------------

        self.area_selector = AreaSelector(
            pines_filas=[5, 13, 14, 27],
            pines_columnas=[26, 25, 33, 32],
            area_minima=self.AREA_MINIMA,
            area_maxima=self.AREA_MAXIMA,
            area_por_defecto=self.AREA_POR_DEFECTO,
            al_confirmar=self.ui.mostrar_area_confirmada,
            al_escribir=self.ui.mostrar_entrada_area
        )

        # ----------------------------------------------------------
        # BOTONES
        # ----------------------------------------------------------

        self.btn_mode = Pin(
            18,
            Pin.IN,
            Pin.PULL_UP
        )

        self.btn_manual_send = Pin(
            19,
            Pin.IN,
            Pin.PULL_UP
        )

        self.last_btn_mode = 1
        self.last_btn_send = 1

        # ----------------------------------------------------------
        # TRANSMISIÓN
        # ----------------------------------------------------------

        self.last_transmission_time = (
            utime.ticks_ms()
        )

        self.transmission_interval_ms = 5000

        # ----------------------------------------------------------
        # LECTURA DE SENSORES (throttle)
        #
        # El DHT22 necesita al menos ~2s entre lecturas; si se llama
        # measure() en cada vuelta del loop (cada 50ms) responde con
        # datos invalidos (T=-40.00 C, H=0.00 %) sin lanzar excepcion.
        # Por eso se cachea la ultima lectura y solo se refresca cada
        # sensor_read_interval_ms.
        # ----------------------------------------------------------

        self.sensor_read_interval_ms = 2000

        self.last_sensor_read_time = (
            utime.ticks_ms()
            - self.sensor_read_interval_ms
        )

        self.last_telemetry = (
            25.0, 50.0, 45.0, CALIDAD_INVALIDA, CALIDAD_INVALIDA
        )

    # ==================================================================
    # CREAR PAYLOAD
    # ==================================================================

    def build_measurement_payload(
        self,
        id_parametro,
        valor,
        calidad_dato=CALIDAD_VALIDA
    ):
        # calidad_dato SIEMPRE debe ser una de las 3 que acepta el
        # backend (medicion_repo.CALIDADES_VALIDAS). Si por algun
        # motivo llega otra cosa, cae a "valida" en vez de mandar un
        # valor que el backend va a rechazar con error 400.
        if calidad_dato not in (
            CALIDAD_VALIDA,
            CALIDAD_SOSPECHOSA,
            CALIDAD_INVALIDA
        ):
            calidad_dato = CALIDAD_VALIDA

        return {

            "id_area":
                self.area_selector.leer_area(),

            "id_parametro":
                id_parametro,

            "valor":
                round(valor, 2),

            "calidad_dato":
                calidad_dato,

            "observacion":
                "ESP32 Simulacion - Wokwi"
        }

    # ==================================================================
    # ENVIAR MEDICIÓN
    # ==================================================================

    def send_measurement(
        self,
        id_parametro,
        valor,
        calidad_dato=CALIDAD_VALIDA
    ):

        url = (
            self.api_base_url
            + "/mediciones/"
        )

        payload = (
            self.build_measurement_payload(
                id_parametro,
                valor,
                calidad_dato
            )
        )

        print()
        print(
            "[HTTP] POST MEDICION"
        )

        print(
            "[HTTP] URL:",
            url
        )

        print(
            "[HTTP] Parametro:",
            id_parametro
        )

        print(
            "[HTTP] Valor:",
            round(valor, 2)
        )
        print(
            "[HTTP] Calidad:",
            calidad_dato
        )
        print(
            "[HTTP] Payload:",
            ujson.dumps(payload)
        )

        try:

            headers = {
                "Content-Type":
                    "application/json"
            }

            response = urequests.post(
                url,
                data=ujson.dumps(payload),
                headers=headers
            )

            print(
                "[HTTP] Status:",
                response.status_code
            )

            # ------------------------------------------------------
            # Respuesta
            # ------------------------------------------------------

            response_text = ""

            try:

                response_text = response.text

                print(
                    "[HTTP] Respuesta:",
                    response_text
                )

            except Exception as e:

                print(
                    "[HTTP] Error leyendo respuesta:",
                    repr(e)
                )

            # ------------------------------------------------------
            # Obtener ID de medición
            # ------------------------------------------------------

            id_medicion = None

            if response.status_code == 201:

                try:

                    data = response.json()

                    id_medicion = data.get(
                        "id_medicion"
                    )

                    print(
                        "[HTTP] ID medicion:",
                        id_medicion
                    )

                except Exception as e:

                    print(
                        "[HTTP] No se pudo obtener ID:",
                        repr(e)
                    )

            elif response.status_code >= 400:

                print(
                    "[HTTP] ERROR DEL BACKEND"
                )

            response.close()

            return id_medicion

        except Exception as e:

            print()
            print(
                "[HTTP] ERROR MEDICION:"
            )

            print(
                repr(e)
            )

            print(
                "[HTTP] Verifique que el backend Flask este activo "
                "(--host=0.0.0.0 --port=8000)."
            )

            print(
                "[HTTP] URL:",
                url
            )

            return None

    # ==================================================================
    # ENVIAR ALERTA
    # ==================================================================

    def send_alert(
        self,
        id_medicion,
        tipo_alerta,
        descripcion
    ):

        if id_medicion is None:

            print(
                "[ALERTA] No se puede registrar alerta."
            )

            print(
                "[ALERTA] No existe id_medicion."
            )

            return

        url = (
            self.api_base_url
            + "/alertas/"
        )

        payload = {

            "id_medicion":
                id_medicion,

            "id_area":
                self.area_selector.leer_area(),

            "tipo_alerta":
                tipo_alerta,

            "nivel":
                "critico",

            "descripcion":
                descripcion
        }

        print()
        print(
            "[HTTP] POST ALERTA"
        )

        print(
            "[HTTP] URL:",
            url
        )

        print(
            "[HTTP] Payload:",
            ujson.dumps(payload)
        )

        try:

            headers = {
                "Content-Type":
                    "application/json"
            }

            response = urequests.post(
                url,
                data=ujson.dumps(payload),
                headers=headers
            )

            print(
                "[HTTP] Status alerta:",
                response.status_code
            )

            try:

                print(
                    "[HTTP] Respuesta alerta:",
                    response.text
                )

            except Exception:

                pass

            response.close()

        except Exception as e:

            print(
                "[HTTP] ERROR ALERTA:",
                repr(e)
            )

    # ==================================================================
    # VERIFICAR RANGO Y ALERTAR (minimo o maximo, para cualquier
    # parametro) — usado por los 3 (temperatura, humedad y gas) para
    # no repetir el mismo bloque de codigo 6 veces.
    # ==================================================================

    def _verificar_y_alertar(
        self,
        id_medicion,
        valor,
        minimo,
        maximo,
        nombre_parametro,
        unidad
    ):

        if valor > maximo:

            self.send_alert(

                id_medicion,

                "Desviacion de {} (alto)".format(
                    nombre_parametro
                ),

                "{} de {:.1f} {} supera el limite maximo de {:.1f} {}".format(
                    nombre_parametro,
                    valor,
                    unidad,
                    maximo,
                    unidad
                )
            )

        elif valor < minimo:

            self.send_alert(

                id_medicion,

                "Desviacion de {} (bajo)".format(
                    nombre_parametro
                ),

                "{} de {:.1f} {} esta por debajo del limite minimo de {:.1f} {}".format(
                    nombre_parametro,
                    valor,
                    unidad,
                    minimo,
                    unidad
                )
            )

    # ==================================================================
    # TRANSMITIR LOTE
    # ==================================================================

    def transmit_to_api(
        self,
        temp,
        hum,
        gas,
        calidad_ambiente,
        calidad_gas,
        alert
    ):

        print()
        print(
            "============================================================"
        )

        print(
            "[HTTP] TRANSMITIENDO LOTE"
        )

        print(
            "Area seleccionada (teclado):",
            self.area_selector.leer_area()
        )

        print(
            "Temperatura: {:.2f} C".format(
                temp
            )
        )

        print(
            "Humedad: {:.2f} %".format(
                hum
            )
        )

        print(
            "Gas: {:.2f} ppm".format(
                gas
            )
        )

        print(
            "Calidad T/H:",
            calidad_ambiente
        )

        print(
            "Alerta:",
            alert
        )

        print(
            "============================================================"
        )

        # ----------------------------------------------------------
        # TEMPERATURA Y HUMEDAD
        #
        # Comparten la misma calidad_ambiente: si el DHT22 fallo y se
        # usaron los valores de respaldo (25.0 C / 50.0 %), esa lectura
        # se manda como "invalida" en vez de "valida", para que quede
        # registrado en la BD que NO fue una lectura real del sensor.
        # ----------------------------------------------------------

        id_med_temp = self.send_measurement(
            self.PARAM_TEMPERATURA,
            temp,
            calidad_ambiente
        )

        # Escanear el teclado entre cada POST: cada llamada HTTP
        # bloquea el programa mientras espera respuesta del backend
        # (puede ser un buen rato); sin esto, un lote de 3-5
        # peticiones seguidas dejaria el teclado "sordo" por toda esa
        # ventana de tiempo en vez de solo por cada peticion individual.
        self.area_selector.escanear()

        id_med_hum = self.send_measurement(
            self.PARAM_HUMEDAD,
            hum,
            calidad_ambiente
        )

        self.area_selector.escanear()

        # ----------------------------------------------------------
        # GAS (MQ-2 real por ADC)
        #
        # calidad_gas viene de EnvironmentalSensors.read_telemetry():
        # "sospechosa" si el ADC quedo pegado en 0 o en el maximo
        # (sensor probablemente desconectado), "valida" en caso normal.
        # ----------------------------------------------------------

        id_med_gas = self.send_measurement(
            self.PARAM_GAS,
            gas,
            calidad_gas
        )

        self.area_selector.escanear()

        # ----------------------------------------------------------
        # ALERTAS (minimo y maximo, para los 3 parametros)
        # ----------------------------------------------------------

        self._verificar_y_alertar(
            id_med_temp,
            temp,
            self.LIMIT_TEMP_MIN,
            self.LIMIT_TEMP_MAX,
            "Temperatura Ambiente",
            "C"
        )

        self.area_selector.escanear()

        self._verificar_y_alertar(
            id_med_hum,
            hum,
            self.LIMIT_HUM_MIN,
            self.LIMIT_HUM_MAX,
            "Humedad Relativa",
            "%"
        )

        self.area_selector.escanear()

        self._verificar_y_alertar(
            id_med_gas,
            gas,
            self.LIMIT_GAS_MIN,
            self.LIMIT_GAS_MAX,
            "Gas Amoniaco (NH3)",
            "ppm"
        )

        print()
        print(
            "[HTTP] Lote terminado."
        )

    # ==================================================================
    # PRUEBA INICIAL DE API
    # ==================================================================

    def test_api(self):

        print()
        print(
            "============================================================"
        )

        print(
            "[TEST] PROBANDO CONEXION CON FLASK"
        )

        print(
            "============================================================"
        )

        id_medicion = self.send_measurement(
            self.PARAM_TEMPERATURA,
            25.5,
            CALIDAD_VALIDA
        )

        if id_medicion is not None:

            print()
            print(
                "[TEST] API FUNCIONANDO CORRECTAMENTE."
            )

        else:

            print()
            print(
                "[TEST] No se obtuvo ID de medicion."
            )

        print(
            "============================================================"
        )

    # ==================================================================
    # LOOP PRINCIPAL
    # ==================================================================

    def run(self):

        print()
        print(
            "############################################################"
        )

        print(
            "#                                                          #"
        )

        print(
            "#       MONOMEROS S.A. - SISTEMA IoT - GRUPO 8            #"
        )

        print(
            "#                                                          #"
        )

        print(
            "############################################################"
        )

        print()

        print(
            "[CONFIG] API:"
        )

        print(
            self.api_base_url
        )

        print()

        # ----------------------------------------------------------
        # CONECTAR WIFI
        # ----------------------------------------------------------

        wifi_ok = self.network.connect()

        if not wifi_ok:

            print(
                "[SISTEMA] Wi-Fi no disponible."
            )

        # ----------------------------------------------------------
        # CALIBRAR SENSOR DE GAS (con el Wi-Fi ya en su estado
        # definitivo, para que la linea base y las lecturas normales
        # se tomen en las mismas condiciones de ruido de RF)
        # ----------------------------------------------------------

        self.sensors.calibrar_linea_base()

        # ----------------------------------------------------------
        # LCD
        # ----------------------------------------------------------

        self.ui.show_splash_screen()

        # ----------------------------------------------------------
        # PRUEBA API
        # ----------------------------------------------------------

        if wifi_ok:

            self.test_api()

        # ----------------------------------------------------------
        # CICLO
        # ----------------------------------------------------------

        while True:

            # ======================================================
            # WIFI
            # ======================================================

            if not self.network.is_connected():

                print(
                    "[RED] Wi-Fi desconectado."
                )

                self.network.connect()

            # ======================================================
            # SENSORES (respeta el intervalo minimo del DHT22)
            # ======================================================

            now_sensor = utime.ticks_ms()

            if (
                utime.ticks_diff(
                    now_sensor,
                    self.last_sensor_read_time
                )
                >=
                self.sensor_read_interval_ms
            ):

                self.last_sensor_read_time = now_sensor

                self.last_telemetry = (
                    self.sensors.read_telemetry()
                )

            temp, hum, gas, calidad_ambiente, calidad_gas = (
                self.last_telemetry
            )

            # ======================================================
            # ALERTA
            # ======================================================

            is_critical = (

                gas > self.LIMIT_GAS_MAX
                or gas < self.LIMIT_GAS_MIN

                or

                temp > self.LIMIT_TEMP_MAX
                or temp < self.LIMIT_TEMP_MIN

                or

                hum > self.LIMIT_HUM_MAX
                or hum < self.LIMIT_HUM_MIN
            )

            # ======================================================
            # LEDS
            # ======================================================

            self.ui.update_indicators(
                is_critical
            )

            # ======================================================
            # LCD
            # ======================================================

            # ======================================================
            # TECLADO - SELECCION DE AREA
            #
            # Se escanea ANTES de decidir que mostrar en el LCD: si
            # hay algo tecleado (buffer no vacio), se muestra eso en
            # vez de la pantalla normal de T/H/Gas, para poder ver
            # el numero mientras se escribe, antes de confirmar con
            # "#".
            # ======================================================

            self.area_selector.escanear()

            if self.area_selector.esta_escribiendo():

                self.ui.mostrar_entrada_area(
                    self.area_selector.buffer_actual()
                )

            else:

                self.ui.render_display(
                    temp,
                    hum,
                    gas,
                    is_critical
                )

            # ======================================================
            # BOTÓN AZUL - CAMBIAR PANTALLA
            # ======================================================

            current_btn_mode = (
                self.btn_mode.value()
            )

            if (

                current_btn_mode == 0

                and

                self.last_btn_mode == 1

            ):

                print(
                    "[BOTON] Cambio de pantalla."
                )

                self.ui.toggle_screen_mode()

                utime.sleep_ms(150)

            self.last_btn_mode = (
                current_btn_mode
            )

            # ======================================================
            # BOTÓN AMARILLO - ENVÍO MANUAL
            # ======================================================

            current_btn_send = (
                self.btn_manual_send.value()
            )

            is_manual_trigger = (

                current_btn_send == 0

                and

                self.last_btn_send == 1

            )

            self.last_btn_send = (
                current_btn_send
            )

            # ======================================================
            # TRANSMISIÓN
            # ======================================================

            now = utime.ticks_ms()

            if is_manual_trigger:

                print()
                print(
                    "[BOTON] ENVIO MANUAL"
                )

                self.ui.show_manual_send_notice()

                self.transmit_to_api(
                    temp,
                    hum,
                    gas,
                    calidad_ambiente,
                    calidad_gas,
                    is_critical
                )

                self.last_transmission_time = (
                    now
                )

            elif (

                utime.ticks_diff(
                    now,
                    self.last_transmission_time
                )

                >=

                self.transmission_interval_ms

            ):

                self.last_transmission_time = (
                    now
                )

                self.transmit_to_api(
                    temp,
                    hum,
                    gas,
                    calidad_ambiente,
                    calidad_gas,
                    is_critical
                )

            # ======================================================
            # PEQUEÑA PAUSA
            # ======================================================

            utime.sleep_ms(100)


# ==================================================================
# PUNTO DE ENTRADA
# ==================================================================

if __name__ == "__main__":

    node = MonomerosController(
        API_BASE_URL
    )

    node.run()

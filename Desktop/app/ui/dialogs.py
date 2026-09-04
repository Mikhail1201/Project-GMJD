from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from app.api import ApiClient
from app.state import Catalogos

SEVERIDADES = ["baja", "media", "alta", "critica"]

# Debe coincidir con PROTOCOLOS_VALIDOS de Backend/app/repositories/sensor_repo.py:
# si se manda otro valor, el backend responde 400.
PROTOCOLOS = [
    "1-Wire", "I2C", "SPI", "Analogico", "4-20 mA",
    "Modbus RTU", "Modbus TCP", "RS-232", "RS-485", "USB", "Wi-Fi",
]


class CrearIncidenteDialog(QDialog):
    """Formulario para escalar manualmente un incidente ambiental: quien lo
    crea es siempre una persona (elige area, severidad, causa y a quien se
    lo asigna) — un sensor no tiene forma de completar esos campos con
    criterio, por eso esto vive en la app de escritorio y no en el ESP32."""

    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self.setWindowTitle("Crear Incidente Ambiental")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        formulario = QFormLayout()
        formulario.setSpacing(10)

        self.combo_area = QComboBox()
        for area in catalogos.areas:
            self.combo_area.addItem(area["nombre"], area["id_area"])

        self.combo_alerta = QComboBox()
        self.combo_alerta.addItem("Ninguna (incidente independiente)", None)
        self._cargar_alertas_recientes()

        self.campo_titulo = QLineEdit()
        self.campo_titulo.setPlaceholderText("Ej. Fuga de amoniaco en Planta A")

        self.campo_descripcion = QPlainTextEdit()
        self.campo_descripcion.setFixedHeight(70)

        self.combo_severidad = QComboBox()
        self.combo_severidad.addItems(SEVERIDADES)

        self.campo_causa = QPlainTextEdit()
        self.campo_causa.setFixedHeight(50)
        self.campo_causa.setPlaceholderText("Opcional")

        self.combo_responsable = QComboBox()
        self.combo_responsable.addItem("Sin asignar", None)
        for usuario in catalogos.usuarios:
            self.combo_responsable.addItem(f"{usuario['nombre']} {usuario['apellido']}", usuario["id_usuario"])

        formulario.addRow("Área *:", self.combo_area)
        formulario.addRow("Alerta relacionada:", self.combo_alerta)
        formulario.addRow("Título *:", self.campo_titulo)
        formulario.addRow("Descripción *:", self.campo_descripcion)
        formulario.addRow("Severidad *:", self.combo_severidad)
        formulario.addRow("Causa:", self.campo_causa)
        formulario.addRow("Responsable:", self.combo_responsable)
        layout.addLayout(formulario)

        layout.addWidget(QLabel("(*) Campos obligatorios"))

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Crear Incidente")
        botones.accepted.connect(self._validar_y_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _cargar_alertas_recientes(self):
        """Trae las alertas mas recientes para poder enlazar el incidente a
        una en concreto. Es una llamada sincronica puntual disparada al
        abrir el dialogo (mismo patron que atender_alerta/resolver_incidente
        en esta app: una accion explicita del usuario, no un refresco
        periodico), asi que no hace falta un hilo aparte para esto."""
        try:
            alertas = self.cliente.listar_alertas()
        except Exception:  # noqa: BLE001 - si falla, el combo simplemente queda solo con "Ninguna"
            return
        for alerta in alertas[:30]:
            atendida = "atendida" if alerta.get("nombre_atendio") else "sin atender"
            etiqueta = (
                f"#{alerta['id_alerta']} · {str(alerta.get('fecha_hora', ''))[:16]} · "
                f"{alerta.get('nombre_area', '')} · {alerta.get('tipo_alerta', '')} "
                f"({str(alerta.get('nivel', '')).upper()}, {atendida})"
            )
            self.combo_alerta.addItem(etiqueta, alerta["id_alerta"])

    def _validar_y_aceptar(self):
        if self.combo_area.count() == 0:
            QMessageBox.warning(self, "Crear incidente", "No hay áreas disponibles en el catálogo.")
            return
        if not self.campo_titulo.text().strip():
            QMessageBox.warning(self, "Crear incidente", "El título es obligatorio.")
            return
        if not self.campo_descripcion.toPlainText().strip():
            QMessageBox.warning(self, "Crear incidente", "La descripción es obligatoria.")
            return
        self.accept()

    def datos(self) -> dict:
        return {
            "id_area": self.combo_area.currentData(),
            "id_alerta": self.combo_alerta.currentData(),
            "titulo": self.campo_titulo.text().strip(),
            "descripcion": self.campo_descripcion.toPlainText().strip(),
            "severidad": self.combo_severidad.currentText(),
            "causa": self.campo_causa.toPlainText().strip() or None,
            "responsable_id": self.combo_responsable.currentData(),
        }


class CrearSensorDialog(QDialog):
    """Formulario para registrar un sensor fisico de la planta.

    Un sensor es un equipo que alguien instala y da de alta: el codigo de
    inventario, el area donde quedo montado, que parametro mide y quien
    responde por su calibracion son datos que solo puede aportar una persona,
    por eso el alta vive aqui y no en el firmware del ESP32.
    """

    def __init__(self, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.catalogos = catalogos
        self.setWindowTitle("Registrar Sensor")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        formulario = QFormLayout()
        formulario.setSpacing(10)

        self.campo_codigo = QLineEdit()
        self.campo_codigo.setPlaceholderText("Ej. SEN-A01-TMP")

        self.campo_nombre = QLineEdit()
        self.campo_nombre.setPlaceholderText("Ej. Sensor de temperatura - Planta de Amoniaco")

        self.combo_area = QComboBox()
        for area in catalogos.areas:
            self.combo_area.addItem(area["nombre"], area["id_area"])

        self.combo_parametro = QComboBox()
        for parametro in catalogos.parametros:
            etiqueta = f"{parametro['nombre']} ({parametro.get('unidad', '')})"
            self.combo_parametro.addItem(etiqueta, parametro["id_parametro"])

        self.campo_ubicacion = QLineEdit()
        self.campo_ubicacion.setPlaceholderText("Opcional. Ej. Bloque A - Nivel 1, muro norte")

        self.campo_modelo = QLineEdit()
        self.campo_modelo.setPlaceholderText("Opcional. Ej. DHT22")

        self.campo_fabricante = QLineEdit()
        self.campo_fabricante.setPlaceholderText("Opcional. Ej. Aosong")

        self.campo_serie = QLineEdit()
        self.campo_serie.setPlaceholderText("Opcional, pero no se puede repetir")

        self.combo_protocolo = QComboBox()
        self.combo_protocolo.addItem("Sin especificar", None)
        for protocolo in PROTOCOLOS:
            self.combo_protocolo.addItem(protocolo, protocolo)

        self.spin_rango_min = QDoubleSpinBox()
        self.spin_rango_min.setRange(-100000.0, 100000.0)
        self.spin_rango_min.setDecimals(2)

        self.spin_rango_max = QDoubleSpinBox()
        self.spin_rango_max.setRange(-100000.0, 100000.0)
        self.spin_rango_max.setDecimals(2)
        self.spin_rango_max.setValue(100.0)

        self.spin_frecuencia = QSpinBox()
        self.spin_frecuencia.setRange(0, 86400)
        self.spin_frecuencia.setSuffix(" s")
        self.spin_frecuencia.setValue(60)

        self.combo_responsable = QComboBox()
        self.combo_responsable.addItem("Sin asignar", None)
        for usuario in catalogos.usuarios:
            self.combo_responsable.addItem(
                f"{usuario['nombre']} {usuario['apellido']}", usuario["id_usuario"]
            )

        self.check_principal = QCheckBox(
            "Marcar como sensor principal de esta area y parametro"
        )
        self.check_principal.setToolTip(
            "El sensor principal es el que se asigna automaticamente a las "
            "mediciones que llegan del ESP32 para esa area y ese parametro."
        )

        self.campo_descripcion = QPlainTextEdit()
        self.campo_descripcion.setFixedHeight(60)
        self.campo_descripcion.setPlaceholderText("Opcional")

        formulario.addRow("Código *:", self.campo_codigo)
        formulario.addRow("Nombre *:", self.campo_nombre)
        formulario.addRow("Área *:", self.combo_area)
        formulario.addRow("Parámetro *:", self.combo_parametro)
        formulario.addRow("Ubicación:", self.campo_ubicacion)
        formulario.addRow("Modelo:", self.campo_modelo)
        formulario.addRow("Fabricante:", self.campo_fabricante)
        formulario.addRow("N.º de serie:", self.campo_serie)
        formulario.addRow("Protocolo:", self.combo_protocolo)
        formulario.addRow("Rango mínimo:", self.spin_rango_min)
        formulario.addRow("Rango máximo:", self.spin_rango_max)
        formulario.addRow("Frecuencia:", self.spin_frecuencia)
        formulario.addRow("Responsable:", self.combo_responsable)
        formulario.addRow("Descripción:", self.campo_descripcion)
        formulario.addRow("", self.check_principal)
        layout.addLayout(formulario)

        layout.addWidget(QLabel("(*) Campos obligatorios"))

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText("Registrar Sensor")
        botones.accepted.connect(self._validar_y_aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _validar_y_aceptar(self):
        if self.combo_area.count() == 0 or self.combo_parametro.count() == 0:
            QMessageBox.warning(
                self, "Registrar sensor",
                "No hay áreas o parámetros disponibles en el catálogo."
            )
            return
        if not self.campo_codigo.text().strip():
            QMessageBox.warning(self, "Registrar sensor", "El código es obligatorio.")
            return
        if not self.campo_nombre.text().strip():
            QMessageBox.warning(self, "Registrar sensor", "El nombre es obligatorio.")
            return
        if self.spin_rango_min.value() > self.spin_rango_max.value():
            QMessageBox.warning(
                self, "Registrar sensor",
                "El rango mínimo no puede ser mayor que el rango máximo."
            )
            return
        self.accept()

    def marcar_como_principal(self) -> bool:
        return self.check_principal.isChecked()

    def datos(self) -> dict:
        return {
            "codigo": self.campo_codigo.text().strip(),
            "nombre": self.campo_nombre.text().strip(),
            "id_area": self.combo_area.currentData(),
            "id_parametro": self.combo_parametro.currentData(),
            "descripcion": self.campo_descripcion.toPlainText().strip() or None,
            "ubicacion_detalle": self.campo_ubicacion.text().strip() or None,
            "modelo": self.campo_modelo.text().strip() or None,
            "fabricante": self.campo_fabricante.text().strip() or None,
            "numero_serie": self.campo_serie.text().strip() or None,
            "protocolo": self.combo_protocolo.currentData(),
            "rango_minimo": self.spin_rango_min.value(),
            "rango_maximo": self.spin_rango_max.value(),
            "frecuencia_muestreo_seg": self.spin_frecuencia.value() or None,
            "responsable_id": self.combo_responsable.currentData(),
        }

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from app.api import ApiClient
from app.state import Catalogos

SEVERIDADES = ["baja", "media", "alta", "critica"]


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

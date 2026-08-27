from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api import ApiClient
from app.services import ApiWorker, lanzar_worker
from app.state import Catalogos
from app.ui.flow_layout import FlowLayout
from app.ui.table_utils import (
    RANGO_NIVEL,
    ItemOrdenable,
    ajustar_columnas,
    deshabilitar_orden,
    habilitar_orden,
    redimensionar_filas,
)
from app.ui.theme import color_por_nivel, color_texto_estado
from app.utils import formatear_fecha_hora, parsear_fecha_hora


class AlertasPage(QWidget):
    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self._alertas: list[dict] = []
        # Lista (no un solo atributo): evita destruir un hilo todavia en
        # curso si se cambia de pestaña rapido. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []
        self._modo_oscuro = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("Alertas del Sistema")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        contenedor_filtros = QWidget()
        filtros = FlowLayout(contenedor_filtros, spacing_h=10, spacing_v=8)
        self.combo_area = QComboBox()
        self.combo_nivel = QComboBox()
        self.combo_nivel.addItems(["Todos", "bajo", "medio", "alto", "critico"])
        self.check_sin_atender = QCheckBox("Solo sin atender")

        filtros.addWidget(QLabel("Área:"))
        filtros.addWidget(self.combo_area)
        filtros.addWidget(QLabel("Nivel:"))
        filtros.addWidget(self.combo_nivel)
        filtros.addWidget(self.check_sin_atender)

        self.boton_buscar = QPushButton("Buscar")
        self.boton_buscar.setObjectName("Primario")
        self.boton_buscar.clicked.connect(self._buscar)
        filtros.addWidget(self.boton_buscar)

        self.boton_atender = QPushButton("Atender seleccionada")
        self.boton_atender.setObjectName("Secundario")
        self.boton_atender.clicked.connect(self._atender_seleccionada)
        filtros.addWidget(self.boton_atender)
        layout.addWidget(contenedor_filtros)

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha/Hora", "Área", "Tipo", "Nivel", "Descripción", "Estado", "Atendida por"]
        )
        ajustar_columnas(self.tabla, [
            QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla, stretch=1)

    def al_mostrar(self):
        if self.combo_area.count() == 0:
            self.combo_area.addItem("Todas", None)
            for area in self.catalogos.areas:
                self.combo_area.addItem(area["nombre"], area["id_area"])
        self._buscar()

    def aplicar_tema(self, modo_oscuro: bool):
        self._modo_oscuro = modo_oscuro
        self._buscar()

    def _buscar(self):
        nivel = self.combo_nivel.currentText()
        self.boton_buscar.setEnabled(False)
        lanzar_worker(
            self._workers,
            self.cliente.listar_alertas,
            self._on_resultado,
            self._on_error,
            id_area=self.combo_area.currentData(),
            nivel=None if nivel == "Todos" else nivel,
            solo_sin_atender=self.check_sin_atender.isChecked(),
        )

    def _on_resultado(self, alertas: list[dict]):
        self.boton_buscar.setEnabled(True)
        self._alertas = alertas
        deshabilitar_orden(self.tabla)
        self.tabla.setRowCount(len(alertas))
        for fila, a in enumerate(alertas):
            atendida = a.get("nombre_atendio") or ""
            estado = "Atendida" if atendida else "Pendiente"
            nivel = a.get("nivel")
            items = [
                ItemOrdenable(formatear_fecha_hora(a.get("fecha_hora")), parsear_fecha_hora(a.get("fecha_hora"))),
                QTableWidgetItem(a.get("nombre_area", "")),
                QTableWidgetItem(a.get("tipo_alerta", "")),
                ItemOrdenable(str(nivel or "").upper(), RANGO_NIVEL.get(nivel, -1)),
                QTableWidgetItem(a.get("descripcion", "")),
                QTableWidgetItem(estado),
                QTableWidgetItem(atendida),
            ]
            for columna, item in enumerate(items):
                item.setData(Qt.UserRole, a.get("id_alerta"))
                if columna == 3:
                    item.setForeground(QColor("white"))
                    item.setBackground(QColor(color_por_nivel(nivel)))
                if columna == 5 and estado == "Pendiente":
                    item.setForeground(QColor(color_texto_estado(True, self._modo_oscuro)))
                self.tabla.setItem(fila, columna, item)
        habilitar_orden(self.tabla)
        redimensionar_filas(self.tabla)

    def _on_error(self, mensaje: str):
        self.boton_buscar.setEnabled(True)
        QMessageBox.warning(self, "Error", f"No se pudieron cargar las alertas:\n{mensaje}")

    def _atender_seleccionada(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Atender alerta", "Selecciona una alerta de la tabla.")
            return

        # Buscar por id (no por indice de fila): con el orden habilitado,
        # la fila visual ya no coincide necesariamente con la posicion en
        # self._alertas si el usuario ordeno la tabla por una columna.
        item = self.tabla.item(fila, 0)
        id_alerta = item.data(Qt.UserRole) if item else None
        alerta = next((a for a in self._alertas if a.get("id_alerta") == id_alerta), None)
        if alerta is None:
            return

        if alerta.get("nombre_atendio"):
            QMessageBox.information(self, "Atender alerta", "Esta alerta ya fue atendida.")
            return

        if not self.catalogos.usuarios:
            QMessageBox.warning(self, "Atender alerta", "No hay usuarios disponibles en el catálogo.")
            return

        usuario = self.catalogos.usuarios[0]
        respuesta = QMessageBox.question(
            self,
            "Atender alerta",
            f"¿Marcar la alerta #{alerta['id_alerta']} como atendida por "
            f"{usuario['nombre']} {usuario['apellido']}?",
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            self.cliente.atender_alerta(alerta["id_alerta"], usuario["id_usuario"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo atender la alerta:\n{exc}")
            return

        self._buscar()

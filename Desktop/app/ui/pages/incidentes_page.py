from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHeaderView,
    QInputDialog,
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
from app.ui.dialogs import CrearIncidenteDialog
from app.ui.flow_layout import FlowLayout
from app.ui.table_utils import (
    RANGO_SEVERIDAD,
    ItemOrdenable,
    ajustar_columnas,
    deshabilitar_orden,
    habilitar_orden,
    redimensionar_filas,
)
from app.ui.theme import color_por_severidad, color_texto_estado
from app.utils import formatear_fecha_hora, parsear_fecha_hora


class IncidentesPage(QWidget):
    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self._incidentes: list[dict] = []
        # Lista (no un solo atributo): evita destruir un hilo todavia en
        # curso si se cambia de pestaña rapido. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []
        self._modo_oscuro = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("Incidentes Ambientales")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        contenedor_filtros = QWidget()
        filtros = FlowLayout(contenedor_filtros, spacing_h=10, spacing_v=8)
        self.combo_severidad = QComboBox()
        self.combo_severidad.addItems(["Todas", "baja", "media", "alta", "critica"])
        self.check_abiertos = QCheckBox("Solo abiertos")

        filtros.addWidget(QLabel("Severidad:"))
        filtros.addWidget(self.combo_severidad)
        filtros.addWidget(self.check_abiertos)

        self.boton_buscar = QPushButton("Buscar")
        self.boton_buscar.setObjectName("Primario")
        self.boton_buscar.clicked.connect(self._buscar)
        filtros.addWidget(self.boton_buscar)

        self.boton_resolver = QPushButton("Resolver seleccionado")
        self.boton_resolver.setObjectName("Secundario")
        self.boton_resolver.clicked.connect(self._resolver_seleccionado)
        filtros.addWidget(self.boton_resolver)

        self.boton_crear = QPushButton("+ Crear Incidente")
        self.boton_crear.setObjectName("Primario")
        self.boton_crear.clicked.connect(self._crear_incidente)
        filtros.addWidget(self.boton_crear)
        layout.addWidget(contenedor_filtros)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Área", "Título", "Severidad", "Inicio", "Estado", "Responsable"]
        )
        ajustar_columnas(self.tabla, [
            QHeaderView.Stretch, QHeaderView.Stretch, QHeaderView.ResizeToContents,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla, stretch=1)

    def al_mostrar(self):
        self._buscar()

    def aplicar_tema(self, modo_oscuro: bool):
        self._modo_oscuro = modo_oscuro
        self._buscar()

    def _buscar(self):
        severidad = self.combo_severidad.currentText()
        self.boton_buscar.setEnabled(False)
        lanzar_worker(
            self._workers,
            self.cliente.listar_incidentes,
            self._on_resultado,
            self._on_error,
            severidad=None if severidad == "Todas" else severidad,
            solo_abiertos=self.check_abiertos.isChecked(),
        )

    def _on_resultado(self, incidentes: list[dict]):
        self.boton_buscar.setEnabled(True)
        self._incidentes = incidentes
        deshabilitar_orden(self.tabla)
        self.tabla.setRowCount(len(incidentes))
        for fila, i in enumerate(incidentes):
            estado = "Cerrado" if i.get("fecha_fin") else "Abierto"
            severidad = i.get("severidad")
            items = [
                QTableWidgetItem(i.get("nombre_area", "")),
                QTableWidgetItem(i.get("titulo", "")),
                ItemOrdenable(str(severidad or "").upper(), RANGO_SEVERIDAD.get(severidad, -1)),
                ItemOrdenable(formatear_fecha_hora(i.get("fecha_inicio")), parsear_fecha_hora(i.get("fecha_inicio"))),
                QTableWidgetItem(estado),
                QTableWidgetItem(i.get("nombre_responsable") or "Sin asignar"),
            ]
            for columna, item in enumerate(items):
                item.setData(Qt.UserRole, i.get("id_incidente"))
                if columna == 2:
                    item.setForeground(QColor("white"))
                    item.setBackground(QColor(color_por_severidad(severidad)))
                if columna == 4:
                    item.setForeground(QColor(color_texto_estado(estado == "Abierto", self._modo_oscuro)))
                self.tabla.setItem(fila, columna, item)
        habilitar_orden(self.tabla)
        redimensionar_filas(self.tabla)

    def _on_error(self, mensaje: str):
        self.boton_buscar.setEnabled(True)
        QMessageBox.warning(self, "Error", f"No se pudieron cargar los incidentes:\n{mensaje}")

    def _crear_incidente(self):
        if not self.catalogos.areas:
            QMessageBox.warning(self, "Crear incidente", "No hay áreas disponibles en el catálogo.")
            return

        dialogo = CrearIncidenteDialog(self.cliente, self.catalogos, parent=self)
        if dialogo.exec() != CrearIncidenteDialog.Accepted:
            return

        try:
            self.cliente.crear_incidente(**dialogo.datos())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo crear el incidente:\n{exc}")
            return

        QMessageBox.information(self, "Crear incidente", "Incidente creado correctamente.")
        self._buscar()

    def _resolver_seleccionado(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Resolver incidente", "Selecciona un incidente de la tabla.")
            return

        # Buscar por id (no por indice de fila): con el orden habilitado,
        # la fila visual ya no coincide necesariamente con la posicion en
        # self._incidentes si el usuario ordeno la tabla por una columna.
        item = self.tabla.item(fila, 0)
        id_incidente = item.data(Qt.UserRole) if item else None
        incidente = next((i for i in self._incidentes if i.get("id_incidente") == id_incidente), None)
        if incidente is None:
            return

        if incidente.get("fecha_fin"):
            QMessageBox.information(self, "Resolver incidente", "Este incidente ya está cerrado.")
            return

        acciones, ok = QInputDialog.getMultiLineText(
            self,
            "Resolver incidente",
            f"Acciones realizadas para cerrar '{incidente.get('titulo')}':",
        )
        if not ok or not acciones.strip():
            return

        try:
            self.cliente.resolver_incidente(incidente["id_incidente"], acciones.strip())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo resolver el incidente:\n{exc}")
            return

        self._buscar()

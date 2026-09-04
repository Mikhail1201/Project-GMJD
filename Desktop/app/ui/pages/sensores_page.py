from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
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
from app.ui.dialogs import CrearSensorDialog
from app.ui.flow_layout import FlowLayout
from app.ui.table_utils import (
    ItemOrdenable,
    ajustar_columnas,
    deshabilitar_orden,
    habilitar_orden,
    redimensionar_filas,
)
from app.ui.theme import color_texto_estado
from app.utils import ZONA_BOGOTA, formatear_fecha_hora, parsear_fecha_hora


def _ya_vencio(fecha, ahora) -> bool:
    """True si la fecha de calibracion ya paso.

    parsear_fecha_hora() devuelve la fecha con zona horaria cuando el backend
    manda el formato HTTP-date (el caso normal), pero sin zona si llega en
    otro formato. Comparar una fecha con zona contra una sin zona lanza
    TypeError, asi que aqui se igualan antes de comparar.
    """
    if fecha is None:
        return False
    if fecha.tzinfo is None:
        return fecha < ahora.replace(tzinfo=None)
    return fecha < ahora


class SensoresPage(QWidget):
    """Inventario de sensores fisicos de la planta.

    Cada sensor dice que parametro mide y en que area esta instalado; el
    marcado como "principal" es el que el backend asigna automaticamente a
    las mediciones que llegan del ESP32 para esa area y ese parametro.
    """

    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self._sensores: list[dict] = []
        # Lista (no un solo atributo): evita destruir un hilo todavia en
        # curso si se cambia de pestaña rapido. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []
        self._modo_oscuro = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("Sensores Instalados")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        contenedor_filtros = QWidget()
        filtros = FlowLayout(contenedor_filtros, spacing_h=10, spacing_v=8)

        self.combo_area = QComboBox()
        self.combo_parametro = QComboBox()

        self.campo_busqueda = QLineEdit()
        self.campo_busqueda.setPlaceholderText("Código, nombre, serie o modelo")
        self.campo_busqueda.setMinimumWidth(200)
        self.campo_busqueda.returnPressed.connect(self._buscar)

        self.check_principales = QCheckBox("Solo principales")
        self.check_vencidos = QCheckBox("Calibración vencida")
        self.check_eliminados = QCheckBox("Incluir eliminados")

        filtros.addWidget(QLabel("Área:"))
        filtros.addWidget(self.combo_area)
        filtros.addWidget(QLabel("Parámetro:"))
        filtros.addWidget(self.combo_parametro)
        filtros.addWidget(QLabel("Buscar:"))
        filtros.addWidget(self.campo_busqueda)
        filtros.addWidget(self.check_principales)
        filtros.addWidget(self.check_vencidos)
        filtros.addWidget(self.check_eliminados)

        self.boton_buscar = QPushButton("Buscar")
        self.boton_buscar.setObjectName("Primario")
        self.boton_buscar.clicked.connect(self._buscar)
        filtros.addWidget(self.boton_buscar)

        self.boton_crear = QPushButton("+ Registrar Sensor")
        self.boton_crear.setObjectName("Primario")
        self.boton_crear.clicked.connect(self._crear_sensor)
        filtros.addWidget(self.boton_crear)

        self.boton_calibrar = QPushButton("Registrar calibración")
        self.boton_calibrar.setObjectName("Secundario")
        self.boton_calibrar.clicked.connect(self._registrar_calibracion)
        filtros.addWidget(self.boton_calibrar)

        self.boton_principal = QPushButton("Marcar como principal")
        self.boton_principal.setObjectName("Secundario")
        self.boton_principal.clicked.connect(self._marcar_principal)
        filtros.addWidget(self.boton_principal)

        layout.addWidget(contenedor_filtros)

        self.tabla = QTableWidget(0, 10)
        self.tabla.setHorizontalHeaderLabels([
            "Código", "Nombre", "Área", "Parámetro", "Modelo",
            "Ubicación", "Instalación", "Próx. calibración", "Responsable", "Estado",
        ])
        ajustar_columnas(self.tabla, [
            QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.Stretch,
            QHeaderView.Stretch, QHeaderView.ResizeToContents, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla, stretch=1)

        self.label_resumen = QLabel("")
        self.label_resumen.setObjectName("TextoSecundario")
        layout.addWidget(self.label_resumen)

    def al_mostrar(self):
        if self.combo_area.count() == 0:
            self.combo_area.addItem("Todas", None)
            for area in self.catalogos.areas:
                self.combo_area.addItem(area["nombre"], area["id_area"])

        if self.combo_parametro.count() == 0:
            self.combo_parametro.addItem("Todos", None)
            for parametro in self.catalogos.parametros:
                self.combo_parametro.addItem(parametro["nombre"], parametro["id_parametro"])

        self._buscar()

    def aplicar_tema(self, modo_oscuro: bool):
        self._modo_oscuro = modo_oscuro
        self._buscar()

    def _buscar(self):
        self.boton_buscar.setEnabled(False)
        lanzar_worker(
            self._workers,
            self.cliente.listar_sensores,
            self._on_resultado,
            self._on_error,
            id_area=self.combo_area.currentData(),
            id_parametro=self.combo_parametro.currentData(),
            busqueda=self.campo_busqueda.text().strip() or None,
            solo_principales=self.check_principales.isChecked(),
            calibracion_vencida=self.check_vencidos.isChecked(),
            incluir_eliminados=self.check_eliminados.isChecked(),
        )

    def _on_resultado(self, sensores: list[dict]):
        self.boton_buscar.setEnabled(True)
        self._sensores = sensores

        ahora = datetime.now(ZONA_BOGOTA)

        deshabilitar_orden(self.tabla)
        self.tabla.setRowCount(len(sensores))
        for fila, s in enumerate(sensores):
            proxima = parsear_fecha_hora(s.get("fecha_proxima_calibracion"))
            vencida = _ya_vencio(proxima, ahora)

            codigo = s.get("codigo", "")
            if s.get("es_principal"):
                codigo = f"* {codigo}"

            unidad = s.get("unidad_parametro") or ""
            parametro = s.get("nombre_parametro", "")
            if unidad:
                parametro = f"{parametro} ({unidad})"

            modelo = " / ".join(
                p for p in (s.get("modelo"), s.get("fabricante")) if p
            ) or "—"

            items = [
                # El texto lleva el "*" del principal, pero se ordena por el
                # codigo limpio: si no, los marcados se separarian del resto
                # al ordenar por esta columna.
                ItemOrdenable(codigo, s.get("codigo", "")),
                QTableWidgetItem(s.get("nombre", "")),
                QTableWidgetItem(s.get("nombre_area", "")),
                QTableWidgetItem(parametro),
                QTableWidgetItem(modelo),
                QTableWidgetItem(s.get("ubicacion_detalle") or "—"),
                ItemOrdenable(
                    formatear_fecha_hora(s.get("fecha_instalacion")),
                    parsear_fecha_hora(s.get("fecha_instalacion")),
                ),
                ItemOrdenable(formatear_fecha_hora(s.get("fecha_proxima_calibracion")), proxima),
                QTableWidgetItem(s.get("nombre_responsable") or "Sin asignar"),
                QTableWidgetItem(s.get("nombre_estado", "")),
            ]

            for columna, item in enumerate(items):
                # Buscar por id (no por indice de fila): con el orden
                # habilitado la fila visual ya no corresponde a self._sensores.
                item.setData(Qt.UserRole, s.get("id_sensor"))
                if columna == 7 and proxima is not None:
                    item.setForeground(QColor(color_texto_estado(vencida, self._modo_oscuro)))
                self.tabla.setItem(fila, columna, item)

        habilitar_orden(self.tabla)
        redimensionar_filas(self.tabla)

        principales = sum(1 for s in sensores if s.get("es_principal"))
        self.label_resumen.setText(
            f"{len(sensores)} sensores · {principales} marcados como principales "
            f"(*) · el principal es el que se asigna solo a las mediciones del ESP32"
        )

    def _on_error(self, mensaje: str):
        self.boton_buscar.setEnabled(True)
        QMessageBox.warning(self, "Error", f"No se pudieron cargar los sensores:\n{mensaje}")

    def _sensor_seleccionado(self) -> dict | None:
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Sensores", "Selecciona un sensor de la tabla.")
            return None

        item = self.tabla.item(fila, 0)
        id_sensor = item.data(Qt.UserRole) if item else None
        return next((s for s in self._sensores if s.get("id_sensor") == id_sensor), None)

    def _crear_sensor(self):
        if not self.catalogos.areas or not self.catalogos.parametros:
            QMessageBox.warning(
                self, "Registrar sensor",
                "No hay áreas o parámetros disponibles en el catálogo."
            )
            return

        dialogo = CrearSensorDialog(self.catalogos, parent=self)
        if dialogo.exec() != CrearSensorDialog.Accepted:
            return

        try:
            nuevo = self.cliente.crear_sensor(**dialogo.datos())
            if dialogo.marcar_como_principal():
                self.cliente.marcar_sensor_principal(nuevo["id_sensor"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo registrar el sensor:\n{exc}")
            return

        QMessageBox.information(self, "Registrar sensor", "Sensor registrado correctamente.")
        self._buscar()

    def _registrar_calibracion(self):
        sensor = self._sensor_seleccionado()
        if sensor is None:
            return

        respuesta = QMessageBox.question(
            self, "Registrar calibración",
            f"¿Registrar la calibración de '{sensor.get('codigo')}' con fecha de hoy?\n"
            "La próxima calibración quedará programada en 12 meses.",
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            self.cliente.registrar_calibracion_sensor(sensor["id_sensor"], meses_proxima=12)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo registrar la calibración:\n{exc}")
            return

        self._buscar()

    def _marcar_principal(self):
        sensor = self._sensor_seleccionado()
        if sensor is None:
            return

        if sensor.get("es_principal"):
            QMessageBox.information(
                self, "Sensores", "Este sensor ya es el principal de su área y parámetro."
            )
            return

        respuesta = QMessageBox.question(
            self, "Marcar como principal",
            f"'{sensor.get('codigo')}' pasará a ser el sensor principal de "
            f"{sensor.get('nombre_area')} / {sensor.get('nombre_parametro')}.\n\n"
            "Las mediciones nuevas de esa combinación se le asignarán a este sensor. "
            "¿Continuar?",
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            self.cliente.marcar_sensor_principal(sensor["id_sensor"])
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo marcar como principal:\n{exc}")
            return

        self._buscar()

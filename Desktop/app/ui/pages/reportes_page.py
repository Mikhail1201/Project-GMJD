from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.api import ApiClient
from app.services import ApiWorker, GeneradorReportePDF, lanzar_worker
from app.state import Catalogos
from app.utils import fecha_local_a_utc_str


class ReportesPage(QWidget):
    """Genera reportes en PDF de mediciones y alertas para un area y rango de fechas."""

    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        # Lista (no un solo atributo): evita destruir un hilo todavia en
        # curso si se reasigna antes de que termine. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []
        self._mediciones_pendientes: list[dict] | None = None
        self._alertas_pendientes: list[dict] | None = None
        self._esperando = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        titulo = QLabel("Generar Reporte PDF")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        tarjeta = QFrame()
        tarjeta.setObjectName("Card")
        formulario = QFormLayout(tarjeta)
        formulario.setContentsMargins(20, 20, 20, 20)
        formulario.setSpacing(12)

        self.combo_area = QComboBox()
        self.fecha_desde = QDateEdit(calendarPopup=True)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-6))
        self.fecha_hasta = QDateEdit(calendarPopup=True)
        self.fecha_hasta.setDate(QDate.currentDate())
        self.check_mediciones = QCheckBox("Incluir mediciones")
        self.check_mediciones.setChecked(True)
        self.check_alertas = QCheckBox("Incluir alertas")
        self.check_alertas.setChecked(True)

        formulario.addRow("Área:", self.combo_area)
        formulario.addRow("Desde:", self.fecha_desde)
        formulario.addRow("Hasta:", self.fecha_hasta)
        formulario.addRow(self.check_mediciones)
        formulario.addRow(self.check_alertas)

        layout.addWidget(tarjeta)

        botones = QHBoxLayout()
        self.boton_generar = QPushButton("Generar PDF")
        self.boton_generar.setObjectName("Primario")
        self.boton_generar.clicked.connect(self._generar)
        botones.addWidget(self.boton_generar)
        botones.addStretch()
        layout.addLayout(botones)

        self.label_estado = QLabel("")
        self.label_estado.setStyleSheet("color: #6B7385;")
        layout.addWidget(self.label_estado)
        layout.addStretch()

    def al_mostrar(self):
        if self.combo_area.count() == 0:
            self.combo_area.addItem("Todas las áreas", None)
            for area in self.catalogos.areas:
                self.combo_area.addItem(area["nombre"], area["id_area"])

    def _generar(self):
        if not self.check_mediciones.isChecked() and not self.check_alertas.isChecked():
            QMessageBox.information(self, "Generar reporte", "Selecciona al menos un tipo de dato a incluir.")
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte", "reporte_monomeros.pdf", "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return

        self._ruta_destino = ruta
        self._mediciones_pendientes = [] if not self.check_mediciones.isChecked() else None
        self._alertas_pendientes = [] if not self.check_alertas.isChecked() else None
        self._esperando = 0
        self.boton_generar.setEnabled(False)
        self.label_estado.setText("Consultando datos...")

        desde = self.fecha_desde.date()
        hasta = self.fecha_hasta.date().addDays(1)
        filtros = {
            "id_area": self.combo_area.currentData(),
            # Convertido a UTC real (el backend guarda fecha_hora en UTC):
            # mandar la fecha del calendario tal cual filtraba con el dia
            # de Bogota corrido, excluyendo mediciones de la noche.
            "fecha_desde": fecha_local_a_utc_str(desde.year(), desde.month(), desde.day()),
            "fecha_hasta": fecha_local_a_utc_str(hasta.year(), hasta.month(), hasta.day()),
        }

        if self.check_mediciones.isChecked():
            self._esperando += 1
            lanzar_worker(
                self._workers, self.cliente.listar_mediciones,
                self._on_mediciones, self._on_error,
                pagina=1, por_pagina=200, **filtros,
            )

        if self.check_alertas.isChecked():
            self._esperando += 1
            lanzar_worker(
                self._workers, self.cliente.listar_alertas,
                self._on_alertas, self._on_error,
                id_area=filtros["id_area"],
            )

    def _on_mediciones(self, resultado: dict):
        datos = resultado.get("datos", [])
        self._mediciones_pendientes = [
            {
                **m,
                "nombre_area": self.catalogos.nombre_area(m.get("id_area")),
                "nombre_parametro": self.catalogos.nombre_parametro(m.get("id_parametro")),
            }
            for m in datos
        ]
        self._esperando -= 1
        self._intentar_finalizar()

    def _on_alertas(self, alertas: list[dict]):
        self._alertas_pendientes = alertas
        self._esperando -= 1
        self._intentar_finalizar()

    def _on_error(self, mensaje: str):
        self.boton_generar.setEnabled(True)
        self.label_estado.setText("")
        QMessageBox.critical(self, "Error", f"No se pudieron obtener los datos:\n{mensaje}")

    def _intentar_finalizar(self):
        if self._esperando > 0:
            return

        self.label_estado.setText("Generando PDF...")
        try:
            GeneradorReportePDF().generar(
                self._ruta_destino,
                mediciones=self._mediciones_pendientes,
                alertas=self._alertas_pendientes,
                filtros_aplicados={
                    "Área": self.combo_area.currentText(),
                    "Desde": self.fecha_desde.date().toString("dd/MM/yyyy"),
                    "Hasta": self.fecha_hasta.date().toString("dd/MM/yyyy"),
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.boton_generar.setEnabled(True)
            self.label_estado.setText("")
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{exc}")
            return

        self.boton_generar.setEnabled(True)
        self.label_estado.setText(f"Reporte generado: {self._ruta_destino}")
        QMessageBox.information(self, "Reporte generado", f"El reporte se guardó en:\n{self._ruta_destino}")

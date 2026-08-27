from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from app.api import ApiClient
from app.services import ApiWorker, GeneradorReportePDF, lanzar_worker
from app.state import Catalogos
from app.ui.flow_layout import FlowLayout
from app.ui.table_utils import (
    ItemOrdenable,
    ajustar_columnas,
    deshabilitar_orden,
    habilitar_orden,
    redimensionar_filas,
)
from app.utils import fecha_local_a_utc_str, formatear_fecha_hora, parsear_fecha_hora, parsear_numero


class HistorialPage(QWidget):
    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self._pagina_actual = 1
        self._total_paginas = 1
        self._ultimos_datos: list[dict] = []
        # Lista (no un solo atributo): si se reasigna un worker en curso se
        # suelta su referencia mientras el hilo sigue vivo y Python lo
        # destruye a la fuerza -> crash. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        layout_raiz.addWidget(scroll)

        contenido = QWidget()
        scroll.setWidget(contenido)

        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        titulo = QLabel("Historial de Mediciones")
        titulo.setObjectName("PageTitle")
        layout.addWidget(titulo)

        contenedor_filtros = QWidget()
        filtros = FlowLayout(contenedor_filtros, spacing_h=10, spacing_v=8)
        self.combo_area = QComboBox()
        self.combo_parametro = QComboBox()
        self.combo_calidad = QComboBox()
        self.combo_calidad.addItems(["Todas", "valida", "sospechosa", "invalida"])
        self.fecha_desde = QDateEdit(calendarPopup=True)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-6))
        self.fecha_hasta = QDateEdit(calendarPopup=True)
        self.fecha_hasta.setDate(QDate.currentDate())

        for etiqueta, widget in [
            ("Área:", self.combo_area),
            ("Parámetro:", self.combo_parametro),
            ("Calidad:", self.combo_calidad),
            ("Desde:", self.fecha_desde),
            ("Hasta:", self.fecha_hasta),
        ]:
            filtros.addWidget(QLabel(etiqueta))
            filtros.addWidget(widget)

        self.boton_buscar = QPushButton("Buscar")
        self.boton_buscar.setObjectName("Primario")
        self.boton_buscar.clicked.connect(self._buscar)
        filtros.addWidget(self.boton_buscar)

        self.boton_pdf = QPushButton("Exportar PDF")
        self.boton_pdf.setObjectName("Secundario")
        self.boton_pdf.clicked.connect(self._exportar_pdf)
        filtros.addWidget(self.boton_pdf)
        layout.addWidget(contenedor_filtros)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha/Hora", "Área", "Parámetro", "Valor", "Calidad", "Observación"]
        )
        ajustar_columnas(self.tabla, [
            QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents, QHeaderView.Stretch,
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setMinimumHeight(320)
        layout.addWidget(self.tabla)

        paginacion = QHBoxLayout()
        self.boton_anterior = QPushButton("< Anterior")
        self.boton_anterior.clicked.connect(self._pagina_anterior)
        self.label_pagina = QLabel("Página 1 de 1")
        self.boton_siguiente = QPushButton("Siguiente >")
        self.boton_siguiente.clicked.connect(self._pagina_siguiente)

        self.spin_pagina = QSpinBox()
        self.spin_pagina.setMinimum(1)
        self.spin_pagina.setMaximum(1)
        self.spin_pagina.setFixedWidth(70)
        self.boton_ir_pagina = QPushButton("Ir")
        self.boton_ir_pagina.setObjectName("Secundario")
        self.boton_ir_pagina.clicked.connect(self._ir_a_pagina)
        self.spin_pagina.editingFinished.connect(self._ir_a_pagina)

        paginacion.addStretch()
        paginacion.addWidget(self.boton_anterior)
        paginacion.addWidget(self.label_pagina)
        paginacion.addWidget(self.boton_siguiente)
        paginacion.addSpacing(16)
        paginacion.addWidget(QLabel("Ir a página:"))
        paginacion.addWidget(self.spin_pagina)
        paginacion.addWidget(self.boton_ir_pagina)
        paginacion.addStretch()
        layout.addLayout(paginacion)

    def al_mostrar(self):
        if self.combo_area.count() == 0:
            self.combo_area.addItem("Todas", None)
            for area in self.catalogos.areas:
                self.combo_area.addItem(area["nombre"], area["id_area"])
        if self.combo_parametro.count() == 0:
            self.combo_parametro.addItem("Todos", None)
            for parametro in self.catalogos.parametros:
                self.combo_parametro.addItem(parametro["nombre"], parametro["id_parametro"])
        if not self._ultimos_datos:
            self._buscar()

    def _filtros_actuales(self) -> dict:
        calidad = self.combo_calidad.currentText()
        desde = self.fecha_desde.date()
        hasta = self.fecha_hasta.date().addDays(1)
        return {
            "id_area": self.combo_area.currentData(),
            "id_parametro": self.combo_parametro.currentData(),
            "calidad_dato": None if calidad == "Todas" else calidad,
            # Convertido a UTC real (el backend guarda fecha_hora en UTC):
            # mandar la fecha del calendario tal cual filtraba con el dia
            # de Bogota corrido, excluyendo mediciones de la noche.
            "fecha_desde": fecha_local_a_utc_str(desde.year(), desde.month(), desde.day()),
            "fecha_hasta": fecha_local_a_utc_str(hasta.year(), hasta.month(), hasta.day()),
        }

    def _buscar(self):
        self._pagina_actual = 1
        self._consultar()

    def _consultar(self):
        self._fijar_controles_habilitados(False)
        lanzar_worker(
            self._workers,
            self.cliente.listar_mediciones,
            self._on_resultado,
            self._on_error,
            pagina=self._pagina_actual,
            por_pagina=25,
            **self._filtros_actuales(),
        )

    def _fijar_controles_habilitados(self, habilitados: bool):
        self.boton_buscar.setEnabled(habilitados)
        self.boton_anterior.setEnabled(habilitados and self._pagina_actual > 1)
        self.boton_siguiente.setEnabled(habilitados and self._pagina_actual < self._total_paginas)
        # blockSignals: deshabilitar un QSpinBox que tiene el foco dispara
        # su señal editingFinished como efecto secundario (pierde el foco
        # al desactivarse). Sin este bloqueo, eso reentraba en
        # _ir_a_pagina() a mitad de _consultar() -antes de que el spin
        # tuviera el numero de pagina nuevo- y terminaba pisando
        # self._pagina_actual de vuelta al valor viejo: por eso "Siguiente"
        # parecia no hacer nada.
        self.spin_pagina.blockSignals(True)
        self.spin_pagina.setEnabled(habilitados)
        self.spin_pagina.blockSignals(False)
        self.boton_ir_pagina.setEnabled(habilitados)

    def _ir_a_pagina(self):
        pagina = self.spin_pagina.value()
        if pagina != self._pagina_actual:
            self._pagina_actual = pagina
            self._consultar()

    def _on_resultado(self, resultado: dict):
        datos = resultado.get("datos", [])
        self._ultimos_datos = datos
        paginacion = resultado.get("paginacion", {})
        self._total_paginas = max(paginacion.get("total_paginas", 1), 1)
        self.label_pagina.setText(
            f"Página {self._pagina_actual} de {self._total_paginas} "
            f"({paginacion.get('total', len(datos))} registros)"
        )
        self.spin_pagina.setMaximum(self._total_paginas)
        self.spin_pagina.setValue(self._pagina_actual)

        deshabilitar_orden(self.tabla)
        self.tabla.setRowCount(len(datos))
        for fila, m in enumerate(datos):
            self.tabla.setItem(fila, 0, ItemOrdenable(
                formatear_fecha_hora(m.get("fecha_hora")), parsear_fecha_hora(m.get("fecha_hora"))
            ))
            self.tabla.setItem(fila, 1, QTableWidgetItem(self.catalogos.nombre_area(m.get("id_area"))))
            self.tabla.setItem(fila, 2, QTableWidgetItem(self.catalogos.nombre_parametro(m.get("id_parametro"))))
            self.tabla.setItem(fila, 3, ItemOrdenable(
                f"{m.get('valor')} {self.catalogos.unidad_parametro(m.get('id_parametro'))}",
                parsear_numero(m.get("valor")),
            ))
            self.tabla.setItem(fila, 4, QTableWidgetItem(str(m.get("calidad_dato", ""))))
            self.tabla.setItem(fila, 5, QTableWidgetItem(str(m.get("observacion") or "")))
        habilitar_orden(self.tabla)
        redimensionar_filas(self.tabla)
        self._fijar_controles_habilitados(True)

    def _on_error(self, mensaje: str):
        self._fijar_controles_habilitados(True)
        QMessageBox.warning(self, "Error", f"No se pudo consultar el historial:\n{mensaje}")

    def _pagina_anterior(self):
        if self._pagina_actual > 1:
            self._pagina_actual -= 1
            self._consultar()

    def _pagina_siguiente(self):
        if self._pagina_actual < self._total_paginas:
            self._pagina_actual += 1
            self._consultar()

    def _exportar_pdf(self):
        if not self._ultimos_datos:
            QMessageBox.information(self, "Exportar PDF", "No hay datos cargados para exportar.")
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar reporte", "historial_mediciones.pdf", "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return

        datos_enriquecidos = [
            {
                **m,
                "nombre_area": self.catalogos.nombre_area(m.get("id_area")),
                "nombre_parametro": self.catalogos.nombre_parametro(m.get("id_parametro")),
            }
            for m in self._ultimos_datos
        ]

        try:
            GeneradorReportePDF().generar(
                ruta,
                mediciones=datos_enriquecidos,
                filtros_aplicados=self._filtros_actuales(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{exc}")
            return

        QMessageBox.information(self, "Exportar PDF", f"Reporte generado en:\n{ruta}")

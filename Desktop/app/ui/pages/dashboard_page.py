from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.api import ApiClient
from app.config import INTERVALO_REFRESCO_MS
from app.services import ApiWorker, lanzar_worker
from app.state import Catalogos
from app.ui.table_utils import (
    RANGO_NIVEL,
    ItemOrdenable,
    ajustar_columnas,
    deshabilitar_orden,
    habilitar_orden,
    redimensionar_filas,
)
from app.ui.theme import PALETA_CLARA, PALETA_OSCURA, color_por_nivel
from app.ui.widgets import GaugeWidget
from app.utils import formatear_fecha_hora, parsear_fecha_hora, parsear_numero

PARAMETROS_EN_TABLERO = [
    "Temperatura Ambiente",
    "Humedad Relativa",
    "Gas Amoniaco (NH3)",
    "Nivel de Ruido",
]


class DashboardPage(QWidget):
    def __init__(self, cliente: ApiClient, catalogos: Catalogos, parent=None):
        super().__init__(parent)
        self.cliente = cliente
        self.catalogos = catalogos
        self._workers: list[ApiWorker] = []
        self._gauges: dict[str, GaugeWidget] = {}
        self._modo_oscuro = False

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        layout_raiz.addWidget(scroll)

        contenido = QWidget()
        scroll.setWidget(contenido)

        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        encabezado = QHBoxLayout()
        titulo = QLabel("Panel de Monitoreo en Tiempo Real")
        titulo.setObjectName("PageTitle")
        self.label_actualizacion = QLabel("Actualizando...")
        self.label_actualizacion.setObjectName("TextoSecundario")
        encabezado.addWidget(titulo)
        encabezado.addStretch()
        encabezado.addWidget(self.label_actualizacion)
        layout.addLayout(encabezado)

        self.label_estado_global = QLabel("Áreas: -- | Mediciones (24h): -- | Alertas sin atender: -- | Incidentes abiertos: --")
        self.label_estado_global.setObjectName("TextoSecundario")
        layout.addWidget(self.label_estado_global)

        # Fila principal: gauges a la izquierda, ultimas mediciones a la
        # derecha (mismo espiritu que el ejemplo del PDF: estado en tiempo
        # real a un lado, datos/tabla al otro, en paralelo).
        fila_principal = QHBoxLayout()
        fila_principal.setSpacing(20)

        columna_izquierda = QVBoxLayout()
        columna_izquierda.setSpacing(10)
        subtitulo_gauges = QLabel("Indicadores en Tiempo Real")
        subtitulo_gauges.setObjectName("Subtitulo")
        columna_izquierda.addWidget(subtitulo_gauges)

        cuadricula_gauges = QGridLayout()
        cuadricula_gauges.setSpacing(12)
        columnas = 2
        for indice, nombre in enumerate(PARAMETROS_EN_TABLERO):
            gauge = GaugeWidget(titulo=nombre)
            self._gauges[nombre] = gauge
            fila, columna = divmod(indice, columnas)
            cuadricula_gauges.addWidget(gauge, fila, columna)
        columna_izquierda.addLayout(cuadricula_gauges)
        columna_izquierda.addStretch()

        columna_izquierda_widget = QWidget()
        columna_izquierda_widget.setLayout(columna_izquierda)
        columna_izquierda_widget.setMaximumWidth(330)
        fila_principal.addWidget(columna_izquierda_widget)

        columna_derecha = QVBoxLayout()
        columna_derecha.setSpacing(10)
        subtitulo = QLabel("Últimas mediciones recibidas de los sensores (ESP32)")
        subtitulo.setObjectName("Subtitulo")
        columna_derecha.addWidget(subtitulo)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Fecha/Hora", "Área", "Parámetro", "Valor", "Calidad"])
        ajustar_columnas(self.tabla, [
            QHeaderView.ResizeToContents, QHeaderView.Stretch, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
        ])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setMinimumHeight(260)
        columna_derecha.addWidget(self.tabla)

        fila_principal.addLayout(columna_derecha, stretch=1)
        layout.addLayout(fila_principal)

        subtitulo_alertas = QLabel("Alertas críticas / altas recientes")
        subtitulo_alertas.setObjectName("Subtitulo")
        layout.addWidget(subtitulo_alertas)

        self.tabla_alertas = QTableWidget(0, 4)
        self.tabla_alertas.setHorizontalHeaderLabels(["Fecha/Hora", "Área", "Nivel", "Descripción"])
        ajustar_columnas(self.tabla_alertas, [
            QHeaderView.ResizeToContents, QHeaderView.Stretch,
            QHeaderView.ResizeToContents, QHeaderView.Stretch,
        ])
        self.tabla_alertas.verticalHeader().setVisible(False)
        self.tabla_alertas.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_alertas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_alertas.setMaximumHeight(180)
        layout.addWidget(self.tabla_alertas)

        self._areas_total = 0
        self._alertas_total = 0
        self._incidentes_total = 0
        self._mediciones_total = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refrescar)
        self._timer.start(INTERVALO_REFRESCO_MS)

    def al_mostrar(self):
        self.refrescar()

    def detener(self):
        """Frena el auto-refresco; se llama al cerrar la ventana para que no
        se disparen mas peticiones mientras se espera a que terminen las
        que ya estaban en curso."""
        self._timer.stop()

    def aplicar_tema(self, modo_oscuro: bool):
        self._modo_oscuro = modo_oscuro
        paleta = PALETA_OSCURA if modo_oscuro else PALETA_CLARA
        for gauge in self._gauges.values():
            gauge.aplicar_paleta(paleta)
        self.refrescar()

    def refrescar(self):
        self.label_actualizacion.setText("Actualizando...")
        self._lanzar(self.cliente.listar_mediciones, self._on_mediciones, pagina=1, por_pagina=15)
        self._lanzar(self.cliente.listar_alertas, self._on_alertas, solo_sin_atender=True)
        self._lanzar(self.cliente.listar_incidentes, self._on_incidentes, solo_abiertos=True)
        self._refrescar_gauges()

    def _refrescar_gauges(self):
        for nombre, parametro in self._parametros_tablero():
            self._lanzar(
                self.cliente.listar_mediciones,
                lambda resultado, nombre=nombre, parametro=parametro: self._on_gauge(resultado, nombre, parametro),
                pagina=1,
                por_pagina=1,
                id_parametro=parametro["id_parametro"],
            )

    def _parametros_tablero(self):
        for nombre in PARAMETROS_EN_TABLERO:
            parametro = next((p for p in self.catalogos.parametros if p["nombre"] == nombre), None)
            if parametro:
                yield nombre, parametro

    def _on_gauge(self, resultado: dict, nombre: str, parametro: dict):
        datos = resultado.get("datos", [])
        gauge = self._gauges.get(nombre)
        if not gauge:
            return
        gauge.unidad = parametro.get("unidad", "")
        if datos:
            valor = float(datos[0]["valor"])
            gauge.actualizar(valor, parametro.get("limite_minimo"), parametro.get("limite_maximo"))
        else:
            gauge.actualizar(0.0, parametro.get("limite_minimo"), parametro.get("limite_maximo"))

    def _lanzar(self, funcion, callback_exito, *args, **kwargs):
        lanzar_worker(self._workers, funcion, callback_exito, self._on_error, *args, **kwargs)

    def _on_mediciones(self, resultado: dict):
        datos = resultado.get("datos", [])
        self._mediciones_total = resultado.get("paginacion", {}).get("total", len(datos))
        self._areas_total = len(self.catalogos.areas)
        self._actualizar_estado_global()

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
        habilitar_orden(self.tabla)
        redimensionar_filas(self.tabla)
        self.label_actualizacion.setText("Actualizado")

    def _on_alertas(self, alertas: list[dict]):
        self._alertas_total = len(alertas)
        self._actualizar_estado_global()

        criticas = [a for a in alertas if a.get("nivel") in ("alto", "critico")][:10]
        deshabilitar_orden(self.tabla_alertas)
        self.tabla_alertas.setRowCount(len(criticas))
        for fila, a in enumerate(criticas):
            nivel = a.get("nivel")
            valores = [
                ItemOrdenable(formatear_fecha_hora(a.get("fecha_hora")), parsear_fecha_hora(a.get("fecha_hora"))),
                QTableWidgetItem(a.get("nombre_area", "")),
                ItemOrdenable(str(nivel or "").upper(), RANGO_NIVEL.get(nivel, -1)),
                QTableWidgetItem(a.get("descripcion", "")),
            ]
            for columna, item in enumerate(valores):
                if columna == 2:
                    item.setForeground(Qt.white)
                    item.setBackground(QColor(color_por_nivel(nivel)))
                self.tabla_alertas.setItem(fila, columna, item)
        habilitar_orden(self.tabla_alertas)
        redimensionar_filas(self.tabla_alertas)

    def _on_incidentes(self, incidentes: list[dict]):
        self._incidentes_total = len(incidentes)
        self._actualizar_estado_global()

    def _actualizar_estado_global(self):
        self.label_estado_global.setText(
            f"Áreas: {self._areas_total} | Mediciones (24h): {self._mediciones_total} | "
            f"Alertas sin atender: {self._alertas_total} | Incidentes abiertos: {self._incidentes_total}"
        )

    def _on_error(self, mensaje: str):
        self.label_actualizacion.setText(f"Error: {mensaje}")

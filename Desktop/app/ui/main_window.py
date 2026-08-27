from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.api import ApiClient
from app.config import INTERVALO_REFRESCO_MS
from app.services import ApiWorker, lanzar_worker
from app.state import Catalogos
from app.ui.pages.alertas_page import AlertasPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.historial_page import HistorialPage
from app.ui.pages.incidentes_page import IncidentesPage
from app.ui.pages.reportes_page import ReportesPage
from app.ui.theme import (
    HOJA_ESTILOS_CLARO,
    HOJA_ESTILOS_OSCURO,
    estilo_badge_estado,
)

TEXTO_ESTADO = {
    "ok": "●  Backend conectado",
    "error": "●  Backend sin conexión",
    "verificando": "●  Verificando backend...",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Monitoreo Ambiental - Monomeros S.A.")
        self.resize(1180, 720)
        self.setMinimumSize(760, 560)

        self.cliente = ApiClient()
        self.catalogos = Catalogos()
        # Lista (no un solo atributo): evita destruir un hilo todavia en
        # curso si se reasigna antes de que termine. Ver app/services/worker.py.
        self._workers: list[ApiWorker] = []
        self._estado_conexion = "verificando"

        self._config = QSettings("Monomeros", "MonitoreoAmbiental")
        self._modo_oscuro = self._config.value("modo_oscuro", False, type=bool)
        QApplication.instance().setStyleSheet(
            HOJA_ESTILOS_OSCURO if self._modo_oscuro else HOJA_ESTILOS_CLARO
        )

        contenedor = QWidget()
        self.setCentralWidget(contenedor)
        layout_raiz = QHBoxLayout(contenedor)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        self.sidebar = self._crear_sidebar()
        layout_raiz.addWidget(self.sidebar)

        columna_derecha = QVBoxLayout()
        columna_derecha.setContentsMargins(0, 0, 0, 0)
        columna_derecha.setSpacing(0)
        columna_derecha.addWidget(self._crear_topbar())

        self.paginas = QStackedWidget()
        columna_derecha.addWidget(self.paginas)

        panel_derecho = QWidget()
        panel_derecho.setLayout(columna_derecha)
        layout_raiz.addWidget(panel_derecho, stretch=1)

        self.dashboard_page = DashboardPage(self.cliente, self.catalogos)
        self.historial_page = HistorialPage(self.cliente, self.catalogos)
        self.alertas_page = AlertasPage(self.cliente, self.catalogos)
        self.incidentes_page = IncidentesPage(self.cliente, self.catalogos)
        self.reportes_page = ReportesPage(self.cliente, self.catalogos)

        for pagina in (
            self.dashboard_page,
            self.historial_page,
            self.alertas_page,
            self.incidentes_page,
            self.reportes_page,
        ):
            self.paginas.addWidget(pagina)

        self.paginas.currentChanged.connect(self._al_cambiar_pagina)

        if self._modo_oscuro:
            self.dashboard_page.aplicar_tema(True)

        self._cargar_catalogos()

        # El estado del backend se calculaba UNA sola vez al arrancar y se
        # quedaba pegado ahi para siempre (si el backend se caia despues,
        # el badge seguia diciendo "conectado"). Con este timer se vuelve
        # a chequear /health periodicamente durante toda la sesion.
        self._timer_conexion = QTimer(self)
        self._timer_conexion.timeout.connect(self._verificar_conexion)
        self._timer_conexion.start(INTERVALO_REFRESCO_MS)

    def _crear_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        titulo = QLabel("MONÓMEROS")
        titulo.setObjectName("SidebarTitle")
        subtitulo = QLabel("Monitoreo Ambiental")
        subtitulo.setObjectName("SidebarSubtitle")
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)

        self._botones_nav: list[QPushButton] = []
        opciones = [
            ("Panel Principal", 0),
            ("Historial de Mediciones", 1),
            ("Alertas", 2),
            ("Incidentes Ambientales", 3),
            ("Reportes PDF", 4),
        ]
        for texto, indice in opciones:
            boton = QPushButton(texto)
            boton.setCheckable(True)
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(lambda _=False, i=indice: self._navegar(i))
            layout.addWidget(boton)
            self._botones_nav.append(boton)

        self._botones_nav[0].setChecked(True)
        layout.addStretch()
        return sidebar

    def _crear_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(52)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(20, 0, 20, 0)

        self.boton_menu = QPushButton("☰")
        self.boton_menu.setObjectName("ToggleTema")
        self.boton_menu.setCursor(Qt.PointingHandCursor)
        self.boton_menu.setFixedWidth(38)
        self.boton_menu.setToolTip("Mostrar/ocultar el menú")
        self.boton_menu.clicked.connect(self._alternar_sidebar)
        layout.addWidget(self.boton_menu)

        self.label_estado_backend = QLabel()
        self.label_estado_backend.setObjectName("BadgeEstado")
        layout.addWidget(self.label_estado_backend)
        layout.addStretch()

        self.boton_tema = QPushButton()
        self.boton_tema.setObjectName("ToggleTema")
        self.boton_tema.setCursor(Qt.PointingHandCursor)
        self.boton_tema.clicked.connect(self._alternar_tema)
        layout.addWidget(self.boton_tema)

        self._actualizar_boton_tema()
        self._actualizar_estado_backend("verificando")
        return topbar

    def _alternar_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _actualizar_boton_tema(self):
        self.boton_tema.setText("☀️  Modo claro" if self._modo_oscuro else "🌙  Modo oscuro")

    def _alternar_tema(self):
        self._modo_oscuro = not self._modo_oscuro
        self._config.setValue("modo_oscuro", self._modo_oscuro)

        QApplication.instance().setStyleSheet(
            HOJA_ESTILOS_OSCURO if self._modo_oscuro else HOJA_ESTILOS_CLARO
        )
        self._actualizar_boton_tema()
        self._actualizar_estado_backend(self._estado_conexion)

        self.dashboard_page.aplicar_tema(self._modo_oscuro)
        self.alertas_page.aplicar_tema(self._modo_oscuro)
        self.incidentes_page.aplicar_tema(self._modo_oscuro)

    def _actualizar_estado_backend(self, estado: str, detalle: str = ""):
        """Muestra una insignia compacta ('Backend conectado/sin conexión')
        en vez de la URL cruda; el detalle tecnico queda solo en el tooltip."""
        self._estado_conexion = estado
        self.label_estado_backend.setText(TEXTO_ESTADO.get(estado, estado))
        self.label_estado_backend.setToolTip(detalle or self.cliente.base_url)
        color_texto, color_fondo = estilo_badge_estado(estado, self._modo_oscuro)
        self.label_estado_backend.setStyleSheet(
            f"color: {color_texto}; background-color: {color_fondo}; "
            "border-radius: 12px; padding: 5px 14px; font-weight: 600; font-size: 9pt;"
        )

    def _navegar(self, indice: int):
        for i, boton in enumerate(self._botones_nav):
            boton.setChecked(i == indice)
        self.paginas.setCurrentIndex(indice)

    def _al_cambiar_pagina(self, indice: int):
        pagina = self.paginas.widget(indice)
        if hasattr(pagina, "al_mostrar"):
            pagina.al_mostrar()

    def _cargar_catalogos(self):
        lanzar_worker(self._workers, self._obtener_catalogos, self._on_catalogos_listos, self._on_error_conexion)

    def _obtener_catalogos(self):
        self.cliente.salud()
        return {
            "areas": self.cliente.listar_areas(),
            "parametros": self.cliente.listar_parametros(),
            "usuarios": self.cliente.listar_usuarios(),
        }

    def _on_catalogos_listos(self, resultado: dict):
        self.catalogos.cargar(
            areas=resultado["areas"],
            parametros=resultado["parametros"],
            usuarios=resultado["usuarios"],
        )
        self._actualizar_estado_backend("ok", detalle=f"Conectado a {self.cliente.base_url}")
        self._al_cambiar_pagina(self.paginas.currentIndex())

    def _on_error_conexion(self, mensaje: str):
        self._actualizar_estado_backend("error", detalle=mensaje)

    def _verificar_conexion(self):
        """Vuelve a chequear /health cada INTERVALO_REFRESCO_MS mientras la
        app esta abierta, para que el badge de arriba refleje el estado
        real del backend en todo momento (no solo el de cuando arranco la
        app)."""
        lanzar_worker(self._workers, self.cliente.salud, self._on_conexion_ok, self._on_error_conexion)

    def _on_conexion_ok(self, _resultado: dict):
        recuperandose = self._estado_conexion == "error"
        self._actualizar_estado_backend("ok", detalle=f"Conectado a {self.cliente.base_url}")
        if recuperandose and not self.catalogos.areas:
            # Si se habia caido antes de terminar de cargar los catalogos,
            # los reintenta ahora que la conexion volvio.
            self._cargar_catalogos()

    def closeEvent(self, event):  # noqa: N802 - nombre requerido por Qt
        """Frena el auto-refresco y espera a que los hilos de red en curso
        terminen antes de cerrar, para evitar destruir un QThread activo."""
        self._timer_conexion.stop()
        self.dashboard_page.detener()
        ApiWorker.esperar_todos()
        super().closeEvent(event)

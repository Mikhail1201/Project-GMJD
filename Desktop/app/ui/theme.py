PALETA_CLARA = {
    "fondo_app": "#F4F6FA",
    "fondo_superficie": "#FFFFFF",
    "borde": "#E3E8F2",
    "texto_primario": "#1B2430",
    "texto_secundario": "#6B7385",
    "primario": "#0B3D91",
    "primario_hover": "#123E9C",
    "primario_texto": "#FFFFFF",
    "fila_alterna": "#EEF2FA",
    "sidebar_fondo": "#0B3D91",
    "sidebar_texto": "#E8ECFB",
    "sidebar_texto_secundario": "#B9C6EE",
    "sidebar_hover": "#123E9C",
    "sidebar_activo": "#1550C9",
    "sidebar_acento": "#7FB2FF",
    "topbar_fondo": "#FFFFFF",
    "topbar_borde": "#DDE3EE",
    "input_fondo": "#FFFFFF",
    "input_borde": "#D6DCE8",
    "seleccion_fondo": "#D8E4FF",
    "seleccion_texto": "#0B3D91",
    "gauge_pista": "#E3E8F2",
    "gauge_seguro": "#2E7D32",
    "gauge_alerta": "#C62828",
    "gauge_texto": "#1B2430",
    "gauge_titulo": "#0B3D91",
    "gauge_texto_secundario": "#6B7385",
}

PALETA_OSCURA = {
    "fondo_app": "#0F1420",
    "fondo_superficie": "#1A2233",
    "borde": "#2B3448",
    "texto_primario": "#E8ECF5",
    "texto_secundario": "#9AA4BD",
    "primario": "#4C8DFF",
    "primario_hover": "#6BA0FF",
    "primario_texto": "#0B1220",
    "fila_alterna": "#212B3E",
    "sidebar_fondo": "#0A0F1C",
    "sidebar_texto": "#D7DEF2",
    "sidebar_texto_secundario": "#8792AE",
    "sidebar_hover": "#16233F",
    "sidebar_activo": "#1E3A6B",
    "sidebar_acento": "#4C8DFF",
    "topbar_fondo": "#161D2C",
    "topbar_borde": "#2B3448",
    "input_fondo": "#1A2233",
    "input_borde": "#2B3448",
    "seleccion_fondo": "#26365A",
    "seleccion_texto": "#BFD4FF",
    "gauge_pista": "#2B3448",
    "gauge_seguro": "#4CAF50",
    "gauge_alerta": "#EF5350",
    "gauge_texto": "#E8ECF5",
    "gauge_titulo": "#7FB2FF",
    "gauge_texto_secundario": "#9AA4BD",
}


def generar_hoja_estilos(p: dict) -> str:
    """Construye el QSS de toda la app a partir de una paleta de colores
    (PALETA_CLARA o PALETA_OSCURA), para poder alternar tema en caliente."""
    return f"""
QWidget {{
    background-color: {p['fondo_app']};
    color: {p['texto_primario']};
    font-family: 'Segoe UI', sans-serif;
    font-size: 10pt;
}}

QMainWindow {{
    background-color: {p['fondo_app']};
}}

#Sidebar {{
    background-color: {p['sidebar_fondo']};
}}

#Sidebar QPushButton {{
    color: {p['sidebar_texto']};
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 12px 18px;
    font-size: 11pt;
    border-radius: 0px;
}}

#Sidebar QPushButton:hover {{
    background-color: {p['sidebar_hover']};
}}

#Sidebar QPushButton:checked {{
    background-color: {p['sidebar_activo']};
    font-weight: 600;
    border-left: 4px solid {p['sidebar_acento']};
}}

#SidebarTitle {{
    background-color: transparent;
    color: {p['sidebar_texto']};
    font-size: 14pt;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 20px 18px 4px 18px;
}}

#SidebarSubtitle {{
    background-color: transparent;
    color: {p['sidebar_texto_secundario']};
    font-size: 8pt;
    padding: 0px 18px 18px 18px;
}}

#TopBar {{
    background-color: {p['topbar_fondo']};
    border-bottom: 1px solid {p['topbar_borde']};
}}

#PageTitle {{
    font-size: 15pt;
    font-weight: 700;
    color: {p['primario']};
}}

QLabel#TextoSecundario {{
    color: {p['texto_secundario']};
    font-size: 9pt;
}}

QLabel#Subtitulo {{
    font-weight: 600;
    color: {p['texto_primario']};
    margin-top: 8px;
}}

QFrame#Card {{
    background-color: {p['fondo_superficie']};
    border-radius: 10px;
    border: 1px solid {p['borde']};
}}

QTableWidget {{
    background-color: {p['fondo_superficie']};
    border: 1px solid {p['borde']};
    border-radius: 8px;
    gridline-color: {p['borde']};
    selection-background-color: {p['seleccion_fondo']};
    selection-color: {p['seleccion_texto']};
}}

QTableWidget::item {{
    padding: 4px;
}}

QHeaderView::section {{
    background-color: {p['primario']};
    color: {p['primario_texto']};
    padding: 8px;
    border: none;
    font-weight: 600;
}}

QPushButton#Primario {{
    background-color: {p['primario']};
    color: {p['primario_texto']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton#Primario:hover {{
    background-color: {p['primario_hover']};
}}

QPushButton#Secundario {{
    background-color: {p['fondo_superficie']};
    color: {p['primario']};
    border: 1px solid {p['primario']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton#Secundario:hover {{
    background-color: {p['fila_alterna']};
}}

QPushButton#ToggleTema {{
    background-color: transparent;
    color: {p['texto_primario']};
    border: 1px solid {p['borde']};
    border-radius: 14px;
    padding: 5px 12px;
    font-weight: 600;
}}

QPushButton#ToggleTema:hover {{
    background-color: {p['fila_alterna']};
}}

QComboBox, QDateEdit, QLineEdit {{
    background-color: {p['input_fondo']};
    color: {p['texto_primario']};
    border: 1px solid {p['input_borde']};
    border-radius: 6px;
    padding: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {p['fondo_superficie']};
    color: {p['texto_primario']};
    selection-background-color: {p['seleccion_fondo']};
    selection-color: {p['seleccion_texto']};
}}

QCalendarWidget QWidget {{
    background-color: {p['fondo_superficie']};
    color: {p['texto_primario']};
}}

QCalendarWidget QAbstractItemView:enabled {{
    background-color: {p['fondo_superficie']};
    color: {p['texto_primario']};
    selection-background-color: {p['seleccion_fondo']};
    selection-color: {p['seleccion_texto']};
}}

QTabWidget::pane {{
    border: none;
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: {p['fondo_app']};
}}

QScrollBar::handle {{
    background: {p['borde']};
    border-radius: 4px;
}}
"""


HOJA_ESTILOS_CLARO = generar_hoja_estilos(PALETA_CLARA)
HOJA_ESTILOS_OSCURO = generar_hoja_estilos(PALETA_OSCURA)


def color_por_nivel(nivel: str) -> str:
    """Color solido de fondo para la insignia de nivel de alerta. Funciona
    igual en ambos temas porque es una insignia opaca con texto blanco."""
    return {
        "bajo": "#2E7D32",
        "medio": "#B8860B",
        "alto": "#D2691E",
        "critico": "#C62828",
    }.get((nivel or "").lower(), "#555555")


def color_por_severidad(severidad: str) -> str:
    return {
        "baja": "#2E7D32",
        "media": "#B8860B",
        "alta": "#D2691E",
        "critica": "#C62828",
    }.get((severidad or "").lower(), "#555555")


def estilo_badge_estado(estado: str, oscuro: bool = False) -> tuple[str, str]:
    """(color_texto, color_fondo) para el badge de estado del backend,
    como insignia tipo 'pill' en vez de texto suelto con la URL cruda."""
    if oscuro:
        mapa = {
            "ok": ("#8BE28F", "#1B3A20"),
            "error": ("#FF8A80", "#3A1B1B"),
            "verificando": ("#FFD180", "#3A2F14"),
        }
    else:
        mapa = {
            "ok": ("#1B5E20", "#DFF5E1"),
            "error": ("#B71C1C", "#FBE0DE"),
            "verificando": ("#8D6E00", "#FFF3CD"),
        }
    return mapa.get(estado, ("#555555", "#EEEEEE"))


def color_texto_estado(negativo: bool, oscuro: bool = False) -> str:
    """Color de texto (sin fondo propio) para estados tipo 'Pendiente'/
    'Abierto' (negativo=True) vs 'Atendida'/'Cerrado' (negativo=False).
    Se aclara en modo oscuro para mantener buen contraste."""
    if oscuro:
        return "#EF5350" if negativo else "#66BB6A"
    return "#C62828" if negativo else "#2E7D32"

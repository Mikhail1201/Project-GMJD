from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

RANGO_NIVEL = {"bajo": 0, "medio": 1, "alto": 2, "critico": 3}
RANGO_SEVERIDAD = {"baja": 0, "media": 1, "alta": 2, "critica": 3}


class ItemOrdenable(QTableWidgetItem):
    """QTableWidgetItem que al hacer click en el encabezado ordena por un
    valor "crudo" (numero, fecha, o un ranking como bajo/medio/alto) en
    vez del texto que se muestra. Sin esto, activar sorting en la tabla
    ordenaria "100.5000 ppm" antes que "44.5000 ppm" (alfabetico) o
    "05/08/2026" antes que "12/01/2026" (alfabetico en vez de cronologico)."""

    def __init__(self, texto: str, valor_orden=None):
        super().__init__(texto)
        self.valor_orden = texto if valor_orden is None else valor_orden

    def __lt__(self, otro):  # noqa: N802 - dunder, no override de Qt
        if isinstance(otro, ItemOrdenable) and self.valor_orden is not None and otro.valor_orden is not None:
            try:
                return self.valor_orden < otro.valor_orden
            except TypeError:
                pass
        return super().__lt__(otro)


def ajustar_columnas(tabla: QTableWidget, modos: list, ancho_minimo: int = 90):
    """Aplica un modo de ajuste por columna (en vez de Stretch parejo para
    todas), para que las columnas de texto largo (Área, Parámetro,
    Descripción...) se estiren y las cortas (Fecha/Hora, Valor, Nivel...)
    ocupen solo el ancho que necesitan.

    Tambien fuerza el ajuste de linea real: por defecto Qt combina
    wordWrap con ElideRight, asi que si una columna Stretch queda muy
    angosta (por ejemplo compartiendo la pantalla con otro panel) el texto
    se corta con '...' aunque el wrap este activo. Con ElideNone + un
    ancho minimo por columna, el texto siempre se ve completo, envuelto en
    varias lineas si hace falta, en vez de truncado.

    Deja la tabla con sorting habilitado (clic en un encabezado ordena por
    esa columna) — quien puebla la tabla debe desactivarlo antes de llenar
    filas y reactivarlo despues (ver deshabilitar_orden/habilitar_orden),
    porque si no Qt reordena en cada setItem() individual."""
    encabezado = tabla.horizontalHeader()
    for columna, modo in enumerate(modos):
        encabezado.setSectionResizeMode(columna, modo)
    encabezado.setMinimumSectionSize(ancho_minimo)
    encabezado.setSectionsClickable(True)
    tabla.setWordWrap(True)
    tabla.setTextElideMode(Qt.ElideNone)
    tabla.setSortingEnabled(True)


def deshabilitar_orden(tabla: QTableWidget):
    """Apagar sorting antes de poblar filas con setItem() en un loop;
    si no, Qt reordena despues de CADA fila y el resultado queda revuelto
    y es mucho mas lento."""
    tabla.setSortingEnabled(False)


def habilitar_orden(tabla: QTableWidget):
    """Reactivar sorting despues de terminar de poblar la tabla."""
    tabla.setSortingEnabled(True)


def redimensionar_filas(tabla: QTableWidget):
    """Recalcula el alto de cada fila segun su contenido (necesario tras
    poblar la tabla para que el texto envuelto no se vea cortado).

    Cuando una celda envuelve en 3 o mas lineas, una sola pasada calcula el
    alto con un ancho de columna que todavia no termino de asentarse (por
    ejemplo calcula 2 lineas cuando en realidad hacen falta 3). Verificado
    que necesita una vuelta real del event loop entre pasadas para
    converger (llamarlo dos veces seguidas sin ceder el loop no alcanza),
    por eso la segunda pasada va en un QTimer.singleShot(0, ...)."""
    tabla.resizeRowsToContents()
    QTimer.singleShot(0, tabla.resizeRowsToContents)

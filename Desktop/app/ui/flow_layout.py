from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy


class FlowLayout(QLayout):
    """Layout que acomoda sus widgets en fila y, cuando ya no caben en el
    ancho disponible, los pasa a la siguiente linea (como el 'flex-wrap'
    de CSS). Se usa en las barras de filtros (combos, fechas, botones) para
    que sean responsive: en vez de recortarse o salirse de la ventana al
    achicarla, se reordenan en varias filas.

    Adaptado del ejemplo oficial 'Flow Layout' de Qt."""

    def __init__(self, parent=None, margin: int = 0, spacing_h: int = 8, spacing_v: int = 8):
        super().__init__(parent)
        self._items: list = []
        self._spacing_h = spacing_h
        self._spacing_v = spacing_v
        self.setContentsMargins(QMargins(margin, margin, margin, margin))

    def addItem(self, item):  # noqa: N802 - override requerido por Qt
        self._items.append(item)

    def count(self):  # noqa: N802
        return len(self._items)

    def itemAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):  # noqa: N802
        return True

    def heightForWidth(self, width):  # noqa: N802
        return self._hacer_layout(QRect(0, 0, width, 0), probar=True)

    def setGeometry(self, rect):  # noqa: N802
        super().setGeometry(rect)
        self._hacer_layout(rect, probar=False)

    def sizeHint(self):  # noqa: N802
        return self.minimumSize()

    def minimumSize(self):  # noqa: N802
        tamano = QSize()
        for item in self._items:
            tamano = tamano.expandedTo(item.minimumSize())
        margenes = self.contentsMargins()
        tamano += QSize(
            margenes.left() + margenes.right(), margenes.top() + margenes.bottom()
        )
        return tamano

    def _hacer_layout(self, rect: QRect, probar: bool) -> int:
        izquierda, arriba, derecha, abajo = self.getContentsMargins()
        area_util = QRect(rect.x() + izquierda, rect.y() + arriba, rect.width() - izquierda - derecha, rect.height())
        x = area_util.x()
        y = area_util.y()
        altura_linea = 0

        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue

            siguiente_x = x + item.sizeHint().width() + self._spacing_h
            if siguiente_x - self._spacing_h > area_util.right() and altura_linea > 0:
                x = area_util.x()
                y += altura_linea + self._spacing_v
                siguiente_x = x + item.sizeHint().width() + self._spacing_h
                altura_linea = 0

            if not probar:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = siguiente_x
            altura_linea = max(altura_linea, item.sizeHint().height())

        return y + altura_linea - rect.y() + abajo

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from app.ui.theme import PALETA_CLARA

COLOR_PANTALLA_FONDO = QColor("#12181F")
COLOR_DIGITOS_OK = QColor("#4CE0B3")
COLOR_DIGITOS_ALERTA = QColor("#FF5C5C")


def _crear_fuente(tamano: int, negrita: bool = False, familia: str = "Segoe UI") -> QFont:
    """Construye la fuente con setPointSize() por separado (nunca via el
    constructor de 3 argumentos), evitando el warning de Qt
    'Point size <= 0 (-1)' que dispara QFont(family, size, peso) en
    algunas configuraciones de Windows/DPI."""
    fuente = QFont(familia)
    if tamano > 0:
        fuente.setPointSize(tamano)
    fuente.setBold(negrita)
    return fuente


class GaugeWidget(QWidget):
    """Medidor circular tipo instrumento (velocimetro/tablero de auto):
    disco con relieve, marcas de escala alrededor del arco, aguja afilada
    con cubo brillante, y una pantalla tipo LCD para el valor. Muestra el
    ultimo valor de un parametro ambiental con una franja verde para el
    rango seguro y color rojo cuando el valor sale de ese rango. Los
    colores de fondo vienen de una paleta (clara u oscura) para soportar
    cambio de tema en caliente via aplicar_paleta(); la pantalla LCD se
    mantiene siempre oscura (como un display real) independientemente del
    tema de la app."""

    def __init__(self, titulo: str, unidad: str = "", parent=None):
        super().__init__(parent)
        self.titulo = titulo
        self.unidad = unidad
        self.valor: float | None = None
        self.valor_min = 0.0
        self.valor_max = 100.0
        self.limite_minimo: float | None = None
        self.limite_maximo: float | None = None
        self._paleta = PALETA_CLARA

        self._fuente_titulo = _crear_fuente(8, negrita=True)
        self._fuente_valor = _crear_fuente(10, negrita=True, familia="Consolas")
        self._fuente_estado = _crear_fuente(7, negrita=True)

        self.setFixedSize(150, 176)

    def aplicar_paleta(self, paleta: dict):
        self._paleta = paleta
        self.update()

    def actualizar(self, valor: float, limite_minimo: float | None, limite_maximo: float | None):
        self.valor = float(valor)
        self.limite_minimo = float(limite_minimo) if limite_minimo is not None else None
        self.limite_maximo = float(limite_maximo) if limite_maximo is not None else None

        lim_min = self.limite_minimo if self.limite_minimo is not None else 0.0
        lim_max = self.limite_maximo if self.limite_maximo is not None else max(self.valor, 1.0)
        rango = max(lim_max - lim_min, 1e-6)
        self.valor_min = lim_min - rango * 0.15
        self.valor_max = lim_max + rango * 0.25
        self.update()

    def _en_rango_seguro(self) -> bool:
        if self.valor is None or self.limite_minimo is None or self.limite_maximo is None:
            return True
        return self.limite_minimo <= self.valor <= self.limite_maximo

    def _fraccion(self, valor: float) -> float:
        total = self.valor_max - self.valor_min
        if total <= 0:
            return 0.0
        return min(max((valor - self.valor_min) / total, 0.0), 1.0)

    def paintEvent(self, event):  # noqa: N802 - nombre requerido por Qt
        p = self._paleta
        color_pista = QColor(p["gauge_pista"])
        color_seguro = QColor(p["gauge_seguro"])
        color_alerta = QColor(p["gauge_alerta"])
        color_titulo = QColor(p["gauge_titulo"])
        color_secundario = QColor(p["gauge_texto_secundario"])
        color_borde = QColor(p["borde"])
        color_superficie = QColor(p["fondo_superficie"])

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        ancho = self.width()
        margen = 1
        # El disco de fondo dibuja un poco MAS ALLA de "rect" (le suma
        # `margen` alrededor), asi que el punto de partida vertical del
        # disco es (offset_superior - margen); tiene que quedar por debajo
        # del titulo (0-16) o se monta encima. offset_superior=28 deja un
        # margen de sobra (28-10=18, vs el titulo que termina en 16).
        offset_superior = 28
        # max(..., 36) evita un rect de tamano negativo si Qt llama a
        # paintEvent con una altura transitoria muy chica durante el layout.
        lado = max(min(ancho, self.height() - (offset_superior + 43)), 36)
        rect = QRectF(
            (ancho - lado) / 2 + margen, offset_superior, lado - 2 * margen, lado - 2 * margen
        )
        centro = rect.center()
        radio_ext = rect.width() / 2

        # Titulo del parametro
        painter.setPen(color_titulo)
        painter.setFont(self._fuente_titulo)
        painter.drawText(QRectF(0, 0, ancho, 16), Qt.AlignHCenter, self.titulo)

        # --- Disco de fondo (bisel) con relieve: un gradiente radial le da
        # sensacion de "hueco" tipo velocimetro real, en vez de un fondo
        # plano. Es un semicirculo (no un circulo completo) para que no se
        # monte sobre la pantalla LCD de abajo.
        disco_rect = QRectF(
            rect.left() - margen, rect.top() - margen,
            rect.width() + 2 * margen, rect.height() + 2 * margen,
        )
        gradiente_disco = QRadialGradient(centro, radio_ext + margen)
        gradiente_disco.setColorAt(0.0, color_superficie.lighter(106))
        gradiente_disco.setColorAt(0.75, color_superficie)
        gradiente_disco.setColorAt(1.0, color_superficie.darker(112))
        camino_disco = QPainterPath()
        camino_disco.moveTo(centro)
        camino_disco.arcTo(disco_rect, 0, 180)
        camino_disco.closeSubpath()
        painter.setPen(QPen(color_borde, 1))
        painter.setBrush(gradiente_disco)
        painter.drawPath(camino_disco)

        # --- Marcas de escala alrededor del arco (como un tablero real)
        painter.setPen(QPen(color_secundario, 1.3))
        radio_marca = radio_ext + 2
        for i in range(11):
            fraccion_marca = i / 10
            angulo = math.radians(180 - fraccion_marca * 180)
            largo = 7 if i % 5 == 0 else 4
            cos_a, sin_a = math.cos(angulo), math.sin(angulo)
            p1 = QPointF(centro.x() + radio_marca * cos_a, centro.y() - radio_marca * sin_a)
            p2 = QPointF(
                centro.x() + (radio_marca - largo) * cos_a,
                centro.y() - (radio_marca - largo) * sin_a,
            )
            painter.drawLine(p1, p2)

        # --- Pista de fondo (semicirculo superior, 180°)
        painter.setPen(QPen(color_pista, 7, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0 * 16, 180 * 16)

        # --- Franja verde = rango seguro (limite_minimo a limite_maximo)
        if self.limite_minimo is not None and self.limite_maximo is not None:
            f_ini = self._fraccion(self.limite_minimo)
            f_fin = self._fraccion(self.limite_maximo)
            inicio_angulo = 180 - f_ini * 180
            span = -(f_fin - f_ini) * 180
            painter.setPen(QPen(color_seguro, 7, Qt.SolidLine, Qt.FlatCap))
            painter.drawArc(rect, int(inicio_angulo * 16), int(span * 16))

        # --- Aguja tipo puntero (triangulo afilado) con cubo brillante,
        # mas corta que el radio del arco para que no se solape con el
        # anillo de color.
        color_aguja = color_seguro if self._en_rango_seguro() else color_alerta
        if self.valor is not None:
            fraccion = self._fraccion(self.valor)
            angulo = math.radians(180 - fraccion * 180)
            radio_aguja = radio_ext * 0.6
            ancho_base = 4.0
            angulo_perp = angulo + math.pi / 2
            dx = math.cos(angulo_perp) * ancho_base
            dy = -math.sin(angulo_perp) * ancho_base
            punta = QPointF(
                centro.x() + radio_aguja * math.cos(angulo),
                centro.y() - radio_aguja * math.sin(angulo),
            )
            base1 = QPointF(centro.x() + dx * 0.4, centro.y() + dy * 0.4)
            base2 = QPointF(centro.x() - dx * 0.4, centro.y() - dy * 0.4)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color_aguja)
            painter.drawPolygon(QPolygonF([base1, punta, base2]))

            gradiente_cubo = QRadialGradient(centro.x() - 1.5, centro.y() - 1.5, 7)
            gradiente_cubo.setColorAt(0.0, QColor("white"))
            gradiente_cubo.setColorAt(0.35, color_aguja.lighter(150))
            gradiente_cubo.setColorAt(1.0, color_aguja.darker(120))
            painter.setPen(QPen(color_aguja.darker(150), 1))
            painter.setBrush(gradiente_cubo)
            painter.drawEllipse(centro, 5, 5)

        # --- Pantalla tipo LCD con el valor (fondo oscuro fijo, como un
        # display real, independiente del tema claro/oscuro de la app)
        ancho_pantalla = min(108, ancho - 12)
        alto_pantalla = 21
        pantalla_rect = QRectF(
            (ancho - ancho_pantalla) / 2, rect.bottom() + 5, ancho_pantalla, alto_pantalla
        )
        painter.setPen(QPen(QColor("black"), 1))
        painter.setBrush(COLOR_PANTALLA_FONDO)
        painter.drawRoundedRect(pantalla_rect, 5, 5)

        texto_valor = f"{self.valor:.1f} {self.unidad}" if self.valor is not None else "-- --"
        color_digitos = COLOR_DIGITOS_OK if self._en_rango_seguro() else COLOR_DIGITOS_ALERTA
        painter.setPen(color_digitos)
        painter.setFont(self._fuente_valor)
        painter.drawText(pantalla_rect, Qt.AlignCenter, texto_valor)

        # --- Insignia de estado (OK / fuera de rango)
        estado_ok = self._en_rango_seguro()
        texto_estado = "OK" if estado_ok else "FUERA DE RANGO"
        painter.setPen(color_seguro if estado_ok else color_alerta)
        painter.setFont(self._fuente_estado)
        zona_estado = QRectF(0, pantalla_rect.bottom() + 2, ancho, 13)
        painter.drawText(zona_estado, Qt.AlignHCenter, texto_estado)

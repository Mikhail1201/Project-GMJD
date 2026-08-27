from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.utils import formatear_fecha_hora

COLOR_PRIMARIO = colors.HexColor("#0B3D91")
COLOR_ENCABEZADO = colors.HexColor("#0B3D91")
COLOR_FILA_ALTERNA = colors.HexColor("#EEF2FA")


class GeneradorReportePDF:
    """Genera reportes en PDF con las mediciones y alertas del sistema de monitoreo."""

    def __init__(self):
        estilos = getSampleStyleSheet()
        self.estilo_titulo = ParagraphStyle(
            "TituloReporte", parent=estilos["Title"], textColor=COLOR_PRIMARIO
        )
        self.estilo_subtitulo = ParagraphStyle(
            "Subtitulo", parent=estilos["Normal"], fontSize=10, textColor=colors.grey
        )
        self.estilo_seccion = ParagraphStyle(
            "Seccion", parent=estilos["Heading2"], textColor=COLOR_PRIMARIO, spaceBefore=14
        )
        self.estilo_normal = estilos["Normal"]
        self.estilo_celda = ParagraphStyle(
            "Celda", parent=estilos["Normal"], fontSize=8, leading=10
        )
        self.estilo_encabezado_celda = ParagraphStyle(
            "EncabezadoCelda",
            parent=estilos["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        )

    def generar(
        self,
        ruta_salida: str,
        mediciones: list[dict] | None = None,
        alertas: list[dict] | None = None,
        filtros_aplicados: dict | None = None,
    ) -> str:
        doc = SimpleDocTemplate(
            ruta_salida,
            pagesize=letter,
            topMargin=1.5 * cm,
            bottomMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            rightMargin=1.5 * cm,
        )
        elementos = []

        elementos.append(Paragraph("Reporte de Monitoreo Ambiental", self.estilo_titulo))
        elementos.append(Paragraph("Monomeros S.A. - Planta de Barranquilla", self.estilo_subtitulo))
        elementos.append(
            Paragraph(
                f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                self.estilo_subtitulo,
            )
        )

        if filtros_aplicados:
            texto_filtros = " | ".join(
                f"{clave}: {valor}" for clave, valor in filtros_aplicados.items() if valor
            )
            if texto_filtros:
                elementos.append(Spacer(1, 6))
                elementos.append(Paragraph(f"Filtros aplicados: {texto_filtros}", self.estilo_subtitulo))

        elementos.append(Spacer(1, 12))

        if mediciones is not None:
            elementos.append(Paragraph(f"Mediciones ({len(mediciones)})", self.estilo_seccion))
            elementos.append(self._tabla_mediciones(mediciones))

        if alertas is not None:
            elementos.append(PageBreak() if mediciones else Spacer(1, 12))
            elementos.append(Paragraph(f"Alertas ({len(alertas)})", self.estilo_seccion))
            elementos.append(self._tabla_alertas(alertas))

        doc.build(elementos, onFirstPage=self._pie_pagina, onLaterPages=self._pie_pagina)
        return ruta_salida

    def _tabla_mediciones(self, mediciones: list[dict]) -> Table:
        encabezado = ["Fecha/Hora", "Área", "Parámetro", "Valor", "Calidad"]
        filas = [self._fila_encabezado(encabezado)]
        for m in mediciones:
            filas.append(self._fila_celdas([
                formatear_fecha_hora(m.get("fecha_hora")),
                str(m.get("nombre_area") or m.get("id_area", "")),
                str(m.get("nombre_parametro") or m.get("id_parametro", "")),
                str(m.get("valor", "")),
                str(m.get("calidad_dato", "")),
            ]))
        return self._construir_tabla(filas, anchos=[3.0 * cm, 4.8 * cm, 5.0 * cm, 2.3 * cm, 2.3 * cm])

    def _tabla_alertas(self, alertas: list[dict]) -> Table:
        encabezado = ["Fecha/Hora", "Área", "Tipo", "Nivel", "Atendida por"]
        filas = [self._fila_encabezado(encabezado)]
        for a in alertas:
            atendida = a.get("nombre_atendio") or "Sin atender"
            filas.append(self._fila_celdas([
                formatear_fecha_hora(a.get("fecha_hora")),
                str(a.get("nombre_area", "")),
                str(a.get("tipo_alerta", "")),
                str(a.get("nivel", "")).upper(),
                atendida,
            ]))
        tabla = self._construir_tabla(filas, anchos=[3.0 * cm, 3.8 * cm, 5.8 * cm, 2.0 * cm, 3.0 * cm])
        self._resaltar_niveles(tabla, alertas)
        return tabla

    def _fila_encabezado(self, textos: list[str]) -> list[Paragraph]:
        return [Paragraph(escape(t), self.estilo_encabezado_celda) for t in textos]

    def _fila_celdas(self, textos: list[str]) -> list[Paragraph]:
        return [Paragraph(escape(t), self.estilo_celda) for t in textos]

    def _construir_tabla(self, filas: list[list], anchos: list[float]) -> Table:
        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        estilo = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ENCABEZADO),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_FILA_ALTERNA]),
        ])
        tabla.setStyle(estilo)
        return tabla

    def _resaltar_niveles(self, tabla: Table, alertas: list[dict]):
        colores_nivel = {
            "bajo": colors.HexColor("#DFF5E1"),
            "medio": colors.HexColor("#FFF3CD"),
            "alto": colors.HexColor("#FFE0B2"),
            "critico": colors.HexColor("#F8D7DA"),
        }
        estilos_extra = []
        for i, alerta in enumerate(alertas, start=1):
            color = colores_nivel.get(str(alerta.get("nivel", "")).lower())
            if color:
                estilos_extra.append(("BACKGROUND", (3, i), (3, i), color))
        if estilos_extra:
            tabla.setStyle(TableStyle(estilos_extra))

    @staticmethod
    def _pie_pagina(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(
            doc.pagesize[0] - 1.5 * cm, 1 * cm, f"Página {doc.page}"
        )
        canvas.drawString(1.5 * cm, 1 * cm, "Sistema Centralizado de Monitoreo Ambiental")
        canvas.restoreState()

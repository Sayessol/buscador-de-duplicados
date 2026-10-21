"""Utilidades compartidas para generar los PDF de documentación.

Portada + índice (tabla de contenidos con números de página reales) +
contenido con cabecera/pie y numeración. Solo reportlab.
"""

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, ListFlowable, ListItem, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

IMG = Path(__file__).resolve().parent / "img"

AZUL = colors.HexColor("#1f6aa5")
AZUL_OSC = colors.HexColor("#14375e")
GRIS = colors.HexColor("#555555")
GRIS_CLARO = colors.HexColor("#e9edf2")
VERDE = colors.HexColor("#2f8f60")
AMBAR = colors.HexColor("#a9791f")
TEXTO = colors.HexColor("#22262b")

_base = getSampleStyleSheet()

EST = {
    "titulo_portada": ParagraphStyle(
        "tp", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=30,
        leading=36, textColor=AZUL_OSC, alignment=TA_LEFT, spaceAfter=6),
    "subtitulo_portada": ParagraphStyle(
        "sp", parent=_base["Normal"], fontSize=14, leading=20, textColor=GRIS,
        alignment=TA_LEFT),
    "meta_portada": ParagraphStyle(
        "mp", parent=_base["Normal"], fontSize=10.5, leading=16, textColor=GRIS),
    "h1": ParagraphStyle(
        "H1", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=18,
        leading=23, textColor=AZUL_OSC, spaceBefore=20, spaceAfter=10,
        keepWithNext=1),
    "h2": ParagraphStyle(
        "H2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=13.5,
        leading=18, textColor=AZUL, spaceBefore=14, spaceAfter=6,
        keepWithNext=1),
    "h3": ParagraphStyle(
        "H3", parent=_base["Heading3"], fontName="Helvetica-Bold", fontSize=11.5,
        leading=15, textColor=TEXTO, spaceBefore=10, spaceAfter=4,
        keepWithNext=1),
    "cuerpo": ParagraphStyle(
        "cuerpo", parent=_base["Normal"], fontSize=10.3, leading=15.5,
        textColor=TEXTO, alignment=TA_JUSTIFY, spaceAfter=7),
    "bullet": ParagraphStyle(
        "bullet", parent=_base["Normal"], fontSize=10.3, leading=15,
        textColor=TEXTO, spaceAfter=3),
    "codigo": ParagraphStyle(
        "codigo", parent=_base["Code"], fontSize=9, leading=12.5,
        textColor=colors.HexColor("#0b3d5c"), backColor=GRIS_CLARO,
        borderPadding=6, spaceBefore=4, spaceAfter=8, leftIndent=4),
    "pre": ParagraphStyle(
        "pre", parent=_base["Code"], fontName="Courier", fontSize=8.2,
        leading=10.6, textColor=colors.HexColor("#10344a"),
        backColor=colors.HexColor("#f2f5f8"), borderColor=colors.HexColor("#d5dde5"),
        borderWidth=0.5, borderPadding=7, spaceBefore=4, spaceAfter=10),
    "nota": ParagraphStyle(
        "nota", parent=_base["Normal"], fontSize=9.7, leading=14,
        textColor=TEXTO, backColor=colors.HexColor("#eef4fb"),
        borderColor=AZUL, borderWidth=0.6, borderPadding=8,
        spaceBefore=4, spaceAfter=10),
    "pie_img": ParagraphStyle(
        "pie", parent=_base["Normal"], fontSize=8.6, leading=11,
        textColor=GRIS, alignment=TA_CENTER, spaceBefore=3, spaceAfter=12),
    "toc1": ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=11,
                           leading=18, textColor=AZUL_OSC),
    "toc2": ParagraphStyle("toc2", fontName="Helvetica", fontSize=10,
                           leading=15, leftIndent=14, textColor=TEXTO),
    "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9,
                         leading=11, textColor=colors.white),
    "td": ParagraphStyle("td", fontName="Helvetica", fontSize=9,
                         leading=12, textColor=TEXTO),
    "titulo_llano": ParagraphStyle(
        "titulo_llano", fontName="Helvetica-Bold", fontSize=18, leading=23,
        textColor=AZUL_OSC, spaceBefore=6, spaceAfter=10),
}


class _Doc(BaseDocTemplate):
    def __init__(self, ruta, titulo_corto):
        super().__init__(str(ruta), pagesize=A4,
                         leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                         topMargin=2.3 * cm, bottomMargin=2.0 * cm,
                         title=titulo_corto, author="Proyecto Buscador de duplicados")
        self._titulo_corto = titulo_corto
        ancho = self.width
        alto = self.height
        portada = PageTemplate(
            id="portada",
            frames=[Frame(self.leftMargin, self.bottomMargin, ancho, alto, id="p")],
            onPage=self._fondo_portada)
        cuerpo = PageTemplate(
            id="cuerpo",
            frames=[Frame(self.leftMargin, self.bottomMargin, ancho, alto, id="c")],
            onPage=self._cabecera_pie)
        self.addPageTemplates([portada, cuerpo])

    def _fondo_portada(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(AZUL_OSC)
        canvas.rect(0, A4[1] - 4.2 * cm, A4[0], 4.2 * cm, fill=1, stroke=0)
        canvas.setFillColor(AZUL)
        canvas.rect(0, A4[1] - 4.35 * cm, A4[0], 0.15 * cm, fill=1, stroke=0)
        canvas.setFillColor(AZUL)
        canvas.rect(0, 0, A4[0], 1.0 * cm, fill=1, stroke=0)
        canvas.restoreState()

    def _cabecera_pie(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRIS)
        canvas.drawString(self.leftMargin, A4[1] - 1.4 * cm, self._titulo_corto)
        canvas.drawRightString(A4[0] - self.rightMargin, A4[1] - 1.4 * cm,
                               "Buscador de duplicados")
        canvas.setStrokeColor(GRIS_CLARO)
        canvas.line(self.leftMargin, A4[1] - 1.6 * cm,
                    A4[0] - self.rightMargin, A4[1] - 1.6 * cm)
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"– {doc.page} –")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        estilo = flowable.style.name
        txt = flowable.getPlainText()
        if estilo == "H1":
            self.notify("TOCEntry", (0, txt, self.page))
        elif estilo == "H2":
            self.notify("TOCEntry", (1, txt, self.page))


# ---- helpers de contenido -------------------------------------------------
def h1(t):
    return Paragraph(t, EST["h1"])


def h2(t):
    return Paragraph(t, EST["h2"])


def h3(t):
    return Paragraph(t, EST["h3"])


def p(t):
    return Paragraph(t, EST["cuerpo"])


def nota(t):
    return Paragraph("<b>Nota.</b> " + t, EST["nota"])


def codigo(t):
    t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
         .replace("\n", "<br/>").replace(" ", "&nbsp;"))
    return Paragraph(t, EST["codigo"])


def pre(texto):
    """Bloque de código de varias líneas (monoespaciado, con recuadro)."""
    return Preformatted(texto.strip("\n"), EST["pre"])


def lista(items):
    return ListFlowable(
        [ListItem(Paragraph(x, EST["bullet"]), leftIndent=12,
                  value="•") for x in items],
        bulletType="bullet", start="•", leftIndent=10)


def imagen(nombre, ancho_cm=15.5, pie=None):
    ruta = IMG / nombre
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(ruta)).getSize()
    w = ancho_cm * cm
    h = w * ih / iw
    flow = [Image(str(ruta), width=w, height=h, hAlign="CENTER")]
    if pie:
        flow.append(Paragraph(pie, EST["pie_img"]))
    else:
        flow.append(Spacer(1, 8))
    return flow


def tabla(filas, anchos_cm=None):
    est = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_OSC),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXTO),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3dd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    celdas = [[Paragraph(str(c), EST["th" if i == 0 else "td"]) for c in fila]
              for i, fila in enumerate(filas)]
    kw = {}
    if anchos_cm:
        kw["colWidths"] = [a * cm for a in anchos_cm]
    t = Table(celdas, repeatRows=1, **kw)
    t.setStyle(est)
    return t


def construir(ruta_pdf, titulo, subtitulo, titulo_corto, cuerpo_flowables,
              resumen_portada=None):
    doc = _Doc(ruta_pdf, titulo_corto)
    story = []

    # --- Portada ---
    story.append(Spacer(1, 5.2 * cm))
    story.append(Paragraph(titulo, EST["titulo_portada"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(subtitulo, EST["subtitulo_portada"]))
    story.append(Spacer(1, 1.4 * cm))
    if resumen_portada:
        story.append(Paragraph(resumen_portada, EST["meta_portada"]))
        story.append(Spacer(1, 1.0 * cm))
    meta = (f"Aplicación de escritorio para Windows &nbsp;·&nbsp; "
            f"Python + CustomTkinter<br/>"
            f"Documento generado el {date.today().strftime('%d/%m/%Y')}")
    story.append(Paragraph(meta, EST["meta_portada"]))

    story.append(NextPageTemplate("cuerpo"))
    story.append(PageBreak())

    # --- Índice ---
    story.append(Paragraph("Índice", EST["titulo_llano"]))
    toc = TableOfContents()
    toc.levelStyles = [EST["toc1"], EST["toc2"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(PageBreak())

    # --- Contenido ---
    story.extend(cuerpo_flowables)

    doc.multiBuild(story)
    print("Generado:", ruta_pdf)

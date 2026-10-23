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

BLUE = colors.HexColor("#1f6aa5")
BLUE_DARK = colors.HexColor("#14375e")
GRAY = colors.HexColor("#555555")
GRAY_LIGHT = colors.HexColor("#e9edf2")
GREEN = colors.HexColor("#2f8f60")
AMBER = colors.HexColor("#a9791f")
TEXT = colors.HexColor("#22262b")

_base = getSampleStyleSheet()

STYLES = {
    "titulo_portada": ParagraphStyle(
        "tp", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=30,
        leading=36, textColor=BLUE_DARK, alignment=TA_LEFT, spaceAfter=6),
    "subtitulo_portada": ParagraphStyle(
        "sp", parent=_base["Normal"], fontSize=14, leading=20, textColor=GRAY,
        alignment=TA_LEFT),
    "meta_portada": ParagraphStyle(
        "mp", parent=_base["Normal"], fontSize=10.5, leading=16, textColor=GRAY),
    "h1": ParagraphStyle(
        "H1", parent=_base["Heading1"], fontName="Helvetica-Bold", fontSize=18,
        leading=23, textColor=BLUE_DARK, spaceBefore=20, spaceAfter=10,
        keepWithNext=1),
    "h2": ParagraphStyle(
        "H2", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=13.5,
        leading=18, textColor=BLUE, spaceBefore=14, spaceAfter=6,
        keepWithNext=1),
    "h3": ParagraphStyle(
        "H3", parent=_base["Heading3"], fontName="Helvetica-Bold", fontSize=11.5,
        leading=15, textColor=TEXT, spaceBefore=10, spaceAfter=4,
        keepWithNext=1),
    "cuerpo": ParagraphStyle(
        "cuerpo", parent=_base["Normal"], fontSize=10.3, leading=15.5,
        textColor=TEXT, alignment=TA_JUSTIFY, spaceAfter=7),
    "bullet": ParagraphStyle(
        "bullet", parent=_base["Normal"], fontSize=10.3, leading=15,
        textColor=TEXT, spaceAfter=3),
    "codigo": ParagraphStyle(
        "codigo", parent=_base["Code"], fontSize=9, leading=12.5,
        textColor=colors.HexColor("#0b3d5c"), backColor=GRAY_LIGHT,
        borderPadding=6, spaceBefore=4, spaceAfter=8, leftIndent=4),
    "pre": ParagraphStyle(
        "pre", parent=_base["Code"], fontName="Courier", fontSize=8.2,
        leading=10.6, textColor=colors.HexColor("#10344a"),
        backColor=colors.HexColor("#f2f5f8"), borderColor=colors.HexColor("#d5dde5"),
        borderWidth=0.5, borderPadding=7, spaceBefore=4, spaceAfter=10),
    "nota": ParagraphStyle(
        "nota", parent=_base["Normal"], fontSize=9.7, leading=14,
        textColor=TEXT, backColor=colors.HexColor("#eef4fb"),
        borderColor=BLUE, borderWidth=0.6, borderPadding=8,
        spaceBefore=4, spaceAfter=10),
    "pie_img": ParagraphStyle(
        "pie", parent=_base["Normal"], fontSize=8.6, leading=11,
        textColor=GRAY, alignment=TA_CENTER, spaceBefore=3, spaceAfter=12),
    "toc1": ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=11,
                           leading=18, textColor=BLUE_DARK),
    "toc2": ParagraphStyle("toc2", fontName="Helvetica", fontSize=10,
                           leading=15, leftIndent=14, textColor=TEXT),
    "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=9,
                         leading=11, textColor=colors.white),
    "td": ParagraphStyle("td", fontName="Helvetica", fontSize=9,
                         leading=12, textColor=TEXT),
    "titulo_llano": ParagraphStyle(
        "titulo_llano", fontName="Helvetica-Bold", fontSize=18, leading=23,
        textColor=BLUE_DARK, spaceBefore=6, spaceAfter=10),
}


class _Doc(BaseDocTemplate):
    def __init__(self, path, short_title):
        super().__init__(str(path), pagesize=A4,
                         leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                         topMargin=2.3 * cm, bottomMargin=2.0 * cm,
                         title=short_title, author="Proyecto Buscador de duplicados")
        self._short_title = short_title
        width = self.width
        height = self.height
        cover = PageTemplate(
            id="portada",
            frames=[Frame(self.leftMargin, self.bottomMargin, width, height, id="p")],
            onPage=self._cover_background)
        body = PageTemplate(
            id="cuerpo",
            frames=[Frame(self.leftMargin, self.bottomMargin, width, height, id="c")],
            onPage=self._header_footer)
        self.addPageTemplates([cover, body])

    def _cover_background(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BLUE_DARK)
        canvas.rect(0, A4[1] - 4.2 * cm, A4[0], 4.2 * cm, fill=1, stroke=0)
        canvas.setFillColor(BLUE)
        canvas.rect(0, A4[1] - 4.35 * cm, A4[0], 0.15 * cm, fill=1, stroke=0)
        canvas.setFillColor(BLUE)
        canvas.rect(0, 0, A4[0], 1.0 * cm, fill=1, stroke=0)
        canvas.restoreState()

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(self.leftMargin, A4[1] - 1.4 * cm, self._short_title)
        canvas.drawRightString(A4[0] - self.rightMargin, A4[1] - 1.4 * cm,
                               "Buscador de duplicados")
        canvas.setStrokeColor(GRAY_LIGHT)
        canvas.line(self.leftMargin, A4[1] - 1.6 * cm,
                    A4[0] - self.rightMargin, A4[1] - 1.6 * cm)
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"– {doc.page} –")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        style = flowable.style.name
        txt = flowable.getPlainText()
        if style == "H1":
            self.notify("TOCEntry", (0, txt, self.page))
        elif style == "H2":
            self.notify("TOCEntry", (1, txt, self.page))


# ---- helpers de contenido -------------------------------------------------
def h1(t):
    return Paragraph(t, STYLES["h1"])


def h2(t):
    return Paragraph(t, STYLES["h2"])


def h3(t):
    return Paragraph(t, STYLES["h3"])


def p(t):
    return Paragraph(t, STYLES["cuerpo"])


def note(t):
    return Paragraph("<b>Nota.</b> " + t, STYLES["nota"])


def code(t):
    t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
         .replace("\n", "<br/>").replace(" ", "&nbsp;"))
    return Paragraph(t, STYLES["codigo"])


def pre(text):
    """Bloque de código de varias líneas (monoespaciado, con recuadro)."""
    return Preformatted(text.strip("\n"), STYLES["pre"])


def bullet_list(items):
    return ListFlowable(
        [ListItem(Paragraph(x, STYLES["bullet"]), leftIndent=12,
                  value="•") for x in items],
        bulletType="bullet", start="•", leftIndent=10)


def image(name, width_cm=15.5, caption=None):
    path = IMG / name
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(path)).getSize()
    w = width_cm * cm
    h = w * ih / iw
    flow = [Image(str(path), width=w, height=h, hAlign="CENTER")]
    if caption:
        flow.append(Paragraph(caption, STYLES["pie_img"]))
    else:
        flow.append(Spacer(1, 8))
    return flow


def table(rows, widths_cm=None):
    styles = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), TEXT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRAY_LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d3dd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    cells = [[Paragraph(str(c), STYLES["th" if i == 0 else "td"]) for c in row]
              for i, row in enumerate(rows)]
    kw = {}
    if widths_cm:
        kw["colWidths"] = [a * cm for a in widths_cm]
    t = Table(cells, repeatRows=1, **kw)
    t.setStyle(styles)
    return t


def build(pdf_path, title, subtitle, short_title, body_flowables,
              cover_summary=None):
    doc = _Doc(pdf_path, short_title)
    story = []

    # --- Portada ---
    story.append(Spacer(1, 5.2 * cm))
    story.append(Paragraph(title, STYLES["titulo_portada"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(subtitle, STYLES["subtitulo_portada"]))
    story.append(Spacer(1, 1.4 * cm))
    if cover_summary:
        story.append(Paragraph(cover_summary, STYLES["meta_portada"]))
        story.append(Spacer(1, 1.0 * cm))
    meta = (f"Aplicación de escritorio para Windows &nbsp;·&nbsp; "
            f"Python + CustomTkinter<br/>"
            f"Documento generado el {date.today().strftime('%d/%m/%Y')}")
    story.append(Paragraph(meta, STYLES["meta_portada"]))

    story.append(NextPageTemplate("cuerpo"))
    story.append(PageBreak())

    # --- Índice ---
    story.append(Paragraph("Índice", STYLES["titulo_llano"]))
    toc = TableOfContents()
    toc.levelStyles = [STYLES["toc1"], STYLES["toc2"]]
    toc.dotsMinLevel = 0
    story.append(toc)
    story.append(PageBreak())

    # --- Contenido ---
    story.extend(body_flowables)

    doc.multiBuild(story)
    print("Generado:", pdf_path)

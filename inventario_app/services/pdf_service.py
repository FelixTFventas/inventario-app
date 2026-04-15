import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from .media_service import get_pdf_dir, get_upload_dir


def build_inventory_pdf(inventario, secciones, firmas) -> str:
    inmueble = inventario.inmueble
    nombre_pdf = f"inventario_{inventario.id}.pdf"
    pdf_dir = get_pdf_dir()
    upload_dir = get_upload_dir()
    ruta_pdf = pdf_dir / nombre_pdf

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "InventarioTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#153385"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "InventarioSection",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#153385"),
        spaceBefore=8,
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "InventarioMeta",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#243041"),
        spaceAfter=6,
    )
    note_style = ParagraphStyle(
        "InventarioNote",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#5b6472"),
        spaceAfter=8,
    )

    def dibujar_encabezado_y_pie(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#d7e1f5"))
        canvas.setLineWidth(1)
        canvas.line(doc.leftMargin, 752, letter[0] - doc.rightMargin, 752)

        canvas.setFillColor(colors.HexColor("#153385"))
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(doc.leftMargin, 764, "Inventario App")

        canvas.setFillColor(colors.HexColor("#5b6472"))
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            764,
            f"Inventario #{inventario.id}",
        )

        canvas.line(doc.leftMargin, 30, letter[0] - doc.rightMargin, 30)
        canvas.drawString(doc.leftMargin, 18, inmueble.empresa.nombre)
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            18,
            f"Pagina {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    elementos = [
        Paragraph("Inventario de Entrega de Inmueble", title_style),
        Paragraph("Resumen general del recorrido documentado.", note_style),
        Spacer(1, 12),
        Paragraph(f"<b>Empresa:</b> {inmueble.empresa.nombre}", meta_style),
        Paragraph(f"<b>Direccion:</b> {inmueble.direccion}", meta_style),
        Paragraph(f"<b>Fecha de recepcion:</b> {inmueble.fecha_recepcion}", meta_style),
        Paragraph(f"<b>Inventario:</b> {inventario.nombre}", meta_style),
        Paragraph(f"<b>Fecha inventario:</b> {inventario.fecha}", meta_style),
        Spacer(1, 18),
    ]

    for seccion in secciones:
        elementos.append(Paragraph(f"Seccion: {seccion.nombre}", section_style))
        elementos.append(
            Paragraph(
                f"<b>Archivos:</b> {len(seccion.fotos)} | <b>Observaciones:</b> {len(seccion.observaciones)}",
                note_style,
            )
        )

        tiene_evidencia = False
        galeria = []
        for foto in seccion.fotos:
            ruta_archivo = upload_dir / foto.archivo
            if not ruta_archivo.exists():
                continue

            tiene_evidencia = True
            ext = foto.archivo.rsplit(".", 1)[-1].lower()
            if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
                imagen = Image(str(ruta_archivo))
                imagen._restrictSize(2.6 * inch, 2.1 * inch)
                galeria.append(imagen)
            else:
                if galeria:
                    _append_gallery(elementos, galeria)
                    galeria = []
                elementos.append(
                    Paragraph(f"<b>Video adjunto:</b> {foto.archivo}", note_style)
                )

        if galeria:
            _append_gallery(elementos, galeria)
            elementos.append(Spacer(1, 4))

        if not tiene_evidencia:
            elementos.append(Paragraph("Sin evidencia multimedia cargada.", note_style))
            elementos.append(Spacer(1, 6))

        descripcion = (seccion.descripcion or "").strip()
        if descripcion:
            elementos.append(
                Paragraph(f"<b>Descripcion:</b> {descripcion}", meta_style)
            )
            elementos.append(Spacer(1, 10))

        tiene_observaciones = False
        for observacion in seccion.observaciones:
            tiene_observaciones = True
            elementos.append(
                Paragraph(f"<b>Observacion:</b> {observacion.comentario}", meta_style)
            )
            elementos.append(Spacer(1, 10))

        if not tiene_observaciones:
            elementos.append(Paragraph("Sin observaciones registradas.", note_style))

        elementos.append(Spacer(1, 20))

    if firmas:
        elementos.append(PageBreak())
        elementos.append(Paragraph("Firmas del inventario", title_style))
        elementos.append(Spacer(1, 18))

        for firma in firmas:
            elementos.append(
                Paragraph(f"<b>Firmado por:</b> {firma.nombre}", meta_style)
            )
            if firma.cedula:
                elementos.append(
                    Paragraph(f"<b>Cédula:</b> {firma.cedula}", meta_style)
                )
            if firma.celular:
                elementos.append(
                    Paragraph(f"<b>Celular:</b> {firma.celular}", meta_style)
                )
            if firma.correo:
                elementos.append(
                    Paragraph(f"<b>Correo electrónico:</b> {firma.correo}", meta_style)
                )
            elementos.append(Spacer(1, 10))

            try:
                imagen_base64 = firma.imagen.split(",", 1)[1]
                imagen_bytes = base64.b64decode(imagen_base64)
                imagen_firma = Image(BytesIO(imagen_bytes))
                imagen_firma._restrictSize(3.2 * inch, 1.6 * inch)
                elementos.append(imagen_firma)
                elementos.append(Spacer(1, 20))
            except Exception:
                elementos.append(
                    Paragraph("No se pudo renderizar una firma.", note_style)
                )
                elementos.append(Spacer(1, 20))

    pdf = SimpleDocTemplate(
        str(ruta_pdf),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=78,
        bottomMargin=46,
    )
    pdf.build(
        elementos,
        onFirstPage=dibujar_encabezado_y_pie,
        onLaterPages=dibujar_encabezado_y_pie,
    )
    return nombre_pdf


def _append_gallery(elementos, galeria) -> None:
    filas = [galeria[index : index + 2] for index in range(0, len(galeria), 2)]
    for fila in filas:
        if len(fila) == 1:
            fila.append(Spacer(1, 1))
    tabla_galeria = Table(filas, colWidths=[2.75 * inch, 2.75 * inch], hAlign="LEFT")
    tabla_galeria.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elementos.append(tabla_galeria)

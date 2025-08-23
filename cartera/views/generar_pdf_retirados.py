from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from academico.models import Alumno
from django.utils import timezone

def generar_pdf_retirados_view(request):
    # Obtener los alumnos retirados con la misma lógica de filtrado que la lista
    queryset = Alumno.objects.filter(estado='retirado', grupo_actual__codigo='RETIRADOS')
    municipio_id = request.GET.get('municipio')
    mes = request.GET.get('mes')
    anio = request.GET.get('anio')
    tipo_programa = request.GET.get('tipo_programa')

    if municipio_id:
        queryset = queryset.filter(grupo_actual__salon__sede__municipio_id=municipio_id)
    if mes and anio:
        queryset = queryset.filter(fecha_retiro__month=mes, fecha_retiro__year=anio)
    elif anio:
        queryset = queryset.filter(fecha_retiro__year=anio)
    if tipo_programa:
        queryset = queryset.filter(tipo_programa=tipo_programa)

    alumnos_retirados = queryset.select_related(
        'municipio', 'grupo_actual', 'grupo_actual__salon__sede__municipio'
    ).order_by('primer_apellido', 'segundo_apellido', 'nombres')

    # Configurar la respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    hoy = timezone.localtime(timezone.now())
    fecha_str_filename = hoy.strftime('%Y-%m-%d')
    filename = f"informe_retirados_{fecha_str_filename}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    # Crear el documento PDF
    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()

    # Fecha y Título
    fecha_str_display = hoy.strftime('%d de %B de %Y')
    elements.append(Paragraph(fecha_str_display, styles['Normal']))
    elements.append(Spacer(1, 0.2 * inch))
    elements.append(Paragraph("Listado de Alumnos Retirados", styles['h1']))

    # Datos de la tabla
    data = [[
        'Nombre Completo',
        'Teléfono',
        'Municipio',
        'Fecha Retiro',
        'Saldo Pendiente'
    ]]

    for alumno in alumnos_retirados:
        nombre_completo = f"{alumno.nombres} {alumno.primer_apellido} {alumno.segundo_apellido or ''}".strip()
        saldo_pendiente = getattr(alumno.deuda, 'saldo_pendiente', 0) if hasattr(alumno, 'deuda') and alumno.deuda else 0
        data.append([
            nombre_completo,
            alumno.celular or 'N/A',
            alumno.municipio.nombre if alumno.municipio else 'N/A',
            alumno.fecha_retiro.strftime('%Y-%m-%d') if alumno.fecha_retiro else 'N/A',
            f"${saldo_pendiente:,.0f}".replace(',', '.')
        ])

    # Estilo de la tabla
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Crear y estilizar la tabla
    table = Table(data)
    table.setStyle(style)
    elements.append(table)

    # Calcular totales
    total_retirados = alumnos_retirados.count()
    total_saldo_pendiente = sum(getattr(alumno.deuda, 'saldo_pendiente', 0) for alumno in alumnos_retirados if hasattr(alumno, 'deuda') and alumno.deuda)

    # Añadir un espacio
    elements.append(Spacer(1, 0.2 * inch))

    # Añadir totales al PDF
    styles = getSampleStyleSheet()
    total_retirados_text = f"<b>Total de alumnos retirados:</b> {total_retirados}"
    total_saldo_text = f"<b>Saldo pendiente total:</b> ${total_saldo_pendiente:,.0f}".replace(',', '.')

    elements.append(Paragraph(total_retirados_text, styles['Normal']))
    elements.append(Paragraph(total_saldo_text, styles['Normal']))

    doc.build(elements)

    return response

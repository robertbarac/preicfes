import os
from datetime import datetime
from io import BytesIO

from django.views import View
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.conf import settings
from django.utils import timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from usuarios.models import Usuario, Firma
from academico.models import Clase


class GenerarCertificadoTrabajoView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Solo superuser y SecretariaAcademica pueden generar certificados
        return (
            self.request.user.is_superuser or
            self.request.user.groups.filter(name='SecretariaAcademica').exists()
        )
    
    def get(self, request, profesor_id):
        profesor = get_object_or_404(Usuario, pk=profesor_id)
        
        # Verificar que el usuario sea profesor
        if not profesor.groups.filter(name='Profesor').exists():
            raise Http404("El usuario no es un profesor")
            
        # Obtener fechas del formulario
        fecha_inicio_str = request.GET.get('fecha_inicio')
        fecha_fin_str = request.GET.get('fecha_fin')
        
        # Si no se proporcionan fechas, redirigir al formulario
        if not fecha_inicio_str or not fecha_fin_str:
            return redirect('certificado_trabajo_form', profesor_id=profesor_id)
            
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        except ValueError:
            return redirect('certificado_trabajo_form', profesor_id=profesor_id)
        
        # Configurar respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"certificado_trabajo_{profesor.username}_{timezone.now().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        # Configurar documento
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
        styles.add(ParagraphStyle(name='SmallCenter', alignment=TA_CENTER, fontSize=8))
        
        # Modificar el estilo Title existente en lugar de crear uno nuevo
        styles['Title'].alignment = TA_CENTER
        styles['Title'].fontSize = 14
        styles['Title'].fontName = 'Helvetica-Bold'
        
        # Contenido
        elements = []
        
        # Logo (escudo)
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img/logo.png')
        if os.path.exists(logo_path):
            elements.append(Image(logo_path, width=2*inch, height=1*inch))
            elements.append(Spacer(1, 20))
        
        # Fecha actual
        fecha_actual = timezone.now().date()
        
        # Diccionario para convertir nombres de meses en inglés a español
        meses_es = {
            'January': 'enero',
            'February': 'febrero',
            'March': 'marzo',
            'April': 'abril',
            'May': 'mayo',
            'June': 'junio',
            'July': 'julio',
            'August': 'agosto',
            'September': 'septiembre',
            'October': 'octubre',
            'November': 'noviembre',
            'December': 'diciembre'
        }
        
        # Obtener el mes actual en español
        mes_actual_es = meses_es.get(fecha_actual.strftime('%B'), fecha_actual.strftime('%B'))
        
        # Encabezado
        elements.append(Paragraph('<b>EL PRE ICFES VICTOR VALDEZ</b>', styles['Title']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('<b>NIT - 9012725987</b>', styles['Title']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph('<b>CERTIFICA QUE</b>', styles['Center']))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 20))
        # Formatear fechas en español usando las fechas proporcionadas por el formulario
        mes_inicio_es = meses_es.get(fecha_inicio.strftime('%B'), fecha_inicio.strftime('%B'))
        fecha_inicio_texto = f"{fecha_inicio.day} de {mes_inicio_es} de {fecha_inicio.year}"
        
        mes_fin_es = meses_es.get(fecha_fin.strftime('%B'), fecha_fin.strftime('%B'))
        fecha_fin_texto = f"{fecha_fin.day} de {mes_fin_es} de {fecha_fin.year}"
        
        # Obtener las materias que el profesor ha enseñado
        materias_profesor = Clase.objects.filter(
            profesor=profesor,
            estado='vista'
        ).values_list('materia__nombre', flat=True).distinct()
        
        # Formatear lista de materias
        materias_texto = "NO DISPONIBLE"
        if materias_profesor:
            # Convertir a lista para poder manipularla
            materias_lista = list(materias_profesor)
            
            # Formatear las materias en formato adecuado
            if len(materias_lista) == 1:
                materias_texto = materias_lista[0].upper()
            elif len(materias_lista) == 2:
                materias_texto = f"{materias_lista[0].upper()} Y {materias_lista[1].upper()}"
            else:
                # Para tres o más materias, usar formato con comas y 'y' al final
                materias_texto = ", ".join([m.upper() for m in materias_lista[:-1]]) + f" Y {materias_lista[-1].upper()}"
        
        # Nombre completo del profesor
        nombre_completo = profesor.get_full_name()
        if not nombre_completo.strip():
            nombre_completo = profesor.username
        
        # Cuerpo del certificado - Primera parte
        texto_certificado1 = f"Que el(la) señor(a) <b>{nombre_completo}</b>, identificado(a) con {profesor.get_tipo_identificacion_display() if hasattr(profesor, 'get_tipo_identificacion_display') else 'documento de identidad'} N° <b>{profesor.cedula if hasattr(profesor, 'cedula') else 'No disponible'}</b> se encuentra prestando su servicio como docente de horas cátedras en el área de <b>{materias_texto}</b>, desde el <b>{fecha_inicio_texto}</b> hasta el <b>{fecha_fin_texto}</b>."
        # POR SI DE NECESITA EN UN FUTURO expedida en {profesor.municipio.nombre if hasattr(profesor, 'municipio') and profesor.municipio else 'Colombia'}, 
        elements.append(Paragraph(texto_certificado1, styles['Justify']))
        elements.append(Spacer(1, 20))
        
        # Cuerpo del certificado - Segunda parte
        texto_certificado2 = "Durante este tiempo, ha demostrado ser un profesional excepcional y comprometido con la institución. Su capacidad para enseñar y motivar a los estudiantes es destacable."
        
        elements.append(Paragraph(texto_certificado2, styles['Justify']))
        elements.append(Spacer(1, 40))
        
        # Texto de constancia
        elements.append(Paragraph(
            f"<para align='justify'>Para mayor constancia se firma y se sella a los ({fecha_actual.day}) días del mes de {mes_actual_es} de {fecha_actual.year}.</para>",
            styles['Justify']
        ))
        elements.append(Spacer(1, 50))
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))
        
        
        # Buscar si el usuario tiene una firma digital registrada
        try:
            # Buscar la firma del usuario actual
            coordinador = request.user
            firma = Firma.objects.get(usuario=coordinador)
            # Si tiene firma digital, agregarla al documento
            if firma.imagen and os.path.exists(firma.imagen.path):
                # Agregar la imagen de la firma
                firma_img = Image(firma.imagen.path)
                # Ajustar el tamaño de la imagen para que se vea bien en el PDF
                firma_img.drawHeight = 0.5*inch
                firma_img.drawWidth = 2*inch
                elements.append(firma_img)
                elements.append(Spacer(1, 5))
            else:
                # Si no tiene imagen de firma, mostrar la línea
                elements.append(Paragraph("___________________________________________", styles['Center']))
        except (Firma.DoesNotExist, Usuario.DoesNotExist):
            # Si no tiene firma registrada, mostrar la línea
            elements.append(Paragraph("___________________________________________", styles['Center']))
        
        

        # Datos del usuario que genera el documento
        nombre_completo_usuario = f"{request.user.first_name} {request.user.last_name}"
        if not nombre_completo_usuario.strip():
            nombre_completo_usuario = request.user.username
            
        elements.append(Paragraph(f"<b>{nombre_completo_usuario}</b>", styles['Center']))
        
        elements.append(Paragraph("<b>COORDINADOR(A) ACADÉMICO(A) PRE ICFES VICTOR VALDEZ</b>", styles['Center']))
        
        # Agregar teléfono si está disponible
        telefono = request.user.telefono if hasattr(request.user, 'telefono') and request.user.telefono else ""
        if telefono:
            elements.append(Paragraph(f"Cel: {telefono}", styles['Center']))
        elements.append(Spacer(1, 30))
        
        # Pie de página en letras pequeñas
        elements.append(Paragraph("<b>VALDEZ Y ANDRADE SOLUCIONES S.A.S</b>", styles['SmallCenter']))
        elements.append(Paragraph("<b>NIT 901.272.598 - 7</b>", styles['SmallCenter']))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("_______________________________________________________________", styles['Center']))
        elements.append(Paragraph("<b>CRA. 60A # 29 - 47 BARRIO LOS ANGELES</b>", styles['Center']))
        
        # Generar PDF
        doc.build(elements)
        return response

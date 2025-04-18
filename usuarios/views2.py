from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.urls import reverse_lazy
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

from .models import Usuario, Firma
from academico.models import Clase

class CustomLoginView(LoginView):
    template_name = 'usuarios/login.html'

    def get_success_url(self):
        if self.request.user.groups.filter(name='Profesor').exists():
            return reverse_lazy('profesor_clases', kwargs={'profesor_id': self.request.user.id})
        else:
            return reverse_lazy('alumnos_list')

class ProfesorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Usuario
    template_name = 'usuarios/profesor_list.html'
    context_object_name = 'profesores'
    login_url = 'login'
    paginate_by = 20  # Paginación de 2 elementos por página

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        grupo_profesor = Group.objects.get(name='Profesor')
        queryset = Usuario.objects.filter(groups=grupo_profesor)
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(municipio=self.request.user.municipio)
            
        return queryset.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Listado de Profesores'
        
        # Añadir información de paginación al contexto
        paginator = context['paginator']
        page_obj = context['page_obj']
        
        # Obtener el número de página actual
        page_number = page_obj.number
        
        # Calcular el rango de páginas a mostrar (para evitar mostrar demasiadas páginas)
        page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
        context['page_range'] = page_range
        
        return context

class ProfesorDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Usuario
    template_name = 'usuarios/profesor_detail.html'
    context_object_name = 'profesor'
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f'Detalles del Profesor: {self.object.get_full_name()}'
        
        # Verificar si el usuario puede generar certificados de trabajo
        puede_generar_certificado = (
            self.request.user.is_superuser or
            self.request.user.groups.filter(name='SecretariaAcademica').exists()
        )
        context['puede_generar_certificado'] = puede_generar_certificado
        
        return context


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
        
        # Obtener la primera y última clase del profesor
        primera_clase = Clase.objects.filter(
            profesor=profesor,
            estado='vista'
        ).order_by('fecha').first()
        
        ultima_clase = Clase.objects.filter(
            profesor=profesor,
            estado='vista'
        ).order_by('-fecha').first()
        
        # Formatear fechas en español
        fecha_inicio = "No disponible"
        fecha_fin = "No disponible"
        
        if primera_clase:
            mes_inicio_es = meses_es.get(primera_clase.fecha.strftime('%B'), primera_clase.fecha.strftime('%B'))
            fecha_inicio = f"{primera_clase.fecha.day} de {mes_inicio_es} de {primera_clase.fecha.year}"
        
        if ultima_clase:
            mes_fin_es = meses_es.get(ultima_clase.fecha.strftime('%B'), ultima_clase.fecha.strftime('%B'))
            fecha_fin = f"{ultima_clase.fecha.day} de {mes_fin_es} de {ultima_clase.fecha.year}"
        
        # Nombre completo del profesor
        nombre_completo = profesor.get_full_name()
        if not nombre_completo.strip():
            nombre_completo = profesor.username
        
        # Cuerpo del certificado
        texto_certificado = f"""
        <para align=justify>
        El(La) señor(a) <b>{nombre_completo}</b>, identificado(a) con {profesor.get_tipo_identificacion_display() if hasattr(profesor, 'get_tipo_identificacion_display') else 'documento de identidad'} N° <b>{profesor.cedula if hasattr(profesor, 'cedula') else 'No disponible'}</b>, 
        ha trabajado como docente en el PRE ICFES VICTOR VALDEZ desde el <b>{fecha_inicio}</b> hasta el <b>{fecha_fin}</b>, 
        desempeñándose en la enseñanza y preparación de estudiantes para las pruebas ICFES.
        </para>
        """
        
        elements.append(Paragraph(texto_certificado, styles['Justify']))
        elements.append(Spacer(1, 40))
        
        # Texto de constancia
        elements.append(Paragraph(
            f"<para align='justify'>Para mayor constancia se firma y se sella a los ({fecha_actual.day}) días del mes de {mes_actual_es} de {fecha_actual.year}.</para>",
            styles['Justify']
        ))
        elements.append(Spacer(1, 50))
        
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
                firma_img.drawHeight = 1.2*inch
                firma_img.drawWidth = 2.5*inch
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
        elements.append(Paragraph("CRA. 60A # 29 - 47 BARRIO LOS ANGELES", styles['SmallCenter']))
        
        # Generar PDF
        doc.build(elements)
        return response

def cambiar_contraseña(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            logout(request)
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('/')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'usuarios/cambiar_contraseña.html', {'form': form})
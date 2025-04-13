import matplotlib.pyplot as plt
import io
import base64
from django.views.generic import DetailView, ListView, TemplateView, View
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.shortcuts import redirect
from django.db.models import Count 
from .models import Alumno, Clase, Grupo, Materia, Asistencia, Nota
from ubicaciones.models import Municipio, Sede
from cartera.models import Deuda, Cuota  # Importar los modelos de la app cartera
from django.contrib.auth.models import User
from usuarios.models import Usuario, Firma
from datetime import datetime
from calendar import month_name
from django.db.models import F
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.db.models import Avg
from django.views.generic.edit import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import AlumnoForm
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from urllib.parse import urlencode
from django.http import QueryDict

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from django.conf import settings
import os
from django.http import HttpResponse, Http404
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from io import BytesIO

class AlumnosListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Alumno
    template_name = 'academico/alumnos_list.html'
    context_object_name = 'alumnos'
    paginate_by = 10
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        if self.request.user.groups.filter(name='Profesor').exists():
            return redirect(reverse('profesor_clases', kwargs={'profesor_id': self.request.user.id}))
        return redirect('login')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('municipio', 'grupo_actual__salon__sede')

        # Filtrar por municipio según el usuario
        if not self.request.user.is_superuser:
            # Si no es superuser, solo ver alumnos de su municipio
            queryset = queryset.filter(municipio=self.request.user.municipio)

        # Aplicar filtros de búsqueda
        nombre = self.request.GET.get('nombre')
        apellido = self.request.GET.get('apellido')
        sede = self.request.GET.get('sede')
        ciudad = self.request.GET.get('ciudad')
        culminado = self.request.GET.get('culminado')
        estado_deuda = self.request.GET.get('estado_deuda')
        es_becado = self.request.GET.get('es_becado')

        if nombre:
            queryset = queryset.filter(nombres__icontains=nombre)
        if apellido:
            queryset = queryset.filter(primer_apellido__icontains=apellido)
        if sede:
            queryset = queryset.filter(grupo_actual__salon__sede__nombre__icontains=sede)
        # Solo aplicar filtro de ciudad si es superuser
        if ciudad and self.request.user.is_superuser:
            queryset = queryset.filter(municipio__nombre__icontains=ciudad)
            
        # Filtrar por estado de culminación
        fecha_actual = timezone.localtime(timezone.now()).date()
        if culminado == 'si':
            queryset = queryset.filter(fecha_culminacion__lt=fecha_actual)
        elif culminado == 'no':
            queryset = queryset.filter(fecha_culminacion__gte=fecha_actual)
            
        # Filtrar por estado de deuda
        if estado_deuda == 'pagada':
            queryset = queryset.filter(deuda__estado='pagada')
        elif estado_deuda == 'pendiente':
            queryset = queryset.filter(deuda__estado='emitida')
        elif estado_deuda == 'no_tiene':
            queryset = queryset.filter(deuda__isnull=True)
            
        # Filtrar por beca
        if es_becado == 'si':
            queryset = queryset.filter(es_becado=True)
        elif es_becado == 'no':
            queryset = queryset.filter(es_becado=False)

        return queryset.order_by('primer_apellido')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros GET actuales
        get_params = self.request.GET.copy()
        
        # Eliminar 'page' si existe para evitar duplicados
        if 'page' in get_params:
            del get_params['page']
        
        # Convertir a string de consulta
        query_string = urlencode(get_params)
        
        # Agregar al contexto
        context['query_string'] = query_string
        
        # Filtrar sedes por municipio del usuario si no es superusuario
        if self.request.user.is_superuser:
            context['sedes'] = Sede.objects.all()
            context['ciudades'] = Municipio.objects.all()
        else:
            # Solo mostrar sedes del municipio del usuario
            context['sedes'] = Sede.objects.filter(municipio=self.request.user.municipio)
            
        # Añadir fecha actual para comparar con fecha_culminacion
        fecha_actual = timezone.localtime(timezone.now()).date()
        context['fecha_actual'] = fecha_actual
        
        # Procesar los alumnos para añadir información adicional
        alumnos_con_info = []
        for alumno in context['alumnos']:
            # Determinar si el alumno ha culminado
            culminado = alumno.fecha_culminacion < fecha_actual

            # Obtener estado de la deuda
            try:
                deuda = alumno.deuda
                if deuda.estado == 'pagada':
                    estado_deuda = 'pagada'
                else:  # estado 'emitida'
                    estado_deuda = 'pendiente'
            except Exception as e:
                # Si no existe relación con deuda o hay otro error
                estado_deuda = 'No tiene'
                
            # Añadir información al alumno
            alumno.culminado = culminado
            alumno.estado_deuda = estado_deuda
            # Ya tenemos acceso directo a es_becado desde el modelo
            alumnos_con_info.append(alumno)
            
        context['alumnos'] = alumnos_con_info
        return context

class AlumnoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = 'academico/alumno_form.html'
    success_url = reverse_lazy('alumnos_list')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Agregar Alumno'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Alumno agregado exitosamente.')
        return super().form_valid(form)


class AlumnoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Alumno
    form_class = AlumnoForm
    template_name = 'academico/alumno_form.html'
    success_url = reverse_lazy('alumnos_list')

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')


class AlumnoDetailView(LoginRequiredMixin, DetailView):
    model = Alumno
    template_name = 'academico/alumno_detail.html'
    context_object_name = 'alumno'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.get_object()

        # Obtener estadísticas de asistencia
        asistencias = Asistencia.objects.filter(alumno=alumno)
        asistencias_vistas = asistencias.filter(clase__estado='vista')
        
        # Obtener cuotas
        try:
            deuda = alumno.deuda
            cuotas = deuda.cuotas.all()
        except Deuda.DoesNotExist:
            deuda = None
            cuotas = []

        context.update({
            'titulo': f'Detalles de {alumno}',
            'deuda': deuda,
            'saldo_pendiente': deuda.saldo_pendiente if deuda else 0,
            'estado_deuda': deuda.estado if deuda else 'Sin deuda',
            'cuotas': cuotas,
            'asistencias': asistencias_vistas,
            'total_asistencias': asistencias_vistas.count(),
            'asistencias_presente': asistencias_vistas.filter(asistio=True).count(),
            'asistencias_faltas': asistencias_vistas.filter(asistio=False).count(),
            
            # Obtener notas y promedios por materia
            'notas': Nota.objects.filter(alumno=alumno, clase__estado='vista'),
            'promedios_materias': Nota.objects.filter(
                alumno=alumno,
                clase__estado='vista'
            ).values('clase__materia__nombre').annotate(
                promedio=Avg('nota')
            ).order_by('clase__materia__nombre')
        })
        
        return context


class ClaseListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Clase
    template_name = 'academico/clase_list.html'
    context_object_name = 'clases'
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = Clase.objects.all()
        
        # Filtrar por municipio según el usuario
        if not self.request.user.is_superuser:
            # Si no es superuser, solo ver clases de su municipio
            queryset = queryset.filter(salon__sede__municipio=self.request.user.municipio)
        
        # Filtros
        estado = self.request.GET.get('estado')
        profesor = self.request.GET.get('profesor')
        materia = self.request.GET.get('materia')
        sede = self.request.GET.get('sede')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        ciudad = self.request.GET.get('ciudad')

        if estado:
            queryset = queryset.filter(estado=estado)
        if profesor:
            queryset = queryset.filter(profesor_id=profesor)
        if materia:
            queryset = queryset.filter(materia_id=materia)
        if sede:
            queryset = queryset.filter(salon__sede_id=sede)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        # Solo aplicar filtro de ciudad si es superuser
        if ciudad and self.request.user.is_superuser:
            queryset = queryset.filter(salon__sede__municipio__nombre=ciudad)

        # Optimizar consultas y ordenar por fecha descendente
        return queryset.select_related(
            'profesor',
            'materia',
            'salon',
            'salon__sede',
            'grupo'
        ).order_by('-fecha', '-horario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar el mensaje preformateado para cada clase
        for clase in context['clases']:
            profesor = clase.profesor
            
            # Renderizar el mensaje con los datos actuales
            # La fecha se formateará automáticamente en español gracias a la configuración de Django
            
            message_context = {
                'nombre': profesor.first_name,
                'fecha': clase.fecha,
                'materia': clase.materia.nombre,
                'sede': clase.salon.sede.nombre,
                'horario': clase.horario
            }
            
            # Renderizar el template y codificar para URL
            clase.whatsapp_message = render_to_string(
                'academico/mensaje_clase_profesor.txt',
                message_context
            ).replace('\n', '%0A').replace(' ', '%20')
        
        # Si es superuser, mostrar todas las sedes y municipios
        if self.request.user.is_superuser:
            sedes = Sede.objects.all()
            context['ciudades'] = Municipio.objects.all()
        else:
            # Si no es superuser, solo mostrar sedes de su municipio
            sedes = Sede.objects.filter(municipio=self.request.user.municipio)
        
        context.update({
            'profesores': Usuario.objects.filter(groups__name='Profesor'),
            'materias': Materia.objects.all(),
            'sedes': sedes,
            'estados_clase': Clase.ESTADO_CLASE,
            'titulo': 'Lista de Clases'
        })
        return context


class ClaseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Clase
    template_name = 'academico/clase_detail.html'
    context_object_name = 'clase'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clase = self.get_object()
        
        context.update({
            'titulo': f'Detalles de la Clase - {clase}'
        })
        return context


class ClasesProfesorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Clase
    template_name = 'academico/clases_profesor_list.html'
    context_object_name = 'clases'
    login_url = 'login'
    paginate_by = 20  # Paginación de 2 elementos por página

    def test_func(self):
        return (
            self.request.user.is_staff or 
            self.request.user.id == int(self.kwargs.get('profesor_id'))
        )

    def get_queryset(self):
        profesor_id = self.kwargs.get('profesor_id')
        mes = self.request.GET.get('mes', datetime.now().month)
        estado = self.request.GET.get('estado', 'vista')
        año = datetime.now().year

        queryset = Clase.objects.filter(
            profesor_id=profesor_id,
            fecha__year=año,
            fecha__month=mes,
            estado=estado
        ).select_related(
            'materia',
            'salon',
            'salon__sede'  
        ).order_by('fecha', 'horario')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profesor_id = self.kwargs.get('profesor_id')
        mes_actual = int(self.request.GET.get('mes', datetime.now().month))
        estado_actual = self.request.GET.get('estado', 'vista')
        
        profesor = get_object_or_404(Usuario, id=profesor_id)
        materias_profesor = (
            Clase.objects.filter(
                profesor=profesor,
                fecha__year=datetime.now().year,
                fecha__month=mes_actual,
                estado=estado_actual
            )
            .values('materia__nombre')
            .annotate(total=Count('materia'))
            .order_by('-total')
        )
        
        # Calcular puede_registrar_asistencia para cada clase
        clases = context['clases']
        
        for clase in clases:
            clase.puede_registrar = clase.puede_registrar_asistencia(self.request.user)
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
            
        context.update({
            'profesor': profesor,
            'meses': [
                {'numero': i, 'nombre': month_name[i]} 
                for i in range(1, 13)
            ],
            'estados_clase': [
                {'valor': 'programada', 'nombre': 'Programadas'},
                {'valor': 'vista', 'nombre': 'Vistas'},
                {'valor': 'cancelada', 'nombre': 'Canceladas'}
            ],
            'mes_actual': mes_actual,
            'estado_actual': estado_actual,
            'año_actual': datetime.now().year,
            'materias_profesor': materias_profesor,
            'titulo': f'Clases {dict(Clase.ESTADO_CLASE).get(estado_actual, "").lower()} de {profesor.get_full_name()} - {month_name[mes_actual]}'
        })
        
        return context


class CronogramaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'academico/cronograma.html'
    
    def test_func(self):
        # Verificar si el usuario es superuser o pertenece a los grupos permitidos
        return (
            self.request.user.is_superuser or
            self.request.user.groups.filter(name__in=['SecretariaAcademica', 'SecretariaCartera']).exists()
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        fecha_str = self.request.GET.get('fecha')
        sede_id = self.request.GET.get('sede')
        tipo_horario = self.request.GET.get('tipo')  # AM o PM
        municipio_id = self.request.GET.get('municipio')
        
        # Establecer fecha inicial si no se proporciona
        if fecha_str:
            fecha_inicial = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha_inicial = datetime.now().date()
            # Ajustar a lunes si no lo es
            while fecha_inicial.weekday() != 0:
                fecha_inicial -= timedelta(days=1)
        
        # Calcular rango de fechas (lunes a sábado)
        fechas = []
        for i in range(6):  # 0 = lunes, 5 = sábado
            fecha = fecha_inicial + timedelta(days=i)
            fechas.append(fecha)
        
        # Filtrar sedes según el usuario
        if self.request.user.is_superuser:
            sedes = Sede.objects.all()
            municipios = Municipio.objects.all()
        else:
            # Obtener municipio del usuario (asumiendo que está en el modelo Usuario)
            municipio_usuario = self.request.user.municipio
            sedes = Sede.objects.filter(municipio=municipio_usuario)
            municipios = Municipio.objects.filter(id=municipio_usuario.id)
        
        # Aplicar filtros a las clases
        clases = Clase.objects.filter(fecha__range=[fecha_inicial, fechas[-1]])
        
        if sede_id:
            clases = clases.filter(salon__sede_id=sede_id)
        elif not self.request.user.is_superuser:
            # Si no se selecciona sede, filtrar por municipio del usuario
            clases = clases.filter(salon__sede__municipio=self.request.user.municipio)
        
        if municipio_id and self.request.user.is_superuser:
            clases = clases.filter(salon__sede__municipio_id=municipio_id)
        
        if tipo_horario:
            if tipo_horario == 'AM':
                clases = clases.filter(
                    Q(horario__startswith='08:00') |
                    Q(horario__startswith='10:00') |
                    Q(horario__startswith='7:00')
                )
            elif tipo_horario == 'PM':
                clases = clases.filter(horario__startswith='15:00')
        
        # Organizar clases por salón y fecha
        clases_organizadas = {}
        for clase in clases:
            salon_key = clase.salon.id
            if salon_key not in clases_organizadas:
                clases_organizadas[salon_key] = {
                    'salon': clase.salon,
                    'clases': {fecha: [] for fecha in fechas}
                }
            clases_organizadas[salon_key]['clases'][clase.fecha].append(clase)
        
        context.update({
            'fechas': fechas,
            'clases_organizadas': clases_organizadas,
            'sedes': sedes,
            'municipios': municipios,
            'fecha_actual': fecha_inicial,
            'fecha_anterior': fecha_inicial - timedelta(days=7),
            'fecha_siguiente': fecha_inicial + timedelta(days=7),
            'sede_seleccionada': sede_id,
            'municipio_seleccionado': municipio_id,
            'tipo_horario': tipo_horario,
            'puede_editar': self.request.user.is_superuser or 
                          self.request.user.groups.filter(name='SecretariaAcademica').exists()
        })
        
        return context


class GenerarCertificadosSimulacroView(View):
    def get(self, request, clase_id):
        try:
            clase = get_object_or_404(Clase, pk=clase_id)
            alumnos = Alumno.objects.filter(grupo_actual=clase.grupo)
            
            if not alumnos.exists():
                raise Http404("No hay alumnos en este grupo")
            
            response = HttpResponse(content_type='application/pdf')
            filename = f"certificados_simulacro_{clase.fecha.strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
            
            # Obtener estilos y modificar en lugar de redefinir
            styles = getSampleStyleSheet()
            
            # Modificar el estilo 'Title' existente en lugar de crear uno nuevo
            styles['Title'].alignment = TA_CENTER
            styles['Title'].fontSize = 14
            styles['Title'].fontName = 'Helvetica-Bold'
            
            # Crear estilos personalizados si no existen
            if 'Center' not in styles:
                styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
            if 'Justify' not in styles:
                styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
            
            # Estilo para el pie de página (letras pequeñas)
            styles.add(ParagraphStyle(name='SmallCenter', alignment=TA_CENTER, fontSize=8))
            
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
            
            # Obtener el mes de la clase en español
            mes_clase_es = meses_es.get(clase.fecha.strftime('%B'), clase.fecha.strftime('%B'))
            
            elements = []
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'img/logo.png')

            try:
                # Buscar la firma del usuario actual
                coordinador = request.user
                firma = Firma.objects.get(usuario=coordinador)
            except (Firma.DoesNotExist, Usuario.DoesNotExist):
                firma = None
            
            for alumno in alumnos:
                if os.path.exists(logo_path):
                    elements.append(Image(logo_path, width=2*inch, height=1*inch))
                    elements.append(Spacer(1, 20))
                
                # Encabezado
                elements.append(Paragraph('<b>EL PRE ICFES VICTOR VALDEZ</b>', styles['Title']))
                elements.append(Spacer(1, 10))
                elements.append(Paragraph('<b>NIT - 9012725987</b>', styles['Title']))
                elements.append(Spacer(1, 20))
                elements.append(Paragraph('<b>HACE CONSTAR QUE</b>', styles['Center']))
                elements.append(Spacer(1, 20))
                elements.append(Spacer(1, 20))
                elements.append(Spacer(1, 20))
                elements.append(Spacer(1, 20))
                
                # Cuerpo del certificado
                nombre_completo = f"{alumno.nombres} {alumno.primer_apellido}{' ' + alumno.segundo_apellido if alumno.segundo_apellido else ''}"
                
                texto_certificado = f"""
                <para align=justify>
                <b>{nombre_completo}</b>, identificado(a) con {alumno.get_tipo_identificacion_display()}, N° <b>{alumno.identificacion}</b>, 
                se encuentra realizando el curso de PRE ICFES en nuestra Institución, el día {clase.fecha.day} de {mes_clase_es} del presente año. 
                Estará realizando un simulacro de jornada completa en los horarios de 8:00 AM a 12:00 PM y de 1:00 PM a 5:00 PM
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
                elements.append(Spacer(1, 40))
                elements.append(Spacer(1, 40))
                
                # Firma
                if firma and firma.imagen and os.path.exists(firma.imagen.path):
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
                
                if alumno != alumnos.last():
                    elements.append(PageBreak())
            
            doc.build(elements)
            response.write(buffer.getvalue())
            buffer.close()
            return response
            
        except Exception as e:
            raise Http404(f"Error al generar certificados: {str(e)}")


class GenerarConstanciaPreICFESView(UserPassesTestMixin, LoginRequiredMixin, View):
    login_url = '/login/'
    
    def test_func(self):
        # Permitir acceso solo a superusers y miembros del grupo 'SecretariaCartera'
        user = self.request.user
        return user.is_superuser or user.groups.filter(name='SecretariaAcademica').exists()
    def get(self, request, alumno_id):
        alumno = get_object_or_404(Alumno, pk=alumno_id)
        
        # Configurar respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        filename = f"constancia_preicfes_{alumno.primer_apellido}_{alumno.identificacion}.pdf"
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
        elements.append(Spacer(1, 20))
        elements.append(Paragraph('<b>NIT - 9012725987</b>', styles['Title']))
        elements.append(Spacer(1, 30))
        
        # Cuerpo del certificado
        nombre_completo = f"{alumno.nombres} {alumno.primer_apellido}{' ' + alumno.segundo_apellido if alumno.segundo_apellido else ''}"
        
        # Obtener la fecha de la primera clase del alumno
        primera_clase = None
        try:
            # Intentar obtener la primera clase del grupo actual del alumno
            if alumno.grupo_actual:
                primera_clase = Clase.objects.filter(
                    grupo=alumno.grupo_actual,
                    estado='vista'  # Solo clases que ya se han visto
                ).order_by('fecha').first()
        except Exception as e:
            # Si hay algún error, continuar sin la fecha de la primera clase
            pass
        
        # Usar las fechas de ingreso y culminación del alumno
        dia_inicio = alumno.fecha_ingreso.day
        mes_inicio_en_ingles = alumno.fecha_ingreso.strftime('%B')
        mes_inicio = meses_es.get(mes_inicio_en_ingles, mes_inicio_en_ingles)
        anio_inicio = alumno.fecha_ingreso.year
        
        # Fecha de finalización desde el campo fecha_culminacion
        mes_fin_en_ingles = alumno.fecha_culminacion.strftime('%B')
        mes_fin = meses_es.get(mes_fin_en_ingles, mes_fin_en_ingles)
        anio_fin = alumno.fecha_culminacion.year
        
        # Calcular la duración en meses
        from dateutil.relativedelta import relativedelta
        duracion = relativedelta(alumno.fecha_culminacion, alumno.fecha_ingreso)
        duracion_meses = duracion.months + (duracion.years * 12)
        
        # Obtener las clases del alumno (no simulacros)
        clases_alumno = Clase.objects.filter(
            grupo=alumno.grupo_actual,
            estado='vista'
        ).exclude(
            horario__in=['08:00-12:00', '08:00-17:00']  # Excluir simulacros
        ).order_by('fecha')
        
        # Determinar los días de la semana en que el alumno tiene clases
        dias_semana = set()
        for clase in clases_alumno:
            dia_semana = clase.fecha.strftime('%A')
            dias_semana.add(dia_semana)
        
        # Convertir los días de la semana a español
        dias_semana_es = {
            'Monday': 'lunes',
            'Tuesday': 'martes',
            'Wednesday': 'miércoles',
            'Thursday': 'jueves',
            'Friday': 'viernes',
            'Saturday': 'sábado',
            'Sunday': 'domingo'
        }
        
        dias_clases = [dias_semana_es.get(dia, dia) for dia in dias_semana]
        dias_clases.sort()  # Ordenar los días
        
        # Formatear los días para el texto
        if len(dias_clases) == 1:
            texto_dias = f"los días {dias_clases[0]}"
        elif len(dias_clases) == 2:
            texto_dias = f"los días {dias_clases[0]} y {dias_clases[1]}"
        else:
            texto_dias = f"los días {', '.join(dias_clases[:-1])} y {dias_clases[-1]}"
        
        # Determinar los horarios de clase
        horas_inicio = set()
        horas_fin = set()
        
        for clase in clases_alumno:
            hora_inicio = clase.get_hora_inicio()
            hora_fin = clase.get_hora_fin()
            horas_inicio.add(hora_inicio)
            horas_fin.add(hora_fin)
        
        # Formatear las horas para el texto
        if horas_inicio and horas_fin:
            hora_inicio_min = min(horas_inicio)
            hora_fin_max = max(horas_fin)
            
            # Formatear en AM/PM
            def formatear_hora(hora):
                hora_12 = hora.strftime('%I:%M')
                # Eliminar cero inicial si existe
                if hora_12.startswith('0'):
                    hora_12 = hora_12[1:]
                ampm = 'am' if hora.hour < 12 else 'pm'
                return f"{hora_12} {ampm}"
            
            texto_horario = f"de {formatear_hora(hora_inicio_min)} hasta las {formatear_hora(hora_fin_max)}"
        else:
            # Si no hay clases, usar un texto genérico
            texto_horario = "en horario regular"
        
        # Añadir cada párrafo por separado
        elements.append(Paragraph("<b>CERTIFICA QUE</b>", styles['Center']))
        elements.append(Spacer(1, 10))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        
        
        texto_constancia = f"""Que <b>{nombre_completo}</b>, identificada(o) con {alumno.get_tipo_identificacion_display()} N° <b>{alumno.identificacion}</b>, 
        se encuentra realizando con nosotros el curso de PRE ICFES, al cual ingresó en modalidad presencial {texto_dias} 
        {texto_horario} desde {mes_inicio} del {anio_inicio}. Fecha de finalización del mes de {mes_fin} de {anio_fin}."""
        
        elements.append(Paragraph(texto_constancia, styles['Justify']))
        elements.append(Spacer(1, 40))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))

        try:
            # Usar la firma del usuario actual que está generando el certificado
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
        nombre_completo = f"{coordinador.first_name} {coordinador.last_name}"
        if not nombre_completo.strip():
            nombre_completo = coordinador.username
            
        elements.append(Paragraph(f"<b>{nombre_completo}</b>", styles['Center']))
        elements.append(Paragraph("<b>COORDINADOR(A) ACADÉMICO(A) PRE ICFES VICTOR VALDEZ</b>", styles['Center']))
        
        # Agregar teléfono si está disponible
        telefono = coordinador.telefono if hasattr(coordinador, 'telefono') and coordinador.telefono else ""
        if telefono:
            elements.append(Paragraph(f"Cel: {telefono}", styles['Center']))
        
        
        # Pie de página en letras pequeñas
        elements.append(Paragraph("<b>VALDEZ Y ANDRADE SOLUCIONES S.A.S</b>", styles['SmallCenter']))
        elements.append(Paragraph("<b>NIT 901.272.598 - 7</b>", styles['SmallCenter']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("CRA. 60A # 29 - 47 BARRIO LOS ANGELES", styles['SmallCenter']))
        
        # Generar PDF
        doc.build(elements)
        return response


class GrupoDetailView(LoginRequiredMixin, DetailView):
    model = Grupo
    template_name = 'academico/grupo_detalle.html'
    context_object_name = 'grupo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupo = self.get_object()

        # Obtener las clases vistas
        clases_vistas = Clase.objects.filter(
            grupo=grupo,
            estado='vista'
        ).select_related(
            'profesor',
            'materia',
            'salon',
            'salon__sede'
        )

        # Guardar las clases ordenadas por fecha para el template
        context['clases_vistas'] = clases_vistas.order_by('-fecha')

        # Obtener estadísticas de materias
        materias_preicfes = Materia.objects.all()

        frecuencia_materias = (
            clases_vistas.values('materia__nombre')
            .annotate(total=Count('materia'))
            .order_by('materia__nombre')
        )

        frecuencia_dict = {item['materia__nombre']: item['total'] for item in frecuencia_materias}

        materias = [materia.nombre for materia in materias_preicfes]
        totales = [frecuencia_dict.get(materia.nombre, 0) for materia in materias_preicfes]

        plt.figure(figsize=(12, 6))
        bars = plt.bar(materias, totales, color='skyblue')
        plt.xlabel('Materias')
        plt.ylabel('Frecuencia de clases vistas')
        plt.title(f'Frecuencia de materias vistas en clases - Grupo {grupo.codigo}')
        plt.xticks(rotation=45)
        plt.tight_layout()

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()

        graphic = base64.b64encode(image_png).decode('utf-8')

        alumnos = Alumno.objects.filter(grupo_actual=grupo)

        context['graphic'] = graphic
        context['alumnos'] = alumnos
        return context


class GrupoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Grupo
    template_name = 'academico/grupo_list.html'
    context_object_name = 'grupos'
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = Grupo.objects.select_related('salon', 'salon__sede', 'salon__sede__municipio').annotate(
            sillas_ocupadas=Count('alumnos_actuales'),
            sillas_totales=F('salon__capacidad_sillas')
        )
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(salon__sede__municipio=self.request.user.municipio)
        
        # Filtros
        sede = self.request.GET.get('sede')
        ciudad = self.request.GET.get('ciudad')
        
        if sede:
            queryset = queryset.filter(salon__sede_id=sede)
        if ciudad:
            queryset = queryset.filter(salon__sede__municipio__nombre=ciudad)
            
        return queryset.order_by('salon__sede__municipio__nombre', 'salon__sede__nombre', 'codigo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Si es superuser, mostrar todas las sedes y ciudades
        if self.request.user.is_superuser:
            context['sedes'] = Sede.objects.all()
            context['ciudades'] = Municipio.objects.values_list('nombre', flat=True).distinct()
        else:
            # Si no es superuser, solo mostrar sedes de su municipio
            context['sedes'] = Sede.objects.filter(municipio=self.request.user.municipio)
            context['ciudades'] = [self.request.user.municipio.nombre]
        
        context['titulo'] = 'Lista de Grupos'
        return context


class RegistroAsistenciaNotaView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Clase
    template_name = 'academico/registro_asistencia_nota.html'
    context_object_name = 'clase'

    def test_func(self):
        user = self.request.user
        clase = self.get_object()
        
        # Si la clase está vista, el profesor no puede acceder más
        if clase.estado == 'vista' and user == clase.profesor:
            return False
            
        # Usar el mismo método que usamos para mostrar el botón
        return clase.puede_registrar_asistencia(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clase = self.get_object()
        
        # Obtener o crear registros de asistencia y nota para cada alumno
        alumnos_registros = []  # Nota: ahora es con "s" en todos los lugares
        for alumno in clase.grupo.alumnos_actuales.all():
            asistencia, _ = Asistencia.objects.get_or_create(
                alumno=alumno,
                clase=clase,
                defaults={'asistio': False}
            )
            nota, _ = Nota.objects.get_or_create(
                alumno=alumno,
                clase=clase,
                defaults={'nota': None}
            )
            # nota.nota = float(nota.nota) if nota.nota is not None else None
            alumnos_registros.append({  # Asegúrate que este nombre coincida con el de la plantilla
                'alumno': alumno,
                'asistencia': asistencia,
                'nota': nota
            })

        context.update({
            'alumnos_registros': alumnos_registros,  # Nombre consistente
            'titulo': f'Registro de Asistencia y Notas - {clase}',
            'puede_marcar_vista': self.request.user.is_superuser or 
                                self.request.user.groups.filter(name='SecretariaAcademica').exists() or 
                                (self.request.user == clase.profesor and clase.estado != 'vista')
        })
        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        clase = self.get_object()
        guardar_y_marcar = request.POST.get('guardar_y_marcar', False)
        
        # Verificar permisos usando el mismo método que el modelo
        if not clase.puede_registrar_asistencia(request.user):
            messages.error(request, 'No tiene permiso para registrar asistencia en este momento.')
            return redirect('profesor_clases', profesor_id=request.user.id)
        
        # Procesar cada alumno
        for alumno in clase.grupo.alumnos_actuales.all():
            # Actualizar asistencia
            asistencia = Asistencia.objects.get_or_create(
                alumno=alumno,
                clase=clase,
                defaults={'asistio': False}
            )[0]
            asistencia.asistio = request.POST.get(f'asistencia_{alumno.id}') == 'on'
            asistencia.save()
            
            # Actualizar nota
            nota = Nota.objects.get_or_create(
                alumno=alumno,
                clase=clase,
                defaults={'nota': None}
            )[0]
            nota_valor = request.POST.get(f'nota_{alumno.id}')
            if nota_valor and nota_valor.strip():
                try:
                    nota.nota = float(nota_valor)
                    nota.save()
                except ValueError:
                    messages.error(request, f'Valor de nota inválido para {alumno}')
                    return redirect('registro_asistencia_nota', pk=clase.pk)
            else:
                nota.nota = None
                nota.save()
        
        # Si se pidió marcar como vista y el usuario tiene permiso
        if guardar_y_marcar and (
            request.user.is_superuser or 
            request.user.groups.filter(name='SecretariaAcademica').exists() or 
            (request.user == clase.profesor and clase.estado != 'vista')
        ):
            clase.estado = 'vista'
            clase.save()
            messages.success(request, 'Clase marcada como vista y registros guardados.')
        else:
            messages.success(request, 'Registros guardados exitosamente.')
        
        return redirect('profesor_clases', profesor_id=clase.profesor.id)
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode
from ..models import Alumno
from ubicaciones.models import Municipio, Departamento, Sede

class AlumnosListView(UserPassesTestMixin, LoginRequiredMixin, ListView):
    model = Alumno
    template_name = 'academico/alumnos_list.html'
    context_object_name = 'alumnos'
    paginate_by = 20
    login_url = 'login'

    def test_func(self):
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        if self.request.user.groups.filter(name='Profesor').exists():
            return redirect(reverse('profesor_clases', kwargs={'profesor_id': self.request.user.id}))
        return redirect('login')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('municipio__departamento', 'grupo_actual__salon__sede')
        user = self.request.user

        # Lógica de filtrado por rol
        if user.is_superuser:
            # Superusuario ve todo
            pass
        elif user.groups.filter(name__in=['CoordinadorDepartamental', 'Auxiliar']).exists():
            # Coordinador o Auxiliar ven todo su departamento
            if hasattr(user, 'departamento') and user.departamento:
                queryset = queryset.filter(municipio__departamento=user.departamento)
        else:
            # Otro personal (staff) ve solo su municipio
            queryset = queryset.filter(municipio=user.municipio)

        # Aplicar filtros de búsqueda
        nombre = self.request.GET.get('nombre')
        apellido = self.request.GET.get('apellido')
        sede = self.request.GET.get('sede')
        ciudad = self.request.GET.get('ciudad')
        departamento_id = self.request.GET.get('departamento')
        culminado = self.request.GET.get('culminado')
        estado_deuda = self.request.GET.get('estado_deuda')
        es_becado = self.request.GET.get('es_becado')
        tipo_programa = self.request.GET.get('tipo_programa')
        estado_alumno = self.request.GET.get('estado_alumno')  # Filtro de estado
        tiene_cuotas = self.request.GET.get('tiene_cuotas')    # Filtro de cuotas

        if nombre:
            queryset = queryset.filter(nombres__icontains=nombre)
        if apellido:
            queryset = queryset.filter(primer_apellido__icontains=apellido)
        if sede:
            queryset = queryset.filter(grupo_actual__salon__sede__nombre__icontains=sede)
        # Filtros de ubicación jerárquicos para Superuser
        if self.request.user.is_superuser:
            if departamento_id:
                queryset = queryset.filter(municipio__departamento_id=departamento_id)
            if ciudad: # El filtro de ciudad puede refinar el de departamento
                queryset = queryset.filter(municipio__nombre__icontains=ciudad)
        # Filtro de ciudad para otros roles con permiso
        elif ciudad and self.request.user.groups.filter(name__in=['CoordinadorDepartamental', 'Auxiliar']).exists():
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
            
        # Filtrar por tipo de programa
        if tipo_programa:
            queryset = queryset.filter(tipo_programa=tipo_programa)
            
        # Filtrar por estado del alumno (activo/retirado)
        if estado_alumno:
            queryset = queryset.filter(estado=estado_alumno)
            
        # Filtrar por si tiene cuotas asociadas
        if tiene_cuotas == 'si':
            queryset = queryset.filter(deuda__cuotas__isnull=False).distinct()
        elif tiene_cuotas == 'no':
            # Aplicar .distinct() a ambas partes de la operación OR para evitar TypeError
            no_deuda = queryset.filter(deuda__isnull=True).distinct()
            deuda_sin_cuotas = queryset.filter(deuda__isnull=False, deuda__cuotas__isnull=True).distinct()
            queryset = no_deuda | deuda_sin_cuotas

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
        
        # Lógica de contexto por rol
        user = self.request.user
        context['is_coordinador_or_auxiliar'] = user.groups.filter(name__in=['CoordinadorDepartamental', 'Auxiliar']).exists()
        if user.is_superuser:
            context['sedes'] = Sede.objects.all()
            context['ciudades'] = Municipio.objects.all()
            context['departamentos'] = Departamento.objects.all()
            context['departamento_seleccionado'] = self.request.GET.get('departamento')
        elif user.groups.filter(name__in=['CoordinadorDepartamental', 'Auxiliar']).exists():
            if hasattr(user, 'departamento') and user.departamento:
                context['sedes'] = Sede.objects.filter(municipio__departamento=user.departamento)
                context['ciudades'] = Municipio.objects.filter(departamento=user.departamento)
            else:
                context['sedes'] = Sede.objects.none()
                context['ciudades'] = Municipio.objects.none()
        else:
            # Otro personal (staff) ve solo su municipio
            context['sedes'] = Sede.objects.filter(municipio=user.municipio)
            context['ciudades'] = Municipio.objects.filter(id=user.municipio.id)
            
        # Añadir tipos de programa al contexto
        context['tipos_programa'] = dict(Alumno.TIPO_PROGRAMA)
        context['tipo_programa_seleccionado'] = self.request.GET.get('tipo_programa')
            
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
            
            # Verificar si tiene cuotas asociadas
            try:
                tiene_cuotas = alumno.deuda and alumno.deuda.cuotas.exists()
            except Exception as e:
                tiene_cuotas = False
                
            alumno.tiene_cuotas = tiene_cuotas
            # Ya tenemos acceso directo a es_becado desde el modelo
            alumnos_con_info.append(alumno)
            
        context['alumnos'] = alumnos_con_info
        return context
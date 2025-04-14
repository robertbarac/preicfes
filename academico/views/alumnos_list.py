from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlencode
from ..models import Alumno
from ubicaciones.models import Municipio, Sede

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
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F

from academico.models import Grupo, Alumno
from ubicaciones.models import Sede, Municipio

class GrupoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Grupo
    template_name = 'academico/grupo_list.html'
    context_object_name = 'grupos'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = Grupo.objects.select_related('salon', 'salon__sede', 'salon__sede__municipio').annotate(
            sillas_ocupadas=Count('alumnos_actuales'),
            sillas_totales=F('salon__capacidad_sillas')
        ).prefetch_related('alumnos_actuales')
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(salon__sede__municipio=self.request.user.municipio)
        
        # Filtros
        sede = self.request.GET.get('sede')
        ciudad = self.request.GET.get('ciudad')
        tipo_programa = self.request.GET.get('tipo_programa')
        
        if sede:
            queryset = queryset.filter(salon__sede_id=sede)
        if ciudad:
            queryset = queryset.filter(salon__sede__municipio__nombre=ciudad)
        if tipo_programa:
            # Filtrar grupos que tienen al menos un alumno con el tipo de programa seleccionado
            queryset = queryset.filter(alumnos_actuales__tipo_programa=tipo_programa).distinct()
            
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
        
        # Añadir tipos de programa al contexto
        context['tipos_programa'] = dict(Alumno.TIPO_PROGRAMA)
        context['tipo_programa_seleccionado'] = self.request.GET.get('tipo_programa', '')
        
        # Preparar los tipos de programa para cada grupo
        grupos = context['grupos']
        for grupo in grupos:
            # Obtener los tipos de programa distintos de los alumnos en este grupo
            programas = set()
            for alumno in grupo.alumnos_actuales.all():
                if alumno.tipo_programa:
                    programas.add(alumno.tipo_programa)
            grupo.programas_lista = list(programas)
        
        return context
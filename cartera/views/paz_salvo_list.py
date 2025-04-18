from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q

from academico.models import Alumno

class PazSalvoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    model = Alumno
    template_name = 'cartera/paz_salvo_list.html'
    context_object_name = 'alumnos'
    paginate_by = 20

    def get_queryset(self):
        queryset = Alumno.objects.filter(
            deuda__saldo_pendiente=0  # Solo alumnos con deuda saldada
        ).distinct().select_related(
            'deuda',
            'grupo_actual__salon',
            'grupo_actual__salon__sede',
            'grupo_actual__salon__sede__municipio'
        ).order_by('primer_apellido', 'nombres', 'id')  # Añadir orden explícito para evitar advertencias de paginación
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(grupo_actual__salon__sede__municipio=self.request.user.municipio)
        else:
            # Si es superuser y hay un filtro por municipio
            municipio_id = self.request.GET.get('municipio')
            if municipio_id:
                queryset = queryset.filter(grupo_actual__salon__sede__municipio_id=municipio_id)
        
        # Filtro de búsqueda
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) |
                Q(primer_apellido__icontains=search_query) |
                Q(segundo_apellido__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        
        # Solo agregar municipios al contexto si es superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all().order_by('nombre')
            context['selected_municipio'] = self.request.GET.get('municipio')
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
        
        return context

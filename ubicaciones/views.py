from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F
from .models import Salon, Sede
from academico.models import Grupo

# Create your views here.

class SalonListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Salon
    template_name = 'ubicaciones/salon_list.html'
    context_object_name = 'salones'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        queryset = Salon.objects.select_related('sede', 'sede__municipio')
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(sede__municipio=self.request.user.municipio)
        
        # Filtros
        sede = self.request.GET.get('sede')
        ciudad = self.request.GET.get('ciudad')
        capacidad_min = self.request.GET.get('capacidad_min')
        capacidad_max = self.request.GET.get('capacidad_max')
        
        if sede:
            queryset = queryset.filter(sede_id=sede)
        if ciudad:
            queryset = queryset.filter(sede__municipio__nombre=ciudad)
        if capacidad_min:
            queryset = queryset.filter(capacidad_sillas__gte=capacidad_min)
        if capacidad_max:
            queryset = queryset.filter(capacidad_sillas__lte=capacidad_max)

        return queryset.order_by('sede__municipio__nombre', 'sede__nombre', 'numero')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Si es superuser, mostrar todas las sedes y ciudades
        if self.request.user.is_superuser:
            context['sedes'] = Sede.objects.all()
            context['ciudades'] = Sede.objects.values_list('municipio__nombre', flat=True).distinct()
        else:
            # Si no es superuser, solo mostrar sedes de su municipio
            context['sedes'] = Sede.objects.filter(municipio=self.request.user.municipio)
        
        context['titulo'] = 'Lista de Salones'
        return context

class SalonDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Salon
    template_name = 'ubicaciones/salon_detail.html'
    context_object_name = 'salon'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        salon = self.get_object()
        
        # Obtener los grupos que usan este salón
        grupos = Grupo.objects.filter(salon=salon).select_related(
            'salon', 'salon__sede', 'salon__sede__municipio'
        ).annotate(
            sillas_ocupadas=Count('alumnos_actuales')
        )
        
        context.update({
            'grupos': grupos,
            'titulo': f'Detalles del Salón {salon}'
        })
        return context

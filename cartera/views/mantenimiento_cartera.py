from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone

from cartera.models import Cuota

class MantenimientoCarteraView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'cartera/mantenimiento_cartera.html'
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener cuotas que necesitan actualización
        queryset = Cuota.objects.filter(
            estado='emitida',
            fecha_vencimiento__lt=timezone.localtime(timezone.now()).date()
        )
        
        # Filtrar por municipio si no es superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
        
        context['cuotas_por_actualizar'] = queryset.count()
        return context
    
    def post(self, request, *args, **kwargs):
        # Obtener cuotas que necesitan actualización
        queryset = Cuota.objects.filter(
            estado='emitida',
            fecha_vencimiento__lt=timezone.localtime(timezone.now()).date()
        )
        
        # Filtrar por municipio si no es superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
        
        # Actualizar estados
        cuotas_actualizadas = queryset.count()
        queryset.update(estado='vencida')
        
        # Agregar mensaje y contexto
        context = self.get_context_data(**kwargs)
        context['cuotas_actualizadas'] = cuotas_actualizadas
        return self.render_to_response(context)
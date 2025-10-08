from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin
from cartera.models import Deuda
from django.shortcuts import get_object_or_404

class DeudaUpdateView(UserPassesTestMixin, UpdateView):
    model = Deuda
    fields = ['valor_total']
    template_name = 'cartera/deuda_form.html'
    
    def test_func(self):
        # Obtener la deuda
        deuda = self.get_object()
        
        # Si el usuario es 'vvgomez', siempre tiene acceso sin restricciones
        if self.request.user.username == 'vvgomez' or self.request.user.username == 'claudia2019':
            return True
        
        # Para otros usuarios, verificar si es superuser o pertenece al grupo SecretariaCartera
        # Y además verificar si la edición está habilitada
        is_admin = self.request.user.is_superuser
        is_in_group = self.request.user.groups.filter(name='SecretariaCartera').exists()
        
        # Solo permitir acceso si es admin o está en el grupo Y la edición está habilitada
        return (is_admin or is_in_group) and deuda.edicion_habilitada
    
    def get_success_url(self):
        return reverse_lazy('alumno_detail', kwargs={'pk': self.object.alumno.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Actualizar el saldo pendiente y estado después de guardar
        self.object.actualizar_saldo_y_estado()
        return response

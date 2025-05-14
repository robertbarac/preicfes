from django.views.generic import FormView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from usuarios.models import Usuario
from usuarios.forms import CertificadoTrabajoForm


class CertificadoTrabajoFormView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'usuarios/certificado_trabajo_form.html'
    form_class = CertificadoTrabajoForm
    
    def test_func(self):
        # Solo superuser y SecretariaAcademica pueden generar certificados
        return (
            self.request.user.is_superuser or
            self.request.user.groups.filter(name='SecretariaAcademica').exists()
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profesor_id = self.kwargs.get('profesor_id')
        profesor = get_object_or_404(Usuario, pk=profesor_id)
        context['profesor'] = profesor
        return context
    
    def form_valid(self, form):
        profesor_id = self.kwargs.get('profesor_id')
        fecha_inicio = form.cleaned_data['fecha_inicio']
        fecha_fin = form.cleaned_data['fecha_fin']
        
        # Redirigir a la vista de generación del PDF con los parámetros de fecha
        url = reverse('generar_certificado_trabajo', kwargs={'profesor_id': profesor_id})
        url += f'?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        return redirect(url)

from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from usuarios.models import Usuario

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

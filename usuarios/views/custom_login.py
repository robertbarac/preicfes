from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin

class CustomLoginView(LoginView):
    template_name = 'usuarios/login.html'

    def get_success_url(self):
        if self.request.user.groups.filter(name='Profesor').exists():
            return reverse_lazy('profesor_clases', kwargs={'profesor_id': self.request.user.id})
        else:
            return reverse_lazy('alumnos_list')
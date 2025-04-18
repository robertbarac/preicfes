from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse

from cartera.models import Cuota
from cartera.forms import CuotaUpdateForm

class CuotaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Cuota
    form_class = CuotaUpdateForm
    template_name = 'cartera/cuota_update_form.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cuota = self.get_object()
        context['alumno'] = cuota.deuda.alumno
        return context

    def form_valid(self, form):
        cuota = form.save(commit=False)
        cuota.save()
        return super().form_valid(form)

    def get_success_url(self):
        cuota = self.get_object()
        return reverse('alumno_detail', kwargs={'pk': cuota.deuda.alumno.id})
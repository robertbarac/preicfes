from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse

from cartera.models import Cuota, Deuda
from cartera.forms import CuotaForm

class CuotaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Cuota
    form_class = CuotaForm
    template_name = 'cartera/cuota_form.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        deuda_id = self.kwargs.get('deuda_id')  # Obtener el ID de la deuda de la URL
        context['deuda'] = get_object_or_404(Deuda, id=deuda_id)  # Obtener la deuda
        return context

    def form_valid(self, form):
        cuota = form.save(commit=False)
        cuota.deuda = self.get_context_data()['deuda']  # Asociar la cuota con la deuda
        cuota.save()
        return super().form_valid(form)

    def get_success_url(self):
        deuda_id = self.get_context_data()['deuda'].id  # Obtener el ID de la deuda
        alumno_id = self.get_context_data()['deuda'].alumno.id  # Obtener el ID del alumno asociado a la deuda
        return reverse('alumno_detail', kwargs={'pk': alumno_id})  # Redirigir a la vista de detalles del alumno

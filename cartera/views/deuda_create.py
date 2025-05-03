from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404

from cartera.models import Deuda
from cartera.forms import DeudaForm
from academico.models import Alumno


class DeudaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Deuda
    form_class = DeudaForm
    template_name = 'cartera/deuda_form.html'
    # No usamos success_url fijo porque necesitamos el ID del alumno
    # Usaremos get_success_url en su lugar

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno_id = self.kwargs.get('alumno_id')  # Obtener el ID del alumno de la URL
        context['alumno'] = get_object_or_404(Alumno, id=alumno_id)  # Obtener el alumno
        return context

    def form_valid(self, form):
        deuda = form.save(commit=False)
        alumno_id = self.kwargs.get('alumno_id')  # Obtener el ID del alumno de la URL
        deuda.alumno = get_object_or_404(Alumno, id=alumno_id)  # Asignar el alumno a la deuda
        deuda.saldo_pendiente = form.cleaned_data['saldo_pendiente']  # Asegurarse de que se guarde el saldo pendiente
        deuda.save()
        return super().form_valid(form)

    def get_success_url(self):
        # Redirigir al detalle del alumno después de crear la deuda
        alumno_id = self.kwargs.get('alumno_id')
        return reverse_lazy('alumno_detail', kwargs={'pk': alumno_id})
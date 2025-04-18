from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.utils import timezone
from academico.models import Alumno, Grupo
from ubicaciones.models import Municipio

class AlumnosRetiradosListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Alumno
    template_name = 'cartera/alumnos_retirados_list.html'
    context_object_name = 'alumnos'
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_queryset(self):
        queryset = Alumno.objects.filter(estado='retirado', grupo_actual__codigo='RETIRADOS')
        municipio_id = self.request.GET.get('municipio')
        mes = self.request.GET.get('mes')
        anio = self.request.GET.get('anio')
        if municipio_id:
            queryset = queryset.filter(grupo_actual__salon__sede__municipio_id=municipio_id)
        if mes and anio:
            queryset = queryset.filter(fecha_retiro__month=mes, fecha_retiro__year=anio)
        elif anio:
            queryset = queryset.filter(fecha_retiro__year=anio)
        return queryset.select_related('grupo_actual', 'grupo_actual__salon', 'grupo_actual__salon__sede', 'grupo_actual__salon__sede__municipio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumnos = context['alumnos']
        context['total_retirados'] = alumnos.count()
        # Suma de saldo pendiente para todos los alumnos retirados
        context['total_saldo_pendiente'] = sum([getattr(a.deuda, 'saldo_pendiente', 0) if hasattr(a, 'deuda') and a.deuda and a.deuda.estado == 'emitida' else 0 for a in alumnos])
        if self.request.user.is_superuser:
            context['municipios'] = Municipio.objects.all().order_by('nombre')
        context['mes_actual'] = timezone.localtime(timezone.now()).month
        context['anio_actual'] = timezone.localtime(timezone.now()).year
        # Lista de años para el filtro (actual ±2)
        anio_actual = context['anio_actual']
        context['anios'] = [anio_actual - 2, anio_actual - 1, anio_actual, anio_actual + 1, anio_actual + 2]
        context['mes'] = str(self.request.GET.get('mes', '') or '')
        context['anio'] = str(self.request.GET.get('anio', '') or '')
        context['municipio_seleccionado'] = str(self.request.GET.get('municipio', '') or '')
        return context

from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.utils import timezone
from academico.models import Alumno, Grupo
from ubicaciones.models import Municipio

class AlumnosRetiradosListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Alumno
    template_name = 'academico/alumnos_retirados_list.html'
    context_object_name = 'alumnos'
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        user = self.request.user
        # Queryset base
        queryset = Alumno.objects.filter(estado='retirado')

        # Filtrado por rol
        if user.is_superuser:
            pass  # Superuser ve todo
        elif user.groups.filter(name='CoordinadorDepartamental').exists():
            if user.departamento:
                queryset = queryset.filter(municipio__departamento=user.departamento)
        else:
            # Otro personal (staff) ve solo su municipio
            queryset = queryset.filter(municipio=user.municipio)

        # Filtros del formulario
        municipio_id = self.request.GET.get('municipio')
        mes = self.request.GET.get('mes')
        anio = self.request.GET.get('anio')
        tipo_programa = self.request.GET.get('tipo_programa')

        if municipio_id:
            queryset = queryset.filter(municipio_id=municipio_id)
        if mes and anio:
            queryset = queryset.filter(fecha_retiro__month=mes, fecha_retiro__year=anio)
        elif anio:
            queryset = queryset.filter(fecha_retiro__year=anio)
        if tipo_programa:
            queryset = queryset.filter(tipo_programa=tipo_programa)
            
        return queryset.select_related('municipio__departamento', 'grupo_actual__salon__sede')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumnos = context['alumnos']
        context['total_retirados'] = context['object_list'].count()

        # Lógica de contexto por rol
        user = self.request.user
        if user.is_superuser:
            context['municipios'] = Municipio.objects.all().order_by('nombre')
        elif user.groups.filter(name='CoordinadorDepartamental').exists():
            if user.departamento:
                context['municipios'] = Municipio.objects.filter(departamento=user.departamento).order_by('nombre')
            else:
                context['municipios'] = Municipio.objects.none()
        else:
            context['municipios'] = Municipio.objects.filter(id=user.municipio.id)
        context['mes_actual'] = timezone.localtime(timezone.now()).month
        context['anio_actual'] = timezone.localtime(timezone.now()).year
        context['mes'] = self.request.GET.get('mes', '')
        context['anio'] = self.request.GET.get('anio', '')
        context['municipio_seleccionado'] = self.request.GET.get('municipio', '')
        context['tipo_programa_seleccionado'] = self.request.GET.get('tipo_programa', '')
        # Añadir tipos de programa al contexto
        context['tipos_programa'] = dict(Alumno.TIPO_PROGRAMA)
        # Rango de años para el filtro (actual +/- 2)
        anio_actual = context['anio_actual']
        context['anios'] = list(range(anio_actual + 2, anio_actual - 3, -1))
        return context

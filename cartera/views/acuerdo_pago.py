from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils import timezone
from cartera.models import AcuerdoPago, Cuota
from cartera.forms import AcuerdoPagoForm, AcuerdoPagoFilterForm

class AcuerdoPagoListView(LoginRequiredMixin, ListView):
    model = AcuerdoPago
    template_name = 'cartera/acuerdo_pago_list.html'
    context_object_name = 'acuerdos'

    def get_queryset(self):
        hoy = timezone.localtime(timezone.now()).date()
        # Actualizar estados de acuerdos emitidos
        acuerdos_pendientes = AcuerdoPago.objects.filter(estado='emitido')
        for acuerdo in acuerdos_pendientes:
            if acuerdo.cuota.estado in ['pagada', 'pagada_parcial']:
                acuerdo.estado = 'cumplido'
                acuerdo.save()
            elif acuerdo.fecha_prometida_pago < hoy:
                acuerdo.estado = 'incumplido'
                acuerdo.save()

        # Queryset base
        queryset = AcuerdoPago.objects.select_related(
            'cuota__deuda__alumno',
            'cuota__deuda__alumno__municipio__departamento'
        ).order_by('fecha_prometida_pago')

        # Filtrado basado en roles de usuario
        user = self.request.user
        if not user.is_superuser:
            if user.groups.filter(name='CoordinadorDepartamental').exists() and user.departamento:
                queryset = queryset.filter(cuota__deuda__alumno__municipio__departamento=user.departamento)
            elif user.groups.filter(name='SecretariaCartera').exists() and user.municipio:
                queryset = queryset.filter(cuota__deuda__alumno__municipio=user.municipio)
            else:
                # Si no es superusuario y no tiene rol con ubicación, no muestra nada
                return queryset.none()

        # Aplicar filtros del formulario
        self.filter_form = AcuerdoPagoFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            departamento = self.filter_form.cleaned_data.get('departamento')
            municipio = self.filter_form.cleaned_data.get('municipio')
            dias_restantes = self.filter_form.cleaned_data.get('dias_restantes')

            if municipio:
                queryset = queryset.filter(cuota__deuda__alumno__municipio=municipio)
            elif departamento:
                queryset = queryset.filter(cuota__deuda__alumno__municipio__departamento=departamento)

            if dias_restantes is not None:
                fecha_exacta = hoy + timezone.timedelta(days=dias_restantes)
                queryset = queryset.filter(fecha_prometida_pago=fecha_exacta)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localtime(timezone.now()).date()
        for acuerdo in context['acuerdos']:
            delta = acuerdo.fecha_prometida_pago - hoy
            acuerdo.dias_faltantes = delta.days
        
        # Añadir el formulario de filtros al contexto
        context['filter_form'] = self.filter_form
        return context

class AcuerdoPagoCreateView(LoginRequiredMixin, CreateView):
    model = AcuerdoPago
    form_class = AcuerdoPagoForm
    template_name = 'cartera/acuerdo_pago_form.html'

    def form_valid(self, form):
        cuota = get_object_or_404(Cuota, pk=self.kwargs['cuota_pk'])
        form.instance.cuota = cuota
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cuota'] = get_object_or_404(Cuota, pk=self.kwargs['cuota_pk'])
        return context

    def get_success_url(self):
        return reverse_lazy('alumno_detail', kwargs={'pk': self.object.cuota.deuda.alumno.pk})

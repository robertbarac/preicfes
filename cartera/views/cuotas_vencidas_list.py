from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import F, ExpressionWrapper, fields, Q
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string

from cartera.models import Cuota

class CuotasVencidasListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Cuota
    template_name = 'cartera/cuotas_vencidas_list.html'
    context_object_name = 'cuotas'
    paginate_by = 20

    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()

    def get_queryset(self):

        queryset = super().get_queryset().filter(
            estado__in=['emitida', 'pagada_parcial', 'vencida'],
            fecha_vencimiento__lt=timezone.localtime(timezone.now()),
            deuda__alumno__estado='activo'  # Solo alumnos activos
        ).select_related('deuda', 'deuda__alumno', 'deuda__alumno__municipio')

        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(deuda__alumno__municipio=self.request.user.municipio)
        else:
            # Si es superuser y hay un filtro por municipio
            municipio_id = self.request.GET.get('municipio')
            if municipio_id:
                queryset = queryset.filter(deuda__alumno__municipio_id=municipio_id)

        # Aplicar filtros
        dias_filtro = self.request.GET.get('dias_filtro', 'todos')
        identificacion = self.request.GET.get('identificacion', '')
        apellido = self.request.GET.get('apellido', '')

        if dias_filtro != 'todos':
            dias = dias_filtro.split('-')
            if len(dias) == 1:  # Caso de '90+'
                queryset = queryset.filter(
                    fecha_vencimiento__lt=timezone.localtime(timezone.now()) - timedelta(days=int(dias[0]))
                )
            else:
                min_dias = int(dias[0])
                max_dias = int(dias[1])
                queryset = queryset.filter(
                    fecha_vencimiento__lt=timezone.localtime(timezone.now()) - timedelta(days=min_dias),
                    fecha_vencimiento__gte=timezone.localtime(timezone.now()) - timedelta(days=max_dias)
                )

        if identificacion:
            queryset = queryset.filter(deuda__alumno__identificacion__icontains=identificacion)

        if apellido:
            queryset = queryset.filter(
                Q(deuda__alumno__primer_apellido__icontains=apellido) |
                Q(deuda__alumno__segundo_apellido__icontains=apellido)
            )

        queryset = queryset.annotate(
            dias_atraso=ExpressionWrapper(
                timezone.localtime(timezone.now()).date() - F('fecha_vencimiento'),
                output_field=fields.IntegerField()
            )
        ).order_by('-dias_atraso')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar el mensaje preformateado y días de atraso a cada cuota
        for cuota in context['cuotas']:
            alumno = cuota.deuda.alumno
            cuota.dias_atraso = (timezone.localtime(timezone.now()).date() - cuota.fecha_vencimiento).days

            # Renderizar el mensaje con los datos actuales
            message_context = {
                'nombres': alumno.nombres,
                'primer_apellido': alumno.primer_apellido,
                'fecha_vencimiento': cuota.fecha_vencimiento,
                'dias_atraso': cuota.dias_atraso,
                'monto': cuota.monto,
                'monto_abonado': cuota.monto_abonado,
                'saldo_pendiente': cuota.deuda.saldo_pendiente
            }
            
            # Renderizar el template y codificar para URL
            cuota.whatsapp_message = render_to_string(
                'cartera/whatsapp_message_template.txt',
                message_context
            ).replace('\n', '%0A').replace(' ', '%20')
        
        # Agregar filtros al contexto
        context.update({
            'dias_filtro': self.request.GET.get('dias_filtro', 'todos'),
            'identificacion': self.request.GET.get('identificacion', ''),
            'apellido': self.request.GET.get('apellido', '')
        })
        
        # Solo agregar municipios al contexto si es superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all().order_by('nombre')
            context['municipio_seleccionado'] = self.request.GET.get('municipio')
        
        return context
from cartera.models.deuda import Deuda
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.db.models import Sum
from django.utils import timezone
from django.utils.formats import date_format

from cartera.models import Cuota


class InformeDiarioView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    template_name = 'cartera/informe_diario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener fecha del filtro o usar la actual
        fecha_str = self.request.GET.get('fecha')
        if fecha_str:
            fecha_seleccionada = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha_seleccionada = timezone.localtime(timezone.now()).date()
        
        context['fecha_seleccionada'] = fecha_seleccionada.strftime('%Y-%m-%d')
        
        # Obtener municipio seleccionado
        municipio_id = self.request.GET.get('municipio')
        if not self.request.user.is_superuser:
            try:
                municipio_id = self.request.user.municipio.id
            except AttributeError:
                # User has no assigned municipality, so they can't see any data.
                municipio_id = None
                context['warning_message'] = 'No tienes un municipio asignado. Contacta al administrador.'
            
        # Obtener tipo de programa seleccionado
        tipo_programa = self.request.GET.get('tipo_programa')
        
        # Obtener lista de municipios para superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all()
            context['municipio_seleccionado'] = int(municipio_id) if municipio_id else None
            
        # Obtener lista de tipos de programa para el filtro
        from academico.models import Alumno
        context['tipos_programa'] = dict(Alumno.TIPO_PROGRAMA)
        context['tipo_programa_seleccionado'] = tipo_programa
            
        # Base queryset para cuotas
        cuotas_qs = Cuota.objects.all()
        
        # Filtrar por municipio
        if municipio_id:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
            
        # Filtrar por tipo de programa
        if tipo_programa:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__tipo_programa=tipo_programa
            )
        
        # Datos de recaudación del día (basado en la fecha de pago seleccionada)
        cuotas_hoy = cuotas_qs.filter(
            fecha_pago=fecha_seleccionada,
            monto_abonado__gt=0
        )
        
        # Totales por método de pago
        context['recaudo_efectivo'] = cuotas_hoy.filter(
            metodo_pago='efectivo'
        ).aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        context['recaudo_transferencia'] = cuotas_hoy.filter(
            metodo_pago='transferencia'
        ).aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        context['recaudo_datáfono'] = cuotas_hoy.filter(
            metodo_pago='datáfono'
        ).aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        context['total_recaudado'] = (
            context['recaudo_efectivo'] + 
            context['recaudo_transferencia'] + 
            context['recaudo_datáfono']
        )
        
        # Objetivo del mes (basado en el mes de la fecha seleccionada)
        mes_actual = fecha_seleccionada.month
        anio_actual = fecha_seleccionada.year
        
        # Calcular el objetivo del mes como la suma de todas las cuotas con vencimiento en el mes actual de alumnos activos
        # Esto sigue usando fecha_vencimiento ya que es el objetivo contractual
        context['objetivo_mes'] = cuotas_qs.filter(
            fecha_vencimiento__month=mes_actual,
            fecha_vencimiento__year=anio_actual,
            deuda__alumno__estado='activo'
        ).aggregate(Sum('monto'))['monto__sum'] or 0
        
        # % de cumplimiento - basado en pagos realizados en el mes actual
        recaudado_mes = cuotas_qs.filter(
            fecha_pago__month=mes_actual,
            fecha_pago__year=anio_actual,
            monto_abonado__gt=0
        ).aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        # Calcular el porcentaje de cumplimiento
        context['porcentaje_cumplimiento'] = (
            (recaudado_mes / context['objetivo_mes']) * 100 
            if context['objetivo_mes'] > 0 else 0
        )
        
        context['recaudado_mes'] = recaudado_mes
        
        # Reporte de cartera
        # Obtener todas las cuotas sin filtrar por estado
        todas_cuotas_qs = Cuota.objects.all()
        
        # Filtrar por municipio
        if municipio_id:
            todas_cuotas_qs = todas_cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            todas_cuotas_qs = todas_cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
            
        # Filtrar por tipo de programa
        if tipo_programa:
            todas_cuotas_qs = todas_cuotas_qs.filter(
                deuda__alumno__tipo_programa=tipo_programa
            )
        
        # Construir queryset de Deuda para aplicar filtros, considerando la fecha seleccionada
        deudas_qs = Deuda.objects.filter(
            alumno__estado='activo',
            fecha_creacion__date__lte=fecha_seleccionada
        )

        if municipio_id:
            deudas_qs = deudas_qs.filter(alumno__grupo_actual__salon__sede__municipio_id=municipio_id)
        elif not self.request.user.is_superuser:
            deudas_qs = deudas_qs.filter(alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio)

        if tipo_programa:
            deudas_qs = deudas_qs.filter(alumno__tipo_programa=tipo_programa)

        # Valor total de cartera (suma de todos los montos de deudas filtradas)
        context['valor_cartera'] = deudas_qs.aggregate(Sum('valor_total'))['valor_total__sum'] or 0
        
        # context['valor_cartera'] = todas_cuotas_qs.filter(
        #     deuda__alumno__estado='activo'
        # ).aggregate(Sum('monto'))['monto__sum'] or 0
        
        # Total cobrado hasta la fecha seleccionada
        context['cobrado'] = todas_cuotas_qs.filter(
            deuda__alumno__estado='activo',
            fecha_pago__lte=fecha_seleccionada
        ).aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        # Falta por cobrar
        context['falta_cobrar'] = context['valor_cartera'] - context['cobrado']
        
        # Fecha formateada para mostrar en el título
        context['fecha_actual'] = date_format(
            fecha_seleccionada, 
            "l, j \d\e F \d\e Y"
        ).capitalize()
        
        return context
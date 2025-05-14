import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum
from django.utils import timezone
from calendar import month_name

from cartera.models import Cuota, Egreso


class GraficaIngresosEgresosView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    template_name = 'cartera/grafica.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name='SecretariaCartera').exists():
            return HttpResponseForbidden("No tienes permisos para ver esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        año_actual = timezone.now().year

        # Obtener el año seleccionado para la gráfica
        año_seleccionado = int(self.request.GET.get('año', año_actual))

        # Obtener el año y mes seleccionados para el cumplimiento
        año_cumplimiento = int(self.request.GET.get('año_cumplimiento', año_actual))
        mes_cumplimiento = int(self.request.GET.get('mes_cumplimiento', timezone.now().month))

        # Obtener municipio seleccionado
        municipio_id = self.request.GET.get('municipio')
        if not self.request.user.is_superuser:
            # Si no es superuser, usar su municipio asignado
            municipio_id = self.request.user.municipio.id

        # Obtener lista de municipios para superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all()
            context['municipio_seleccionado'] = int(municipio_id) if municipio_id else None

        # Base queryset para cuotas
        cuotas_qs = Cuota.objects.all()
        if municipio_id:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )

        # Obtener los años disponibles para la gráfica (basado en cuándo se realizaron los pagos)
        # Primero intentamos obtener años de fecha_pago (para pagos ya realizados)
        años_pago = list(cuotas_qs.filter(fecha_pago__isnull=False).dates('fecha_pago', 'year').values_list('fecha_pago__year', flat=True))
        # Luego añadimos años de fecha_vencimiento (para pagos futuros)
        años_vencimiento = list(cuotas_qs.dates('fecha_vencimiento', 'year').values_list('fecha_vencimiento__year', flat=True))
        años_grafica = list(set(años_pago + años_vencimiento))
        if not años_grafica or año_actual not in años_grafica:
            años_grafica.append(año_actual)
        años_grafica = sorted(set(años_grafica))

        # Los años de cumplimiento son los mismos que los de la gráfica
        años_cumplimiento = años_grafica

        # La meta mensual es la suma de todas las cuotas del mes de alumnos activos
        meta_mensual = cuotas_qs.filter(
            fecha_vencimiento__year=año_cumplimiento,
            fecha_vencimiento__month=mes_cumplimiento,
            deuda__alumno__estado='activo'
        ).aggregate(total=Sum('monto'))['total'] or 0

        # Obtener los ingresos del mes (basado en cuándo se realizaron los pagos realmente)
        ingresos_mes = cuotas_qs.filter(
            fecha_pago__year=año_cumplimiento,
            fecha_pago__month=mes_cumplimiento,
            estado='pagada',
            monto_abonado__gt=0
        ).aggregate(total=Sum('monto_abonado'))['total'] or 0

        # Calcular el porcentaje de cumplimiento
        porcentaje_cumplimiento = (ingresos_mes / meta_mensual * 100) if meta_mensual > 0 else 0

        # Calcular superávit o déficit
        superavit_deficit = ingresos_mes - meta_mensual

        context.update({
            'año_seleccionado': año_seleccionado,
            'año_cumplimiento': año_cumplimiento,
            'mes_cumplimiento': mes_cumplimiento,
            'años_grafica': años_grafica,
            'años_cumplimiento': años_cumplimiento,
            'meta_mensual': meta_mensual,
            'ingresos_mes': ingresos_mes,
            'porcentaje_cumplimiento': porcentaje_cumplimiento,
            'superavit_deficit': superavit_deficit,
            'nombre_mes': month_name[mes_cumplimiento],
            'meses': [(i, month_name[i]) for i in range(1, 13)]
        })
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        if 'grafica' in request.GET:
            return self.generar_grafica(context)
        return self.render_to_response(context)


    def generar_grafica(self, context):
        año_seleccionado = int(self.request.GET.get('año', timezone.now().year))

        # Obtener municipio seleccionado
        municipio_id = self.request.GET.get('municipio')
        if not self.request.user.is_superuser:
            # Si no es superuser, usar su municipio asignado
            municipio_id = self.request.user.municipio.id

        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        ingresos = [0] * 12
        egresos = [0] * 12

        # Base queryset para cuotas - usando fecha_pago para mostrar cuándo realmente se recibió el dinero
        cuotas_qs = Cuota.objects.filter(
            fecha_pago__year=año_seleccionado,
            estado='pagada',
            monto_abonado__gt=0  # Asegurarse de que se haya pagado algo
        )
        
        # Filtrar cuotas por municipio
        if municipio_id:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            cuotas_qs = cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )

        # Agrupar cuotas por mes - usando el mes de pago real
        cuotas = cuotas_qs.values('fecha_pago__month').annotate(
            total_abonado=Sum('monto_abonado')
        )

        for cuota in cuotas:
            ingresos[cuota['fecha_pago__month'] - 1] = float(cuota['total_abonado'] or 0)

        # Consulta para egresos
        egresos_qs = Egreso.objects.filter(fecha__year=año_seleccionado)
        
        # Filtrar egresos por municipio
        if municipio_id:
            egresos_qs = egresos_qs.filter(
                sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            egresos_qs = egresos_qs.filter(
                sede__municipio=self.request.user.municipio
            )

        # Agrupar egresos por mes
        egresos_db = egresos_qs.values('fecha__month').annotate(
            total_egresado=Sum('valor')
        )

        for egreso in egresos_db:
            egresos[egreso['fecha__month'] - 1] = float(egreso['total_egresado'] or 0)

        # Configuración de la gráfica de barras lado a lado
        plt.figure(figsize=(12, 6))
        index = np.arange(len(meses))
        bar_width = 0.35

        # Gráficas de barras
        barra_ingresos = plt.bar(index, ingresos, bar_width, label='Ingresos', color='#4CAF50')
        barra_egresos = plt.bar(index + bar_width, egresos, bar_width, label='Egresos', color='#F44336')

        # Mostrar valores en la parte superior de las barras
        for barra in barra_ingresos:
            altura = barra.get_height()
            plt.text(barra.get_x() + barra.get_width() / 2, altura, f'${altura:,.0f}', ha='center', va='bottom', fontsize=10, color='black')

        for barra in barra_egresos:
            altura = barra.get_height()
            plt.text(barra.get_x() + barra.get_width() / 2, altura, f'${altura:,.0f}', ha='center', va='bottom', fontsize=10, color='black')

        # Configuración final de la gráfica
        plt.xlabel('Meses')
        plt.ylabel('Valor ($)')
        plt.title(f'Ingresos vs Egresos - {año_seleccionado}')
        plt.xticks(index + bar_width / 2, meses)
        plt.legend()
        plt.tight_layout()

        # Guardar la gráfica en un buffer para mostrarla en el template
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        plt.close()
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'inline; filename=grafica_{año_seleccionado}.png'
        return response
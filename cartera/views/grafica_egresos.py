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
from collections import defaultdict

from cartera.models import Egreso


class GraficaEgresosView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    template_name = 'cartera/grafica_egresos.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.groups.filter(name='SecretariaCartera').exists():
            return HttpResponseForbidden("No tienes permisos para ver esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        año_actual = timezone.now().year

        # Obtener el año seleccionado para la gráfica
        año_seleccionado = int(self.request.GET.get('año', año_actual))

        # Obtener el mes seleccionado para detalles
        mes_seleccionado = int(self.request.GET.get('mes', timezone.now().month))

        # Obtener municipio seleccionado
        municipio_id = self.request.GET.get('municipio')
        if not self.request.user.is_superuser:
            # Si no es superuser, usar su municipio asignado
            municipio_id = self.request.user.municipio.id

        # Obtener concepto seleccionado
        concepto = self.request.GET.get('concepto')

        # Obtener lista de municipios para superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all()
            context['municipio_seleccionado'] = int(municipio_id) if municipio_id else None

        # Base queryset para egresos
        egresos_qs = Egreso.objects.filter(fecha__year=año_seleccionado)
        
        if municipio_id:
            egresos_qs = egresos_qs.filter(municipio_id=municipio_id)
        elif not self.request.user.is_superuser:
            egresos_qs = egresos_qs.filter(municipio=self.request.user.municipio)
            
        if concepto:
            egresos_qs = egresos_qs.filter(concepto=concepto)

        # Obtener los años disponibles para la gráfica
        años_disponibles = list(Egreso.objects.dates('fecha', 'year').values_list('fecha__year', flat=True))
        if not años_disponibles or año_actual not in años_disponibles:
            años_disponibles.append(año_actual)
        años_disponibles = sorted(set(años_disponibles))

        # Calcular egresos por mes para la gráfica
        egresos_por_mes = egresos_qs.values('fecha__month').annotate(total=Sum('valor'))
        egresos_mensuales = [0] * 12
        for egreso in egresos_por_mes:
            egresos_mensuales[egreso['fecha__month'] - 1] = float(egreso['total'] or 0)
        
        # Calcular egresos por concepto para el mes seleccionado
        egresos_mes = egresos_qs.filter(fecha__month=mes_seleccionado)
        total_mes = egresos_mes.aggregate(total=Sum('valor'))['total'] or 0
        
        egresos_por_concepto = egresos_mes.values('concepto').annotate(total=Sum('valor'))
        detalles_conceptos = []
        
        for egreso in egresos_por_concepto:
            concepto_key = egreso['concepto']
            concepto_display = dict(Egreso.CONCEPTO_CHOICES).get(concepto_key, concepto_key)
            monto = float(egreso['total'] or 0)
            porcentaje = (monto / float(total_mes) * 100) if total_mes > 0 else 0
            
            detalles_conceptos.append({
                'concepto_key': concepto_key,
                'concepto': concepto_display,
                'monto': monto,
                'porcentaje': porcentaje
            })

        context.update({
            'año_seleccionado': año_seleccionado,
            'años_disponibles': años_disponibles,
            'mes_seleccionado': mes_seleccionado,
            'nombre_mes': month_name[mes_seleccionado],
            'meses': [(i, month_name[i]) for i in range(1, 13)],
            'egresos_mensuales': egresos_mensuales,
            'total_egresos_año': sum(egresos_mensuales),
            'total_egresos_mes': total_mes,
            'detalles_conceptos': detalles_conceptos,
            'conceptos': Egreso.CONCEPTO_CHOICES,
            'concepto_seleccionado': concepto
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
        
        # Obtener concepto seleccionado
        concepto = self.request.GET.get('concepto')

        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        egresos = [0] * 12

        # Base queryset para egresos
        egresos_qs = Egreso.objects.filter(fecha__year=año_seleccionado)
        
        # Filtrar por municipio
        if municipio_id:
            egresos_qs = egresos_qs.filter(municipio_id=municipio_id)
        elif not self.request.user.is_superuser:
            egresos_qs = egresos_qs.filter(municipio=self.request.user.municipio)
            
        # Filtrar por concepto
        if concepto:
            egresos_qs = egresos_qs.filter(concepto=concepto)

        # Agrupar egresos por mes
        egresos_por_mes = egresos_qs.values('fecha__month').annotate(total=Sum('valor'))

        for egreso in egresos_por_mes:
            egresos[egreso['fecha__month'] - 1] = float(egreso['total'] or 0)

        # Configuración de la gráfica de barras
        plt.figure(figsize=(12, 6))
        index = np.arange(len(meses))
        bar_width = 0.6

        # Gráfica de barras
        barras = plt.bar(index, egresos, bar_width, color='#F44336')

        # Mostrar valores en la parte superior de las barras
        for barra in barras:
            altura = barra.get_height()
            plt.text(barra.get_x() + barra.get_width() / 2, altura, f'${altura:,.0f}', ha='center', va='bottom', fontsize=10, color='black')

        # Configuración final de la gráfica
        plt.xlabel('Meses')
        plt.ylabel('Valor ($)')
        titulo = f'Egresos - {año_seleccionado}'
        if concepto:
            concepto_display = dict(Egreso.CONCEPTO_CHOICES).get(concepto, concepto)
            titulo += f' - {concepto_display}'
        plt.title(titulo)
        plt.xticks(index, meses)
        plt.tight_layout()

        # Guardar la gráfica en un buffer para mostrarla en el template
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        plt.close()
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'inline; filename=grafica_egresos_{año_seleccionado}.png'
        return response

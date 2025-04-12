import io
from io import BytesIO
import os
import json
from datetime import timedelta, date, datetime
from calendar import month_name
from decimal import Decimal

# Matplotlib para gráficos
import numpy as np
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt

# Django imports
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DeleteView, ListView, DetailView, TemplateView, View
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.formats import date_format
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import DurationField, ExpressionWrapper, F, IntegerField, Sum, Q, Case, When, Value, FloatField, Count, fields
from django.db.models.functions import Now, TruncDate, ExtractDay, Cast, Coalesce
from django.template.loader import render_to_string
from django.conf import settings

# Modelos de la aplicación
from .models import Cuota, Egreso, Deuda, MetaRecaudo
from .forms import DeudaForm, CuotaForm, CuotaUpdateForm
from academico.models import Alumno
from usuarios.models import Firma

# Reportlab para generar PDFs
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class BecadosListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    model = Alumno
    template_name = 'cartera/becados_list.html'
    context_object_name = 'becados'
    paginate_by = 20  # Paginación de 2 elementos por página
   
    def get_queryset(self):
        queryset = Alumno.objects.filter(
            es_becado=True
        ).select_related(
            'grupo_actual__salon',
            'grupo_actual__salon__sede',
            'grupo_actual__salon__sede__municipio'
        )
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(grupo_actual__salon__sede__municipio=self.request.user.municipio)
        else:
            # Si es superuser y hay un filtro por municipio
            municipio_id = self.request.GET.get('municipio')
            if municipio_id:
                queryset = queryset.filter(grupo_actual__salon__sede__municipio_id=municipio_id)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_becados'] = self.get_queryset().count()
        
        # Solo agregar municipios al contexto si es superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all().order_by('nombre')
            context['selected_municipio'] = self.request.GET.get('municipio')
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
            
        return context


# class CarteraListView(LoginRequiredMixin, ListView):
#     model = Cuota
#     template_name = 'cartera/cartera.html'
#     context_object_name = 'cuotas'
#     paginate_by = 10  

#     def get_queryset(self):
#         queryset = Cuota.objects.annotate(
#             # Calcular la diferencia en días de manera manual
#             dias_sin_pago=Cast(
#                 (TruncDate(Now()) - F('fecha_vencimiento')) / timedelta(days=1),
#                 IntegerField()
#             )
#         )

#         # Filtrar por estado solo si el usuario lo elige en el template
#         estado = self.request.GET.get('estado')
#         if estado in ["emitida", "pagada", "vencida", "pagada_parcial"]:
#             queryset = queryset.filter(estado=estado)

#         # Filtrar por días de atraso (opcional según el template)
#         filtro_dias = self.request.GET.get('dias')
#         if filtro_dias:
#             dias = int(filtro_dias)
#             fecha_limite = TruncDate(Now()) - timedelta(days=dias)
#             queryset = queryset.filter(fecha_vencimiento__gte=fecha_limite)

#         # Filtrar por nombre del alumno (si el usuario escribe algo)
#         nombre_alumno = self.request.GET.get('nombre')
#         if nombre_alumno:
#             queryset = queryset.filter(deuda__alumno__nombres__icontains=nombre_alumno)

#         # Filtrar por sede (si el usuario lo elige)
#         sede = self.request.GET.get('sede')
#         if sede:
#             queryset = queryset.filter(deuda__alumno__sede__nombre__icontains=sede)

#         # Ordenar por días de atraso
#         orden = self.request.GET.get('orden')
#         if orden == 'mayor':
#             queryset = queryset.order_by('-dias_sin_pago')
#         else:
#             queryset = queryset.order_by('dias_sin_pago')

#         return queryset


class CuotasVencidasListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Cuota
    template_name = 'cartera/cuotas_vencidas_list.html'
    context_object_name = 'cuotas'
    paginate_by = 20

    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()

    def get_queryset(self):
        from django.db.models import F, ExpressionWrapper, fields, Q
        from datetime import timedelta

        queryset = super().get_queryset().filter(
            estado__in=['emitida', 'pagada_parcial', 'vencida'],
            fecha_vencimiento__lt=timezone.now()
        ).select_related('deuda', 'deuda__alumno', 'deuda__alumno__municipio')

        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(deuda__alumno__municipio=self.request.user.municipio)

        # Aplicar filtros
        dias_filtro = self.request.GET.get('dias_filtro', 'todos')
        identificacion = self.request.GET.get('identificacion', '')
        apellido = self.request.GET.get('apellido', '')

        if dias_filtro != 'todos':
            dias = dias_filtro.split('-')
            if len(dias) == 1:  # Caso de '90+'
                queryset = queryset.filter(
                    fecha_vencimiento__lt=timezone.now() - timedelta(days=int(dias[0]))
                )
            else:
                min_dias = int(dias[0])
                max_dias = int(dias[1])
                queryset = queryset.filter(
                    fecha_vencimiento__lt=timezone.now() - timedelta(days=min_dias),
                    fecha_vencimiento__gte=timezone.now() - timedelta(days=max_dias)
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
                timezone.now().date() - F('fecha_vencimiento'),
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
        
        return context



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


class CuotaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Cuota
    template_name = 'cartera/cuota_confirm_delete.html'
    
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return redirect('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cuota = self.get_object()
        context['alumno'] = cuota.deuda.alumno
        return context

    def get_success_url(self):
        cuota = self.get_object()
        return reverse('alumno_detail', kwargs={'pk': cuota.deuda.alumno.id})


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


class DeudaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Deuda
    form_class = DeudaForm
    template_name = 'cartera/deuda_form.html'
    success_url = reverse_lazy('alumnos_list')

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
        deuda.saldo_pendiente = form.cleaned_data['saldo_pendiente']  # Asegurarse de que se guarde el saldo pendiente
        deuda.save()
        return super().form_valid(form)


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

        # Obtener los años disponibles para la gráfica
        años_grafica = list(cuotas_qs.dates('fecha_vencimiento', 'year').values_list('fecha_vencimiento__year', flat=True))
        if not años_grafica or año_actual not in años_grafica:
            años_grafica.append(año_actual)
        años_grafica = sorted(set(años_grafica))

        # Los años de cumplimiento son los mismos que los de la gráfica
        años_cumplimiento = años_grafica

        # La meta mensual es la suma de todas las cuotas del mes
        meta_mensual = cuotas_qs.filter(
            fecha_vencimiento__year=año_cumplimiento,
            fecha_vencimiento__month=mes_cumplimiento
        ).aggregate(total=Sum('monto'))['total'] or 0

        # Obtener los ingresos del mes (cuotas pagadas)
        ingresos_mes = cuotas_qs.filter(
            fecha_vencimiento__year=año_cumplimiento,
            fecha_vencimiento__month=mes_cumplimiento,
            estado='pagada'
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

        # Base queryset para cuotas
        cuotas_qs = Cuota.objects.filter(
            fecha_vencimiento__year=año_seleccionado,
            estado='pagada'
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

        # Agrupar cuotas por mes
        cuotas = cuotas_qs.values('fecha_vencimiento__month').annotate(
            total_abonado=Sum('monto_abonado')
        )

        for cuota in cuotas:
            ingresos[cuota['fecha_vencimiento__month'] - 1] = float(cuota['total_abonado'] or 0)

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


class MantenimientoCarteraView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'cartera/mantenimiento_cartera.html'
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener cuotas que necesitan actualización
        queryset = Cuota.objects.filter(
            estado='emitida',
            fecha_vencimiento__lt=timezone.localtime(timezone.now()).date()
        )
        
        # Filtrar por municipio si no es superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
        
        context['cuotas_por_actualizar'] = queryset.count()
        return context
    
    def post(self, request, *args, **kwargs):
        # Obtener cuotas que necesitan actualización
        queryset = Cuota.objects.filter(
            estado='emitida',
            fecha_vencimiento__lt=timezone.localtime(timezone.now()).date()
        )
        
        # Filtrar por municipio si no es superuser
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
        
        # Actualizar estados
        cuotas_actualizadas = queryset.count()
        queryset.update(estado='vencida')
        
        # Agregar mensaje y contexto
        context = self.get_context_data(**kwargs)
        context['cuotas_actualizadas'] = cuotas_actualizadas
        return self.render_to_response(context)


class PazSalvoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    model = Alumno
    template_name = 'cartera/paz_salvo_list.html'
    context_object_name = 'alumnos'
    paginate_by = 20

    def get_queryset(self):
        queryset = Alumno.objects.filter(
            deuda__saldo_pendiente=0  # Solo alumnos con deuda saldada
        ).distinct().select_related(
            'deuda',
            'grupo_actual__salon',
            'grupo_actual__salon__sede',
            'grupo_actual__salon__sede__municipio'
        ).order_by('primer_apellido', 'nombres', 'id')  # Añadir orden explícito para evitar advertencias de paginación
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(grupo_actual__salon__sede__municipio=self.request.user.municipio)
        else:
            # Si es superuser y hay un filtro por municipio
            municipio_id = self.request.GET.get('municipio')
            if municipio_id:
                queryset = queryset.filter(grupo_actual__salon__sede__municipio_id=municipio_id)
        
        # Filtro de búsqueda
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(nombres__icontains=search_query) |
                Q(primer_apellido__icontains=search_query) |
                Q(segundo_apellido__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        
        # Solo agregar municipios al contexto si es superuser
        if self.request.user.is_superuser:
            from ubicaciones.models import Municipio
            context['municipios'] = Municipio.objects.all().order_by('nombre')
            context['selected_municipio'] = self.request.GET.get('municipio')
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
        
        return context


class PazSalvoPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser or 'SecretariaCartera' in self.request.user.groups.all().values_list('name', flat=True)

    def handle_no_permission(self):
        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")

    def get(self, request, alumno_id):
        alumno = get_object_or_404(Alumno, pk=alumno_id)
        
        try:
            deuda = alumno.deuda  # Accede a la deuda a través del related_name
            if not (deuda.estado == 'pagada' and deuda.saldo_pendiente == 0):
                return HttpResponseForbidden("El alumno no está a paz y salvo")
                
        except Deuda.DoesNotExist:
            return HttpResponseForbidden("El alumno no tiene registros de deuda")

        # Traducción de meses al español
        meses_es = {
            'January': 'enero',
            'February': 'febrero',
            'March': 'marzo',
            'April': 'abril',
            'May': 'mayo',
            'June': 'junio',
            'July': 'julio',
            'August': 'agosto',
            'September': 'septiembre',
            'October': 'octubre',
            'November': 'noviembre',
            'December': 'diciembre'
        }
        
        # Obtener información adicional para el certificado
        # Fecha de ingreso (primera clase del alumno)
        primera_clase = None
        ultima_clase_regular = None
        horario_clase = "8:00 a.m. a 11:00 a.m."  # Horario por defecto
        dias_semana = []
        
        # Buscar clases del alumno a través de su grupo actual
        if alumno.grupo_actual:
            # Filtrar clases excluyendo las de materia 'Simulacro'
            clases = alumno.grupo_actual.clases.all().select_related('materia').order_by('fecha')
            clases_regulares = clases.exclude(materia__nombre__icontains='Simulacro')
            
            if clases_regulares.exists():
                primera_clase = clases_regulares.first()
                ultima_clase_regular = clases_regulares.last()
                
                # Obtener el horario de la última clase regular (no simulacro)
                if ultima_clase_regular and ultima_clase_regular.horario:
                    hora_inicio = ultima_clase_regular.get_hora_inicio()
                    hora_fin = ultima_clase_regular.get_hora_fin()
                    horario_clase = f"{hora_inicio.strftime('%I:%M %p')} a {hora_fin.strftime('%I:%M %p')}"
                
                # Determinar los días de la semana en que asiste
                dias_por_semana = {}
                for clase in clases_regulares:
                    dia_semana = clase.fecha.strftime("%A").lower()
                    dias_por_semana[dia_semana] = True
                
                # Traducir días de la semana al español
                traduccion_dias = {
                    'monday': 'lunes',
                    'tuesday': 'martes',
                    'wednesday': 'miércoles',
                    'thursday': 'jueves',
                    'friday': 'viernes',
                    'saturday': 'sábado',
                    'sunday': 'domingo'
                }
                
                dias_semana = [traduccion_dias.get(dia, dia) for dia in dias_por_semana.keys()]
                
                # Ordenar los días de la semana en orden cronológico
                orden_dias = {'lunes': 1, 'martes': 2, 'miércoles': 3, 'jueves': 4, 'viernes': 5, 'sábado': 6, 'domingo': 7}
                dias_semana.sort(key=lambda x: orden_dias.get(x, 8))
        
        # Calcular duración del curso en meses
        duracion_meses = 3  # Valor por defecto
        if primera_clase and ultima_clase_regular:
            # Calcular diferencia en meses
            meses = (ultima_clase_regular.fecha.year - primera_clase.fecha.year) * 12
            meses += ultima_clase_regular.fecha.month - primera_clase.fecha.month
            if meses > 0:
                duracion_meses = meses
        
        # Diccionario para convertir números a texto en español
        numeros_texto = {
            1: 'uno',
            2: 'dos',
            3: 'tres',
            4: 'cuatro',
            5: 'cinco',
            6: 'seis',
            7: 'siete',
            8: 'ocho',
            9: 'nueve',
            10: 'diez',
            11: 'once',
            12: 'doce'
        }
        
        # Obtener el texto del número de meses
        duracion_meses_texto = numeros_texto.get(duracion_meses, str(duracion_meses))
        
        # Configurar documento
        response = HttpResponse(content_type='application/pdf')
        filename = f"paz_salvo_{alumno.primer_apellido}_{alumno.identificacion}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Justify', alignment=4))
        styles.add(ParagraphStyle(name='Center', alignment=1))
        
        # Contenido
        elements = []
        
        # Logo (opcional)
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img/logo.png')
        if os.path.exists(logo_path):
            elements.append(Image(logo_path, width=2*inch, height=1*inch))
            elements.append(Spacer(1, 20))
        
        # Encabezado
        elements.append(Paragraph('<b>EL PRE ICFES VICTOR VALDEZ</b>', styles['Center']))
        elements.append(Paragraph('<b>NIT: 901.272.598-7</b>', styles['Center']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph('<b>' + '_'*50 + '</b>', styles['Center']))
        elements.append(Paragraph('<b>HACE CONSTAR</b>', styles['Center']))
        elements.append(Paragraph('<b>' + '_'*50 + '</b>', styles['Center']))
        elements.append(Spacer(1, 20))
        
        # Fecha actual formateada
        fecha_actual = timezone.now().date()
        mes_actual_en_ingles = fecha_actual.strftime("%B")
        mes_actual_es = meses_es.get(mes_actual_en_ingles, mes_actual_en_ingles)
        fecha_str = f"{fecha_actual.day} de {mes_actual_es} de {fecha_actual.year}"
        
        # Texto para los días de la semana
        texto_dias = "los días establecidos en el horario"
        if len(dias_semana) > 0:
            # Verificar si asiste de lunes a viernes
            dias_laborables = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']
            if all(dia in dias_semana for dia in dias_laborables) and len(dias_semana) == 5:
                texto_dias = "de lunes a viernes"
            # Verificar si asiste de lunes a sábado
            elif all(dia in dias_semana for dia in dias_laborables + ['sábado']) and len(dias_semana) == 6:
                texto_dias = "de lunes a sábado"
            # Caso especial para sábado
            elif len(dias_semana) == 1 and 'sábado' in dias_semana:
                texto_dias = "los días sábados"
            # Caso especial para domingo
            elif len(dias_semana) == 1 and 'domingo' in dias_semana:
                texto_dias = "los días domingos"
            # Caso para días consecutivos (ej: lunes a miércoles)
            elif len(dias_semana) >= 2:
                # Verificar si los días son consecutivos
                indices = [orden_dias[dia] for dia in dias_semana]
                indices.sort()
                if indices == list(range(min(indices), max(indices) + 1)) and max(indices) - min(indices) + 1 == len(indices):
                    texto_dias = f"de {dias_semana[0]} a {dias_semana[-1]}"
                else:
                    texto_dias = f"los días {', '.join(dias_semana)}"
        
        
        # Mes y año de finalización
        mes_finalizacion = "diciembre"
        anio_finalizacion = fecha_actual.year
        if ultima_clase_regular:
            mes_en_ingles = ultima_clase_regular.fecha.strftime("%B")
            mes_finalizacion = meses_es.get(mes_en_ingles, mes_en_ingles)
            anio_finalizacion = ultima_clase_regular.fecha.year
        
        # Fecha de ingreso
        fecha_ingreso = "la fecha de inscripción"
        if primera_clase:
            dia = primera_clase.fecha.day
            mes_en_ingles = primera_clase.fecha.strftime("%B")
            mes = meses_es.get(mes_en_ingles, mes_en_ingles)
            anio = primera_clase.fecha.year
            fecha_ingreso = f"{dia} de {mes} de {anio}"
        
        # Vamos a crear los párrafos por separado para evitar problemas con ReportLab
        # Párrafo 1
        nombre_completo = f"{alumno.nombres} {alumno.primer_apellido}{(' ' + alumno.segundo_apellido) if alumno.segundo_apellido else ''}"
        parrafo1 = Paragraph(
            f"<para align='justify'>Que <b>{nombre_completo}</b>, "
            f"identificado(a) con {alumno.get_tipo_identificacion_display()} <b>{alumno.identificacion}</b>, "
            f"se encuentra realizando el curso de PRE ICFES, al cual ingresó en modalidad presencial desde el día <b>{fecha_ingreso}</b>.</para>", 
            styles['Justify']
        )
        
        # Párrafo 2
        parrafo2 = Paragraph(
            "<para align='justify'>El curso tiene como objetivo preparar académicamente a la estudiante en las diferentes áreas evaluadas "
            "en el examen de Estado Saber 11, reforzando conocimientos, promoviendo estrategias de aprendizaje, y fortaleciendo "
            "habilidades analíticas para garantizar su desempeño óptimo en dicho examen.</para>",
            styles['Justify']
        )
        
        # Párrafo 3
        parrafo3 = Paragraph(
            f"<para align='justify'>La estudiante asiste regularmente {texto_dias} de <b>{horario_clase}</b>, en modalidad presencial. "
            f"El curso tiene una duración total de <b>{duracion_meses_texto} ({duracion_meses})</b> meses, con fecha de finalización "
            f"prevista para el mes de <b>{mes_finalizacion}</b> de <b>{anio_finalizacion}</b>.</para>",
            styles['Justify']
        )
        
        # Párrafo 4
        parrafo4 = Paragraph(
            "<para align='justify'>La estudiante ha cumplido con las obligaciones correspondientes, y se encuentra a paz y salvo en su totalidad de curso, "
            "incluyendo las responsabilidades administrativas y financieras requeridas para su participación en el programa académico.</para>",
            styles['Justify']
        )
        
        # Línea separadora
        linea1 = Paragraph(f"<para align='justify'><b>{'_'*50}</b></para>", styles['Justify'])
        
        # Párrafo 5
        parrafo5 = Paragraph(
            f"<para align='justify'>Para mayor constancia, se firma y se sella el presente documento a los {fecha_actual.day} días "
            f"del mes de {mes_actual_es} de {fecha_actual.year}.</para>",
            styles['Justify']
        )
        
        # Línea separadora final
        linea2 = Paragraph(f"<para align='justify'><b>{'_'*50}</b></para>", styles['Justify'])
        
        # Añadir todos los elementos al documento
        elements.append(parrafo1)
        elements.append(Spacer(1, 10))
        elements.append(parrafo2)
        elements.append(Spacer(1, 10))
        elements.append(parrafo3)
        elements.append(Spacer(1, 10))
        elements.append(parrafo4)
        elements.append(Spacer(1, 15))
        elements.append(linea1)
        elements.append(Spacer(1, 10))
        elements.append(parrafo5)
        elements.append(Spacer(1, 10))
        elements.append(linea2)
        elements.append(Spacer(1, 30))
        
        # Firma del usuario que genera el documento
        nombre_completo = f"{request.user.first_name} {request.user.last_name}"
        if not nombre_completo.strip():
            nombre_completo = request.user.username
            
        telefono = request.user.telefono if hasattr(request.user, 'telefono') and request.user.telefono else ""
        
        # Buscar si el usuario tiene una firma digital registrada
        try:
            firma = Firma.objects.get(usuario=request.user)
            # Si tiene firma digital, agregarla al documento
            if firma.imagen and os.path.exists(firma.imagen.path):
                print(f"Firma encontrada: {firma.imagen.path}")
                # Agregar la imagen de la firma
                firma_img = Image(firma.imagen.path)
                # Ajustar el tamaño de la imagen para que se vea bien en el PDF
                firma_img.drawHeight = 1.2*inch
                firma_img.drawWidth = 2.5*inch
                elements.append(firma_img)
                elements.append(Spacer(1, 5))
            else:
                # Si no tiene imagen de firma, mostrar la línea
                elements.append(Paragraph("___________________________________________", styles['Center']))
        except Firma.DoesNotExist:
            # Si no tiene firma registrada, mostrar la línea
            elements.append(Paragraph("___________________________________________", styles['Center']))
        
        # Agregar el nombre y cargo
        elements.append(Paragraph(f"<b>{nombre_completo}</b>", styles['Center']))
        elements.append(Paragraph("Jefe de Cartera del Pre ICFES", styles['Center']))
            
        if telefono:
            elements.append(Paragraph(f"Cel.: {telefono}", styles['Center']))
        elements.append(Paragraph("VALDEZ Y ANDRADE SOLUCIONES S.A.S", styles['Center']))
        elements.append(Paragraph("NIT: 901.272.598-7", styles['Center']))
        
        elements.append(Spacer(1, 30))
        
        # Pie de página
        elements.append(Paragraph("VALDEZ Y ANDRADE SOLUCIONES S.A.S NIT 901.272.598 - 7", styles['Center']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("CRA. 60A # 29 - 47 BARRIO LOS ANGELES", styles['Center']))
        
        # Generar PDF
        doc.build(elements)
        return response


class ProximosPagosListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    model = Cuota
    template_name = 'cartera/proximos_pagos_list.html'
    context_object_name = 'cuotas'
    paginate_by = 2

    def get_queryset(self):
        queryset = super().get_queryset().filter(
            estado='emitida',
            fecha_vencimiento__gte=timezone.now().date()
        ).select_related('deuda', 'deuda__alumno')

        # Aplicar filtros
        dias_filtro = self.request.GET.get('dias_filtro', 'todos')
        identificacion = self.request.GET.get('identificacion', '')
        apellido = self.request.GET.get('apellido', '')

        if dias_filtro != 'todos':
            dias = dias_filtro.split('-')
            if len(dias) == 1:  # Caso de '90+'
                queryset = queryset.filter(
                    fecha_vencimiento__lte=timezone.now().date() + timedelta(days=int(dias[0]))
                )
            else:
                min_dias = int(dias[0])
                max_dias = int(dias[1])
                queryset = queryset.filter(
                    fecha_vencimiento__gte=timezone.now().date() + timedelta(days=min_dias),
                    fecha_vencimiento__lte=timezone.now().date() + timedelta(days=max_dias)
                )

        if identificacion:
            queryset = queryset.filter(deuda__alumno__identificacion__icontains=identificacion)

        if apellido:
            queryset = queryset.filter(
                Q(deuda__alumno__primer_apellido__icontains=apellido) |
                Q(deuda__alumno__segundo_apellido__icontains=apellido)
            )

        queryset = queryset.annotate(
            dias_restantes=ExpressionWrapper(
                F('fecha_vencimiento') - timezone.now().date(),
                output_field=fields.IntegerField()
            )
        ).order_by('dias_restantes')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Agregar el mensaje preformateado y días restantes a cada cuota
        for cuota in context['cuotas']:
            alumno = cuota.deuda.alumno
            
            # Renderizar el mensaje con los datos actuales
            message_context = {
                'nombres': alumno.nombres,
                'primer_apellido': alumno.primer_apellido,
                'fecha_vencimiento': cuota.fecha_vencimiento,
                'dias_restantes': (cuota.fecha_vencimiento - timezone.localtime(timezone.now()).date()).days,
                'monto': cuota.monto
            }
            
            # Renderizar el template y codificar para URL
            cuota.whatsapp_message = render_to_string(
                'cartera/proximo_pago_template.txt',
                message_context
            ).replace('\n', '%0A').replace(' ', '%20')
        
        for cuota in context['cuotas']:
            cuota.dias_restantes = (cuota.fecha_vencimiento - timezone.now().date()).days
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
        
        return context


class ReciboPDFView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser or 'SecretariaCartera' in self.request.user.groups.all().values_list('name', flat=True)

    def handle_no_permission(self):
        return HttpResponseForbidden("No tienes permisos para acceder a esta página.")

    def get(self, request, pk):
        cuota = get_object_or_404(Cuota, pk=pk)
        
        # Crear el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="recibo_{cuota.id}.pdf"'
        
        # Configurar el documento
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=1))
        
        # Contenido
        elements = []
        
        # Logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img/logo.png')
        if os.path.exists(logo_path):
            elements.append(Image(logo_path, width=2*inch, height=1*inch))
        
        # Títulos
        elements.append(Paragraph('<b>PRE-ICFES VICTOR VALDEZ</b>', styles['Center']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph('<b>RECIBO DE PAGO</b>', styles['Center']))
        elements.append(Spacer(1, 30))
        
        # Datos del recibo
        data = [
            ['Nombres:', f'{cuota.deuda.alumno.nombres}'],
            ['Primer Apellido:', f'{cuota.deuda.alumno.primer_apellido}'],
            ['Segundo Apellido:', f'{cuota.deuda.alumno.segundo_apellido}'],
            ['Tipo de Identificación:', f'{dict(Alumno.TIPO_IDENTIFICACION)[cuota.deuda.alumno.tipo_identificacion]}'],
            ['Identificación:', f'{cuota.deuda.alumno.identificacion}'],
            ['Fecha de Vencimiento:', f'{cuota.fecha_vencimiento.strftime("%d/%m/%Y")}'],
            ['Fecha Actual:', f'{timezone.now().strftime("%d/%m/%Y")}'],
            ['Monto Abonado:', f'${cuota.monto_abonado:.1f}'],
            ['Método de Pago:', f'{cuota.metodo_pago}'],
            ['Saldo Pendiente:', f'${cuota.deuda.saldo_pendiente:.1f}'],
            ['Valor de la Deuda:', f'${cuota.deuda.valor_total:.1f}']
        ]
        
        # Tabla de datos
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONT', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(table)
        elements.append(Spacer(1, 30))
        elements.append(Spacer(1, 30))
        
        # Líneas para firmas
        elements.append(Paragraph('__________________________', styles['Normal']))
        elements.append(Paragraph('Firma del Alumno', styles['Normal']))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph('__________________________', styles['Normal']))
        elements.append(Paragraph('Firma Acudiente', styles['Normal']))
        elements.append(Spacer(1, 20))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph('__________________________', styles['Normal']))
        elements.append(Paragraph('Firma de la Secretaria Cartera', styles['Normal']))
        
        # Construir el PDF
        doc.build(elements)
        
        return response


class InformeDiarioView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    def test_func(self):
        # Solo permitir acceso a superusers y secretarias de cartera
        return self.request.user.is_superuser or self.request.user.groups.filter(name='SecretariaCartera').exists()
    template_name = 'cartera/informe_diario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha_servidor = timezone.localtime(timezone.now()).date()
        hoy = timezone.now()
        
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
        
        # Datos de recaudación del día
        cuotas_hoy = cuotas_qs.filter(
            fecha_vencimiento=hoy,
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
        
        # Objetivo del mes
        mes_actual = hoy.month
        anio_actual = hoy.year
        
        # Calcular el objetivo del mes como la suma de todas las cuotas con vencimiento en el mes actual
        context['objetivo_mes'] = cuotas_qs.filter(
            fecha_vencimiento__month=mes_actual,
            fecha_vencimiento__year=anio_actual
        ).aggregate(Sum('monto'))['monto__sum'] or 0
        
        # % de cumplimiento
        recaudado_mes = cuotas_qs.filter(
            fecha_vencimiento__month=mes_actual,
            fecha_vencimiento__year=anio_actual,
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
        if municipio_id:
            todas_cuotas_qs = todas_cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio_id=municipio_id
            )
        elif not self.request.user.is_superuser:
            todas_cuotas_qs = todas_cuotas_qs.filter(
                deuda__alumno__grupo_actual__salon__sede__municipio=self.request.user.municipio
            )
        
        # Valor total de cartera (suma de todos los montos de cuotas)
        context['valor_cartera'] = todas_cuotas_qs.aggregate(Sum('monto'))['monto__sum'] or 0
        
        # Total cobrado (suma de todos los montos_abonados)
        context['cobrado'] = todas_cuotas_qs.aggregate(Sum('monto_abonado'))['monto_abonado__sum'] or 0
        
        # Falta por cobrar
        context['falta_cobrar'] = context['valor_cartera'] - context['cobrado']
        
        # Fecha formateada
        context['fecha_actual'] = date_format(
            fecha_servidor, 
            "l, j \d\e F \d\e Y"
        ).capitalize()
        
        return context

def generar_pdf_informe(request):
    if request.method == 'POST':
        # Función simple para formatear valores como moneda
        def format_currency(value):
            try:
                # Convertir a float y luego a entero para redondear
                num = int(float(value))
                # Formatear con separadores de miles
                return f"${num:,}".replace(',', '.')
            except (ValueError, TypeError):
                return f"${value}"
        
        # Obtener datos del formulario
        efectivo_sedes = request.POST.get('efectivo_sedes', '0')
        
        # Configurar el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="informe_diario.pdf"'
        
        # Crear el canvas
        p = canvas.Canvas(response, pagesize=letter)
        
        # Obtener fecha formateada
        from django.utils import timezone
        from django.utils.formats import date_format
        hoy = timezone.localtime(timezone.now()).date()
        fecha_str = date_format(hoy, "l, j \d\e F \d\e Y").capitalize()
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, "Informe Diario de Cartera")
        p.setFont("Helvetica", 12)
        p.drawString(100, 730, fecha_str)
        
        # Resto del código para el PDF...
        
        
        # Datos de recaudación
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 700, "Recaudación del Día")
        p.setFont("Helvetica", 12)
        
        y_position = 680
        datos = [
            ("Efectivo:", format_currency(request.POST.get('recaudo_efectivo', '0'))),
            ("Transferencia:", format_currency(request.POST.get('recaudo_transferencia', '0'))),
            ("Datáfono:", format_currency(request.POST.get('recaudo_datáfono', '0'))),
            ("Total Recaudado:", format_currency(request.POST.get('total_recaudado', '0'))),
            ("Efectivo en sedes:", format_currency(efectivo_sedes))
        ]
        
        for label, value in datos:
            p.drawString(100, y_position, f"{label} {value}")
        y_position -= 20
        
        # Objetivos
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y_position - 20, "Objetivos del Mes")
        p.setFont("Helvetica", 12)
        y_position -= 40
        
        objetivos = [
            ("Objetivo:", format_currency(request.POST.get('objetivo_mes', '0'))),
            ('Recaudado del mes:', format_currency(request.POST.get('recaudado_mes', '0'))),
            ("% Cumplimiento:", f"{request.POST.get('porcentaje_cumplimiento', '0')}%")
        ]
        
        # Dibujar tabla de objetivos
        for label, value in objetivos:
            p.drawString(100, y_position, f"{label} {value}")
            y_position -= 20
        
        # Reporte de cartera
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y_position - 20, "Reporte de Cartera")
        p.setFont("Helvetica", 12)
        y_position -= 40
        
        cartera = [
            ("Valor Cartera:", format_currency(request.POST.get('valor_cartera', '0'))),
            ("Cobrado:", format_currency(request.POST.get('cobrado', '0'))),
            ("Falta por Cobrar:", format_currency(request.POST.get('falta_cobrar', '0')))
        ]
        
        for label, value in cartera:
            p.drawString(100, y_position, f"{label} {value}")
            y_position -= 20
        
        p.showPage()
        p.save()
        
        return response
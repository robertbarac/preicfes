from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.db.models import Count
from datetime import datetime
from calendar import month_name

from academico.models import Clase
from usuarios.models import Usuario


class ClasesProfesorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Clase
    template_name = 'academico/clases_profesor_list.html'
    context_object_name = 'clases'
    login_url = 'login'
    paginate_by = 20  # Paginación de 2 elementos por página

    def test_func(self):
        return (
            self.request.user.is_staff or 
            self.request.user.id == int(self.kwargs.get('profesor_id'))
        )

    def get_queryset(self):
        profesor_id = self.kwargs.get('profesor_id')
        mes = self.request.GET.get('mes', datetime.now().month)
        estado = self.request.GET.get('estado', 'vista')
        año = datetime.now().year

        queryset = Clase.objects.filter(
            profesor_id=profesor_id,
            fecha__year=año,
            fecha__month=mes,
            estado=estado
        ).select_related(
            'materia',
            'salon',
            'salon__sede'  
        ).order_by('fecha', 'horario')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profesor_id = self.kwargs.get('profesor_id')
        mes_actual = int(self.request.GET.get('mes', datetime.now().month))
        estado_actual = self.request.GET.get('estado', 'vista')
        
        profesor = get_object_or_404(Usuario, id=profesor_id)
        materias_profesor = (
            Clase.objects.filter(
                profesor=profesor,
                fecha__year=datetime.now().year,
                fecha__month=mes_actual,
                estado=estado_actual
            )
            .values('materia__nombre')
            .annotate(total=Count('materia'))
            .order_by('-total')
        )
        
        # Calcular puede_registrar_asistencia para cada clase
        clases = context['clases']
        
        for clase in clases:
            clase.puede_registrar = clase.puede_registrar_asistencia(self.request.user)
        
        # Añadir información de paginación al contexto
        if context.get('is_paginated', False):
            paginator = context['paginator']
            page_obj = context['page_obj']
            
            # Obtener el número de página actual
            page_number = page_obj.number
            
            # Calcular el rango de páginas a mostrar
            page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
            context['page_range'] = page_range
            
        context.update({
            'profesor': profesor,
            'meses': [
                {'numero': i, 'nombre': month_name[i]} 
                for i in range(1, 13)
            ],
            'estados_clase': [
                {'valor': 'programada', 'nombre': 'Programadas'},
                {'valor': 'vista', 'nombre': 'Vistas'},
                {'valor': 'cancelada', 'nombre': 'Canceladas'}
            ],
            'mes_actual': mes_actual,
            'estado_actual': estado_actual,
            'año_actual': datetime.now().year,
            'materias_profesor': materias_profesor,
            'titulo': f'Clases {dict(Clase.ESTADO_CLASE).get(estado_actual, "").lower()} de {profesor.get_full_name()} - {month_name[mes_actual]}'
        })
        
        return context
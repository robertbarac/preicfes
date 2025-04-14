from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count

import matplotlib.pyplot as plt
import io
import base64

from academico.models import Grupo, Clase, Materia, Alumno

class GrupoDetailView(LoginRequiredMixin, DetailView):
    model = Grupo
    template_name = 'academico/grupo_detalle.html'
    context_object_name = 'grupo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        grupo = self.get_object()

        # Obtener las clases vistas
        clases_vistas = Clase.objects.filter(
            grupo=grupo,
            estado='vista'
        ).select_related(
            'profesor',
            'materia',
            'salon',
            'salon__sede'
        )

        # Guardar las clases ordenadas por fecha para el template
        context['clases_vistas'] = clases_vistas.order_by('-fecha')

        # Obtener estadísticas de materias
        materias_preicfes = Materia.objects.all()

        frecuencia_materias = (
            clases_vistas.values('materia__nombre')
            .annotate(total=Count('materia'))
            .order_by('materia__nombre')
        )

        frecuencia_dict = {item['materia__nombre']: item['total'] for item in frecuencia_materias}

        materias = [materia.nombre for materia in materias_preicfes]
        totales = [frecuencia_dict.get(materia.nombre, 0) for materia in materias_preicfes]

        plt.figure(figsize=(12, 6))
        bars = plt.bar(materias, totales, color='skyblue')
        plt.xlabel('Materias')
        plt.ylabel('Frecuencia de clases vistas')
        plt.title(f'Frecuencia de materias vistas en clases - Grupo {grupo.codigo}')
        plt.xticks(rotation=45)
        plt.tight_layout()

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',
                    ha='center', va='bottom')

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()

        graphic = base64.b64encode(image_png).decode('utf-8')

        alumnos = Alumno.objects.filter(grupo_actual=grupo)

        context['graphic'] = graphic
        context['alumnos'] = alumnos
        return context
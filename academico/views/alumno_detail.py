from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg

from academico.models import Alumno, Asistencia, Nota
from cartera.models import Deuda

class AlumnoDetailView(LoginRequiredMixin, DetailView):
    model = Alumno
    template_name = 'academico/alumno_detail.html'
    context_object_name = 'alumno'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.get_object()

        # Obtener estadísticas de asistencia
        asistencias = Asistencia.objects.filter(alumno=alumno)
        asistencias_vistas = asistencias.filter(clase__estado='vista')
        
        # Obtener cuotas
        try:
            deuda = alumno.deuda
            cuotas = deuda.cuotas.all()
        except Deuda.DoesNotExist:
            deuda = None
            cuotas = []

        context.update({
            'titulo': f'Detalles de {alumno}',
            'deuda': deuda,
            'saldo_pendiente': deuda.saldo_pendiente if deuda else 0,
            'estado_deuda': deuda.estado if deuda else 'Sin deuda',
            'cuotas': cuotas,
            'asistencias': asistencias_vistas,
            'total_asistencias': asistencias_vistas.count(),
            'asistencias_presente': asistencias_vistas.filter(asistio=True).count(),
            'asistencias_faltas': asistencias_vistas.filter(asistio=False).count(),
            
            # Obtener notas y promedios por materia
            'notas': Nota.objects.filter(alumno=alumno, clase__estado='vista'),
            'promedios_materias': Nota.objects.filter(
                alumno=alumno,
                clase__estado='vista'
            ).values('clase__materia__nombre').annotate(
                promedio=Avg('nota')
            ).order_by('clase__materia__nombre')
        })
        
        return context

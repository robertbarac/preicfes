from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.utils import timezone
from django.template.loader import render_to_string

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
            
            # Agregar mensaje WhatsApp a cada cuota
            for cuota in cuotas:
                # Forzar la actualización del estado de la cuota según la fecha actual
                if cuota.monto_abonado >= cuota.monto:
                    cuota.estado = "pagada"
                elif cuota.monto_abonado > 0:
                    cuota.estado = "pagada_parcial"
                elif timezone.localtime(timezone.now()).date() > cuota.fecha_vencimiento:
                    cuota.estado = "vencida"
                else:
                    cuota.estado = "emitida"
                    
                cuota.dias_atraso = (timezone.localtime(timezone.now()).date() - cuota.fecha_vencimiento).days if cuota.fecha_vencimiento < timezone.localtime(timezone.now()).date() else 0
                
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

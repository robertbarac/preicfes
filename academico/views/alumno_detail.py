from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.utils import timezone
import json
from django.template.loader import render_to_string

from academico.models import Alumno, Asistencia, Nota, Inasistencia
from cartera.models import Deuda, AcuerdoPago

class AlumnoDetailView(LoginRequiredMixin, DetailView):
    model = Alumno
    template_name = 'academico/alumno_detail.html'
    context_object_name = 'alumno'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        alumno = self.get_object()
        user = self.request.user

        # Flags de permisos para simplificar la lógica en la plantilla
        can_view_academic = user.is_superuser or user.groups.filter(name__in=['SecretariaAcademica', 'CoordinadorDepartamental', 'Auxiliar']).exists()
        can_view_cartera = user.is_superuser or user.groups.filter(name__in=['SecretariaCartera', 'CoordinadorDepartamental', 'Auxiliar']).exists()

        # Flags de permisos específicos para acciones
        context['can_add_cuota'] = user.has_perm('cartera.add_cuota')
        context['can_change_deuda'] = user.has_perm('cartera.change_deuda')
        context['is_manager'] = user.is_superuser or user.groups.filter(name__in=['CoordinadorDepartamental', 'Auxiliar']).exists()

        context['can_view_academic_history'] = can_view_academic
        context['can_view_cartera_info'] = can_view_cartera
        

        # Obtener estadísticas de asistencia
        asistencias = Asistencia.objects.filter(alumno=alumno)
        asistencias_vistas = asistencias.filter(clase__estado='vista')
        
        # Obtener cuotas
        try:
            deuda = alumno.deuda
            cuotas = deuda.cuotas.all().order_by('fecha_vencimiento')
            
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
                
                alumno = cuota.deuda.alumno
                
                # Generar mensaje diferente según el estado de la cuota
                if cuota.estado == "emitida":
                    # Para cuotas emitidas (próximos pagos): calcular días restantes
                    cuota.dias_restantes = (cuota.fecha_vencimiento - timezone.localtime(timezone.now()).date()).days
                    
                    # Renderizar el mensaje con los datos actuales
                    message_context = {
                        'nombres': alumno.nombres,
                        'primer_apellido': alumno.primer_apellido,
                        'segundo_apellido': alumno.segundo_apellido,
                        'fecha_vencimiento': cuota.fecha_vencimiento,
                        'dias_restantes': cuota.dias_restantes,
                        'monto': cuota.monto
                    }
                    
                    # Renderizar el template y codificar para URL
                    cuota.whatsapp_message = render_to_string(
                        'cartera/proximo_pago_template.txt',
                        message_context
                    ).replace('\n', '%0A').replace(' ', '%20')
                
                elif cuota.estado == "vencida":
                    # Para cuotas vencidas: calcular días de atraso
                    cuota.dias_atraso = (timezone.localtime(timezone.now()).date() - cuota.fecha_vencimiento).days
                    
                    # Renderizar el mensaje con los datos actuales
                    message_context = {
                        'nombres': alumno.nombres,
                        'primer_apellido': alumno.primer_apellido,
                        'segundo_apellido': alumno.segundo_apellido,
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
            # Preparar datos de acuerdos para JSON
            acuerdos_data = {}
            for cuota in cuotas:
                acuerdos = cuota.acuerdos.all().order_by('-fecha_acuerdo')
                acuerdos_data[cuota.id] = [
                    {
                        'fecha_acuerdo': a.fecha_acuerdo.strftime('%d/%m/%Y'),
                        'fecha_prometida_pago': a.fecha_prometida_pago.strftime('%d/%m/%Y'),
                        'nota': a.nota,
                        'estado': a.get_estado_display(),
                    }
                    for a in acuerdos
                ]

        except Deuda.DoesNotExist:
            deuda = None
            cuotas = []
            acuerdos_data = {}

        context.update({
            'acuerdos_json': json.dumps(acuerdos_data),
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
            ).order_by('clase__materia__nombre'),

            # Crear un diccionario para mapear inasistencias a clases
            'inasistencias_justificadas': {
                inasistencia.clase.id: inasistencia
                for inasistencia in Inasistencia.objects.filter(alumno=alumno)
            }
        })
        
        return context

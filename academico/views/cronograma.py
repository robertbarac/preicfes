from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from datetime import datetime, timedelta

from academico.models import Clase
from ubicaciones.models import Sede, Municipio

class CronogramaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'academico/cronograma.html'
    
    def test_func(self):
        # Verificar si el usuario es superuser o pertenece a los grupos permitidos
        return (
            self.request.user.is_superuser or
            self.request.user.groups.filter(name__in=['SecretariaAcademica', 'SecretariaCartera']).exists()
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener parámetros de filtro
        fecha_str = self.request.GET.get('fecha')
        sede_id = self.request.GET.get('sede')
        tipo_horario = self.request.GET.get('tipo')  # AM o PM
        municipio_id = self.request.GET.get('municipio')
        
        # Convertir 'None' en None para evitar errores de tipo
        if sede_id == 'None':
            sede_id = None
        if municipio_id == 'None':
            municipio_id = None
        if tipo_horario == 'None':
            tipo_horario = None
        
        # Establecer fecha inicial si no se proporciona
        if fecha_str:
            fecha_inicial = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        else:
            fecha_inicial = datetime.now().date()
            # Ajustar a lunes si no lo es
            while fecha_inicial.weekday() != 0:
                fecha_inicial -= timedelta(days=1)
        
        # Calcular rango de fechas (lunes a sábado)
        fechas = []
        for i in range(6):  # 0 = lunes, 5 = sábado
            fecha = fecha_inicial + timedelta(days=i)
            fechas.append(fecha)
        
        # Filtrar sedes según el usuario
        if self.request.user.is_superuser:
            sedes = Sede.objects.all()
            municipios = Municipio.objects.all()
        else:
            # Obtener municipio del usuario (asumiendo que está en el modelo Usuario)
            municipio_usuario = self.request.user.municipio
            sedes = Sede.objects.filter(municipio=municipio_usuario)
            municipios = Municipio.objects.filter(id=municipio_usuario.id)
        
        # Aplicar filtros a las clases
        clases = Clase.objects.filter(fecha__range=[fecha_inicial, fechas[-1]])
        
        if sede_id and sede_id != 'None':
            clases = clases.filter(salon__sede_id=sede_id)
        elif not self.request.user.is_superuser:
            # Si no se selecciona sede, filtrar por municipio del usuario
            clases = clases.filter(salon__sede__municipio=self.request.user.municipio)
        
        if municipio_id and municipio_id != 'None' and self.request.user.is_superuser:
            clases = clases.filter(salon__sede__municipio_id=municipio_id)
        
        if tipo_horario:
            if tipo_horario == 'AM':
                clases = clases.filter(
                    Q(horario__startswith='08:00') |
                    Q(horario__startswith='10:00') |
                    Q(horario__startswith='7:00')
                )
            elif tipo_horario == 'PM':
                clases = clases.filter(horario__startswith='15:00')
        
        # Organizar clases por salón y fecha
        clases_organizadas = {}
        for clase in clases:
            salon_key = clase.salon.id
            if salon_key not in clases_organizadas:
                clases_organizadas[salon_key] = {
                    'salon': clase.salon,
                    'clases': {fecha: [] for fecha in fechas}
                }
            clases_organizadas[salon_key]['clases'][clase.fecha].append(clase)
        
        context.update({
            'fechas': fechas,
            'clases_organizadas': clases_organizadas,
            'sedes': sedes,
            'municipios': municipios,
            'fecha_actual': fecha_inicial,
            'fecha_anterior': fecha_inicial - timedelta(days=7),
            'fecha_siguiente': fecha_inicial + timedelta(days=7),
            'sede_seleccionada': sede_id,
            'municipio_seleccionado': municipio_id,
            'tipo_horario': tipo_horario,
            'puede_editar': self.request.user.is_superuser or 
                          self.request.user.groups.filter(name='SecretariaAcademica').exists()
        })
        
        return context

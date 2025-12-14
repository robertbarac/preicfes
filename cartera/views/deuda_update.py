from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin
from cartera.models import Deuda, Cuota
from django.shortcuts import get_object_or_404
from cartera.utils import generar_fechas_pago
from django.utils import timezone
from datetime import datetime

class DeudaUpdateView(UserPassesTestMixin, UpdateView):
    model = Deuda
    fields = ['valor_total']
    template_name = 'cartera/deuda_form.html'
    
    def test_func(self):
        # Obtener la deuda
        deuda = self.get_object()
        
        # Si el usuario es 'vvgomez', siempre tiene acceso sin restricciones
        if self.request.user.username == 'vvgomez' or self.request.user.username == 'claudia2019':
            return True
        
        # Para otros usuarios, verificar si es superuser o pertenece al grupo SecretariaCartera
        # Y además verificar si la edición está habilitada
        is_admin = self.request.user.is_superuser
        is_in_group = self.request.user.groups.filter(name='SecretariaCartera').exists()
        
        # Solo permitir acceso si es admin o está en el grupo Y la edición está habilitada
        return (is_admin or is_in_group) and deuda.edicion_habilitada
    
    def get_success_url(self):
        return reverse_lazy('alumno_detail', kwargs={'pk': self.object.alumno.id})
    
    def form_valid(self, form):
        # Obtener valores antiguos antes de que el form guarde los cambios
        old_deuda = Deuda.objects.get(pk=self.object.pk)
        old_valor = old_deuda.valor_total
        
        # Guardar la deuda con el nuevo valor total
        response = super().form_valid(form)
        
        new_valor = self.object.valor_total
        tipo_operacion = self.request.POST.get('tipo_operacion')
        
        if tipo_operacion == 'descuento':
            # Caso 2a: Descuento
            # Si el nuevo valor es menor, la diferencia se resta de las cuotas emitidas
            if new_valor < old_valor:
                diff = old_valor - new_valor
                self.aplicar_descuento(diff)
                
        elif tipo_operacion == 'ampliacion':
            # Caso 2b: Ampliación / Extensión
            # Si el nuevo valor es mayor, se generan nuevas cuotas
            if new_valor > old_valor:
                diff = new_valor - old_valor
                nueva_fecha_str = self.request.POST.get('nueva_fecha_culminacion')
                if nueva_fecha_str:
                    self.aplicar_ampliacion(diff, nueva_fecha_str)

        # Actualizar el saldo pendiente y estado después de todas las operaciones
        self.object.actualizar_saldo_y_estado()
        return response

    def aplicar_descuento(self, diff):
        """Resta la diferencia de las cuotas emitidas (las que están por vencer)."""
        cuotas = self.object.cuotas.filter(estado='emitida').order_by('fecha_vencimiento')
        
        for cuota in cuotas:
            if diff <= 0:
                break
            
            if cuota.monto <= diff:
                # La diferencia cubre toda la cuota
                diff -= cuota.monto
                cuota.monto = 0
                cuota.estado = 'pagada' # Se marca como pagada al quedar en 0
                cuota.save()
            else:
                # La diferencia cubre solo una parte
                cuota.monto -= diff
                diff = 0
                cuota.save()

    def aplicar_ampliacion(self, diff, nueva_fecha_str):
        """Extiende la fecha de culminación y genera nuevas cuotas."""
        # Convertir fecha
        try:
            nueva_fecha_culminacion = datetime.strptime(nueva_fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return # O manejar error
            
        alumno = self.object.alumno
        fecha_inicio_nuevas = alumno.fecha_culminacion if alumno.fecha_culminacion else timezone.now().date()
        
        # Actualizar fecha de culminación del alumno
        alumno.fecha_culminacion = nueva_fecha_culminacion
        alumno.save()
        
        # Usar la frecuencia de pago del alumno
        frecuencia = alumno.frecuencia_pago  # El campo que acabamos de agregar
        
        # Generar las fechas y montos
        cuotas_a_crear = generar_fechas_pago(fecha_inicio_nuevas, nueva_fecha_culminacion, frecuencia, diff)
        
        # Crear las nuevas cuotas
        for fecha_vencimiento, monto in cuotas_a_crear:
            Cuota.objects.create(
                deuda=self.object,
                monto=monto,
                fecha_vencimiento=fecha_vencimiento,
                estado='emitida'
            )

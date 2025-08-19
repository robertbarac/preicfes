# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import UpdateView

# Local imports
from cartera.forms import CuotaUpdateForm
from cartera.models import Cuota

class CuotaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Cuota
    form_class = CuotaUpdateForm
    template_name = 'cartera/cuota_update_form.html'
    
    def test_func(self):
        # vvgomez tiene acceso total para editar cualquier cuota.
        if self.request.user.username == 'vvgomez':
            return True
        
        # Para otros usuarios, permitir solo si son staff/superuser Y la cuota no tiene abonos.
        cuota = self.get_object()
        user_is_authorized = self.request.user.is_staff or self.request.user.is_superuser
        cuota_is_editable = cuota.monto_abonado == 0
        return user_is_authorized and cuota_is_editable

    def handle_no_permission(self):
        return redirect('alumnos_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cuota = self.get_object()
        context['alumno'] = cuota.deuda.alumno
        return context

    def form_valid(self, form):
        # Obtenemos la instancia de la cuota sin guardarla aún en la BD
        cuota_actual = form.save(commit=False)

        # Guardado inicial para registrar el abono y actualizar el estado a 'pagada_parcial'
        # Esto usa la lógica por defecto del modelo (run_logic=True)
        cuota_actual.save()

        # Recalculamos el saldo pendiente después del guardado inicial
        saldo_pendiente = cuota_actual.monto - cuota_actual.monto_abonado

        # Caso 1: Hay un saldo pendiente (pago parcial)
        if saldo_pendiente > 0 and cuota_actual.monto_abonado > 0:
            siguiente_cuota = Cuota.objects.filter(
                deuda=cuota_actual.deuda,
                fecha_vencimiento__gt=cuota_actual.fecha_vencimiento,
                estado__in=['emitida', 'pagada_parcial']
            ).order_by('fecha_vencimiento').first()

            if siguiente_cuota:
                siguiente_cuota.monto += saldo_pendiente
                siguiente_cuota.save()  # Guardado normal, la lógica del modelo se encarga

                # Forzamos el estado de la cuota actual a 'pagada' para "cerrarla"
                cuota_actual.estado = 'pagada'
                # Guardamos SIN ejecutar la lógica del modelo para que no revierta el estado
                cuota_actual.save(run_logic=False, update_fields=['estado'])

                messages.success(self.request, f"Pago parcial registrado. Saldo de ${saldo_pendiente:,.2f} transferido a la próxima cuota.")
            else:
                messages.warning(self.request, f"Pago parcial registrado, pero no se encontró próxima cuota para transferir el saldo.")

        # Caso 2: Hay un excedente de pago
        elif saldo_pendiente < 0:
            excedente = -saldo_pendiente  # Convertir a valor positivo
            siguiente_cuota = Cuota.objects.filter(
                deuda=cuota_actual.deuda,
                fecha_vencimiento__gt=cuota_actual.fecha_vencimiento,
                estado__in=['emitida', 'pagada_parcial']
            ).order_by('fecha_vencimiento').first()

            if siguiente_cuota:
                siguiente_cuota.monto -= excedente
                siguiente_cuota.save()
                messages.success(self.request, f"Pago registrado con un excedente de ${excedente:,.2f}, que ha sido acreditado a la próxima cuota.")
            else:
                messages.info(self.request, f"Pago registrado con un excedente de ${excedente:,.2f}. No se encontró una próxima cuota para aplicar el crédito.")

        # Al final, nos aseguramos de que el estado general de la deuda se recalcule
        cuota_actual.deuda.actualizar_saldo_y_estado()

        return redirect(self.get_success_url())

    def get_success_url(self):
        cuota = self.get_object()
        return reverse('alumno_detail', kwargs={'pk': cuota.deuda.alumno.id})
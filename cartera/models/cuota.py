from django.db import models
from django.utils.timezone import now
from .deuda import Deuda

class Cuota(models.Model):
    ESTADO_CUOTA = [
        ('emitida', 'Emitida'),
        ('pagada_parcial', 'Pagada Parcial'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
    ]

    METODO_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('datáfono', 'Datáfono'),
    ]

    deuda = models.ForeignKey('Deuda', on_delete=models.CASCADE, related_name="cuotas")
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto total de la cuota.")
    monto_abonado = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monto abonado hasta la fecha.")
    fecha_vencimiento = models.DateField(help_text="Fecha de vencimiento de la cuota.")
    fecha_pago = models.DateField(blank=True, null=True, help_text="Fecha en que se realizó el pago efectivamente.")
    estado = models.CharField(max_length=20, choices=ESTADO_CUOTA, default='emitida', help_text="Estado actual de la cuota.")
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO, blank=True, null=True, help_text="Método de pago utilizado.")

    def __str__(self):
        return f"Cuota de {self.monto} - {self.estado} (Vence: {self.fecha_vencimiento})"

    def actualizar_estado(self):
        """Cambia el estado de la cuota según el monto abonado y la fecha de vencimiento."""
        if self.monto_abonado >= self.monto:
            self.estado = "pagada"
        elif self.monto_abonado > 0:
            self.estado = "pagada_parcial"
        elif now().date() > self.fecha_vencimiento:
            self.estado = "vencida"
        else:
            self.estado = "emitida"

    def save(self, *args, **kwargs):
        """Antes de guardar, actualiza el estado de la cuota y el saldo de la deuda."""
        # Si se está realizando un pago y no hay fecha_pago registrada, establecerla ahora
        if self.monto_abonado > 0 and not self.fecha_pago:
            self.fecha_pago = now().date()
            
        self.actualizar_estado()
        super().save(*args, **kwargs)
        self.deuda.actualizar_saldo_y_estado()

    def delete(self, *args, **kwargs):
        """Si se elimina una cuota, se recalcula el saldo pendiente de la deuda."""
        super().delete(*args, **kwargs)
        self.deuda.actualizar_saldo_y_estado()

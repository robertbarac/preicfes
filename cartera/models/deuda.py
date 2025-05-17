from django.db import models
from academico.models import Alumno

class Deuda(models.Model):
    ESTADO_DEUDA = [
        ('emitida', 'Emitida'),
        ('pagada', 'Pagada'),
    ]

    alumno = models.OneToOneField(Alumno, on_delete=models.CASCADE, related_name="deuda")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor total de la deuda.")
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Saldo pendiente de la deuda.")
    fecha_creacion = models.DateTimeField(auto_now_add=True, help_text="Fecha de creación de la deuda.")
    estado = models.CharField(max_length=20, choices=ESTADO_DEUDA, default='emitida', help_text="Estado actual de la deuda.")

    def __str__(self):
        return str(f"Deuda de {self.alumno} - {self.estado}")

    def actualizar_saldo_y_estado(self):
        """Recalcula el saldo pendiente y actualiza el estado de la deuda."""
        total_abonado = self.cuotas.aggregate(models.Sum('monto_abonado'))['monto_abonado__sum'] or 0
        self.saldo_pendiente = self.valor_total - total_abonado

        # Actualizar estado
        if self.saldo_pendiente <= 0:
            self.saldo_pendiente = 0  # Asegurar que no quede negativo
            self.estado = "pagada"
        else:
            self.estado = "emitida"

        self.save(update_fields=['saldo_pendiente', 'estado'])
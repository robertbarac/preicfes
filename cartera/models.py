from django.db import models
from academico.models import Alumno
from ubicaciones.models import Sede
from django.utils.timezone import now


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

    deuda = models.ForeignKey(Deuda, on_delete=models.CASCADE, related_name="cuotas")
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto total de la cuota.")
    monto_abonado = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monto abonado hasta la fecha.")
    fecha_vencimiento = models.DateField(help_text="Fecha de vencimiento de la cuota.")
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
        self.actualizar_estado()
        super().save(*args, **kwargs)
        self.deuda.actualizar_saldo_y_estado()

    def delete(self, *args, **kwargs):
        """Si se elimina una cuota, se recalcula el saldo pendiente de la deuda."""
        super().delete(*args, **kwargs)
        self.deuda.actualizar_saldo_y_estado()


class HistorialModificacion(models.Model):
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.SET_NULL, null=True)
    deuda = models.ForeignKey(Deuda, on_delete=models.CASCADE, related_name="modificaciones")
    fecha_modificacion = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    def __str__(self):
        return f"Modificación en deuda {self.deuda} por {self.usuario} - {self.fecha_modificacion}"


class Recibo(models.Model):
    cuota = models.ForeignKey(Cuota, on_delete=models.CASCADE, related_name="recibos")
    numero_recibo = models.CharField(max_length=20, unique=True, help_text="Número único del recibo.")
    fecha_emision = models.DateTimeField(auto_now_add=True, help_text="Fecha de emisión del recibo.")
    monto_abonado = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto abonado en este recibo.")
    metodo_pago = models.CharField(max_length=20, choices=Cuota.METODO_PAGO, help_text="Método de pago utilizado.")

    def __str__(self):
        return f"Recibo {self.numero_recibo} para {self.cuota}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.cuota.agregar_abono(self.monto_abonado, self.metodo_pago)


class Egreso(models.Model):
    ESTADO_EGRESO = [
        ('publicado', 'Publicado'),
        ('pagado', 'Pagado'),
    ]

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name="egresos")
    fecha = models.DateTimeField()  # Cambiado a DateTimeField
    concepto = models.CharField(max_length=100)
    contratista = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_EGRESO, default='publicado')

    def __str__(self):
        return f"Egreso de {self.concepto} - {self.estado}"


class MetaRecaudo(models.Model):
    MES_CHOICES = [
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ]

    mes = models.IntegerField(choices=MES_CHOICES)
    anio = models.IntegerField()
    valor_meta = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('mes', 'anio')
        ordering = ['-anio', 'mes']

    def __str__(self):
        return f"Meta {self.get_mes_display()} {self.anio} - ${self.valor_meta:.1f}"

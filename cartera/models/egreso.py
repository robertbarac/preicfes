from django.db import models
from ubicaciones.models import Sede, Municipio


class Egreso(models.Model):
    ESTADO_EGRESO = [
        ('publicado', 'Publicado'),
        ('pagado', 'Pagado'),
    ]

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name="egresos")
    municipio = models.ForeignKey('ubicaciones.Municipio', on_delete=models.CASCADE, related_name="egresos", null=True, blank=True)
    fecha = models.DateTimeField()  # Cambiado a DateTimeField
    concepto = models.CharField(max_length=100)
    contratista = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_EGRESO, default='publicado')
    
    def save(self, *args, **kwargs):
        # Si no se ha especificado un municipio, usar el municipio de la sede
        if not self.municipio and self.sede and self.sede.municipio:
            self.municipio = self.sede.municipio
        # Si aún no hay municipio, intentar establecer Cartagena como predeterminado
        if not self.municipio:
            from ubicaciones.models import Municipio
            try:
                self.municipio = Municipio.objects.get(nombre='Cartagena')
            except Municipio.DoesNotExist:
                pass  # Si no existe Cartagena, dejarlo como None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Egreso de {self.concepto} - {self.estado}"

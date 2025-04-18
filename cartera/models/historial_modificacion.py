from django.db import models
from .deuda import Deuda

class HistorialModificacion(models.Model):
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.SET_NULL, null=True)
    deuda = models.ForeignKey('Deuda', on_delete=models.CASCADE, related_name="modificaciones")
    fecha_modificacion = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    def __str__(self):
        return f"Modificación en deuda {self.deuda} por {self.usuario} - {self.fecha_modificacion}"
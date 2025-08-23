from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from ubicaciones.models import Municipio, Departamento
import re
from django.conf import settings
import os

class Usuario(AbstractUser):
    telefono = models.CharField(max_length=20, blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True, null=True, unique=True)
    municipio = models.ForeignKey(
        Municipio, 
        on_delete=models.SET_NULL, 
        related_name='usuarios', 
        blank=True, 
        null=True
    )
    departamento = models.ForeignKey(
        Departamento, 
        on_delete=models.SET_NULL, 
        related_name='usuarios', 
        blank=True, 
        null=True
    )

    def __str__(self):
        return f"{self.username} ({self.telefono})"
    
    def clean(self):
        super().clean()
        # Validar cédula
        if self.cedula and not re.match(r'^\d+$', self.cedula):
            raise ValidationError({'cedula': 'La cédula solo debe contener números.'})
        # Validar teléfono
        if self.telefono and not re.match(r'^\+\d+$', self.telefono):
            raise ValidationError({'telefono': 'El teléfono debe incluir el código de país (ej: +57).'})


def firma_upload_path(instance, filename):
    """Define la ruta donde se guardarán las firmas (ahora en media/firmas/)"""
    ext = filename.split('.')[-1]
    filename = f"{instance.usuario.username}.{ext}"
    return os.path.join('firmas', filename)  # Elimina 'static/' de la ruta


class Firma(models.Model):
    """Modelo simplificado para almacenar las firmas digitales de los usuarios del staff"""
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='firma')
    imagen = models.ImageField(upload_to=firma_upload_path, help_text="Imagen de la firma digital (preferiblemente PNG con fondo transparente)")
    
    class Meta:
        verbose_name = "Firma"
        verbose_name_plural = "Firmas"
    
    def __str__(self):
        return f"Firma de {self.usuario.get_full_name() or self.usuario.username}"
    
    def clean(self):
        """Validar que solo los usuarios staff puedan tener firma"""
        if not self.usuario.is_staff:
            raise ValidationError({'usuario': 'Solo los usuarios del staff pueden tener firmas registradas.'})
        
        # Validar el formato de la imagen
        if self.imagen:
            ext = self.imagen.name.split('.')[-1].lower()
            if ext not in ['png', 'jpg', 'jpeg']:
                raise ValidationError({'imagen': 'El archivo debe ser una imagen PNG, JPG o JPEG.'})
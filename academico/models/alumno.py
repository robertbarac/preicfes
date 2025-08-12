from django.db import models
from django.core.exceptions import ValidationError
from datetime import date
from ubicaciones.models import Municipio
from . import Grupo  # Importación relativa del modelo Grupo en la misma app


class Alumno(models.Model):
    TIPO_IDENTIFICACION = [
        ('TI', 'Tarjeta de Identidad'),
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
    ]
    
    ESTADO_ALUMNO = [
        ('activo', 'Activo'),
        ('retirado', 'Retirado'),
    ]
    
    TIPO_PROGRAMA = [
        ('pre_privado', 'PreICFES Privado'),
        ('pre_publico', 'PreICFES Público'),
        ('premedico', 'PreMédico'),
        ('formacion_laboral', 'Formación Laboral'),
        ('semillero', 'Semillero de Investigación'),
        ('preicfes_kids', 'PreICFES Kids'),
    ]

    # Campos obligatorios
    nombres = models.CharField(max_length=100)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    identificacion = models.CharField(max_length=20, unique=True, null=True, blank=True)
    tipo_identificacion = models.CharField(max_length=2, choices=TIPO_IDENTIFICACION)
    tipo_programa = models.CharField(
        max_length=20, 
        choices=TIPO_PROGRAMA, 
        default='pre_privado',
        verbose_name="Tipo de Programa",
        help_text="Programa al que pertenece el estudiante"
    )
    es_becado = models.BooleanField(
        default=False,
        verbose_name="¿Es becado?",
        help_text="Marcar si el estudiante tiene beca"
    )

    # Fechas de ingreso y culminación
    fecha_ingreso = models.DateField(
        default=date(2025, 1, 1),
        verbose_name="Fecha de ingreso",
        help_text="Fecha en que el alumno ingresó al preicfes"
    )
    fecha_culminacion = models.DateField(
        default=date(2025, 8, 8),
        verbose_name="Fecha de culminación",
        help_text="Fecha en que el alumno culmina su estancia en el preicfes"
    )
    
    # Campos opcionales (pueden ser null o blank)
    celular = models.CharField(max_length=15, blank=True, null=True)

    # Datos del padre
    nombres_padre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido_padre = models.CharField(max_length=100, blank=True, null=True)
    segundo_apellido_padre = models.CharField(max_length=100, blank=True, null=True)
    celular_padre = models.CharField(max_length=15, blank=True, null=True)

    # Datos de la madre
    nombres_madre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido_madre = models.CharField(max_length=100, blank=True, null=True)
    segundo_apellido_madre = models.CharField(max_length=100, blank=True, null=True)
    celular_madre = models.CharField(max_length=15, blank=True, null=True)

    # Estado del alumno
    estado = models.CharField(
        max_length=10, 
        choices=ESTADO_ALUMNO, 
        default='activo',
        verbose_name="Estado",
        help_text="Estado actual del alumno en el preicfes"
    )
    fecha_retiro = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Fecha de retiro",
        help_text="Fecha en que el alumno se retiró del preicfes"
    )
    
    # Relaciones
    municipio = models.ForeignKey(Municipio, on_delete=models.SET_NULL, null=True, blank=True, related_name="alumnos")
    grupo_actual = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True, related_name="alumnos_actuales")

    def clean(self):
        super().clean()
        if self.grupo_actual and self.municipio:
            if self.grupo_actual.salon.sede.municipio != self.municipio:
                raise ValidationError({'grupo_actual': 'El grupo seleccionado no pertenece al municipio del alumno.'})

    def __str__(self):
        return f"{self.nombres} {self.primer_apellido} ({self.identificacion}) - {self.municipio.nombre if self.municipio else 'Sin municipio'}"

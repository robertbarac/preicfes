from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import time
from ubicaciones.models import Salon
from usuarios.models import Usuario
from ubicaciones.models import Municipio
from datetime import datetime, timedelta
from django.utils import timezone

class Grupo(models.Model):
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="grupos")
    codigo = models.CharField(max_length=12, unique=True, blank=True, help_text="""Regla de código:
                            3 letras de la ciudad + 3 letras de la sede + codigo de 2 numeros + una letra 
                            (opcional por si) hay un salon gemelo""")

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = (
                f"{self.salon.sede.municipio.departamento.nombre[:3]}"  # 3 iniciales del departamento
                f"{self.salon.sede.municipio.nombre[:3]}"  # 3 iniciales de la ciudad
                f"{self.salon.sede.nombre[:3]}"  # 3 iniciales de la sede
                f"{self.id:02d}"  # Número de dos dígitos
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Grupo {self.codigo} - {self.salon.sede.nombre}"

class Alumno(models.Model):
    TIPO_IDENTIFICACION = [
        ('TI', 'Tarjeta de Identidad'),
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
    ]

    # Campos obligatorios
    nombres = models.CharField(max_length=100)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    identificacion = models.CharField(max_length=20, unique=True, null=True, blank=True)
    tipo_identificacion = models.CharField(max_length=2, choices=TIPO_IDENTIFICACION)
    es_becado = models.BooleanField(
        default=False,
        verbose_name="¿Es becado?",
        help_text="Marcar si el estudiante tiene beca"
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

class Materia(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return str(self.nombre)


class Clase(models.Model):
    HORARIOS_DISPONIBLES = [
        ('08:00-10:00', '8:00 AM - 10:00 AM'),
        ('10:00-12:00', '10:00 AM - 12:00 PM'),
        ('15:00-17:00', '3:00 PM - 5:00 PM'),
        ('08:00-12:00', '8:00 AM - 12:00 PM (Medio Simulacro)'),
        ('08:00-17:00', '8:00 AM - 5:00 PM (Simulacro Completo)'),
        ('07:00-14:00', '7:00 AM - 2:00 PM (Jornada Especial Colegios)'),
    ]

    ESTADO_CLASE = [
        ('programada', 'Programada'),
        ('vista', 'Vista'),
        ('cancelada', 'Cancelada'),
    ]

    fecha = models.DateField()
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE, related_name="clases")
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name="clases")
    profesor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="clases",
        limit_choices_to={'groups__name': 'Profesor'},  # Solo usuarios del grupo "Profesor"
    )
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="clases")
    horario = models.CharField(max_length=20, choices=HORARIOS_DISPONIBLES, help_text="Seleccione el horario de la clase.", default=None)
    estado = models.CharField(max_length=20, choices=ESTADO_CLASE, default='programada', help_text="Estado de la clase.")

    def clean(self):
        # Validación 1: El profesor debe pertenecer al grupo "Profesor"
        if not self.profesor.groups.filter(name="Profesor").exists():
            raise ValidationError({'profesor': 'El usuario seleccionado no pertenece al grupo Profesor.'})

        # Validación 2: Evitar superposición de horarios para el mismo salón
        clases_existentes = Clase.objects.filter(
            salon=self.salon,
            fecha=self.fecha,
            horario=self.horario,  # Mismo horario
        ).exclude(id=self.id)  # Excluir la clase actual si ya existe

        if clases_existentes.exists():
            raise ValidationError({'horario': 'El salón ya está ocupado en este horario.'})

        # Validación 3: Evitar superposición de horarios para el mismo profesor
        clases_profesor = Clase.objects.filter(
            profesor=self.profesor,
            fecha=self.fecha,
            horario=self.horario,  # Mismo horario
        ).exclude(id=self.id)  # Excluir la clase actual si ya existe

        if clases_profesor.exists():
            raise ValidationError({'horario': 'El profesor ya tiene una clase en este horario.'})

    def get_hora_inicio(self):
        """Obtiene la hora de inicio como objeto time"""
        hora_str = self.horario.split('-')[0].strip()
        # Asegurar formato HH:MM agregando cero inicial si es necesario
        if len(hora_str.split(':')[0]) == 1:
            hora_str = f'0{hora_str}'
        return datetime.strptime(hora_str, '%H:%M').time()
        
    def get_hora_fin(self):
        """Obtiene la hora de fin como objeto time"""
        hora_str = self.horario.split('-')[1].strip()
        # Asegurar formato HH:MM agregando cero inicial si es necesario
        if len(hora_str.split(':')[0]) == 1:
            hora_str = f'0{hora_str}'
        return datetime.strptime(hora_str, '%H:%M').time()
        
    def get_datetime_fin(self):
        """Combina fecha y hora de fin como datetime aware"""
        return timezone.make_aware(
            datetime.combine(self.fecha, self.get_hora_fin())
        )
    
    def get_datetime_inicio(self):
        """Combina fecha y hora de inicio como datetime aware"""
        return timezone.make_aware(
            datetime.combine(self.fecha, self.get_hora_inicio())
        )
    
    def puede_registrar_asistencia(self, usuario):
        """
        Determina si un usuario puede registrar asistencia
        - Superusuarios y SecretariaAcademica siempre pueden
        - Profesores solo pueden ±5 minutos alrededor de la hora de clase
        
        Args:
            usuario: El usuario que intenta registrar asistencia
        """
        if usuario.is_superuser or usuario.groups.filter(name='SecretariaAcademica').exists():
            return True
            
        if usuario != self.profesor:
            return False
            
        # Para el profesor, verificar el margen de tiempo
        ahora = timezone.localtime(timezone.now())  # Convertir a hora local
        inicio_clase = timezone.localtime(self.get_datetime_inicio())  # Asegurar que esté en hora local
        fin_clase = timezone.localtime(self.get_datetime_fin())  # Hora de fin en local
        margen = timedelta(minutes=5)
        
        # Calcular duración de la clase en horas
        duracion = (fin_clase - inicio_clase).total_seconds() / 3600
        
        
        # Si la clase dura más de 2 horas (simulacros), permitir registro durante toda la clase
        if duracion > 2:
            puede = inicio_clase <= ahora <= fin_clase
        else:
            # Para clases normales, solo permitir ±5 minutos alrededor del inicio
            puede = (inicio_clase - margen) <= ahora <= (inicio_clase + margen)
            
        return puede

    def __str__(self):
        return f"Clase de {self.materia.nombre} - {self.fecha} ({self.get_horario_display()})"



class Nota(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="notas")
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="notas")
    nota = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True,
        validators=[
            MinValueValidator(0),   # Valor mínimo permitido: 0
            MaxValueValidator(100)  # Valor máximo permitido: 100
        ]
    )
    def __str__(self):
        return f"Nota de {self.alumno} en {self.clase}: {self.nota if self.nota is not None else 'Sin nota'}"

class Asistencia(models.Model):
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name="asistencias")
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="asistencias")
    asistio = models.BooleanField(default=False)

    def __str__(self):
        return f"Asistencia de {self.alumno} en {self.clase}: {'Sí' if self.asistio else 'No'}"
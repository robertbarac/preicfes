# ubicaciones/models.py
from django.db import models

class Departamento(models.Model):
    nombre = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=30)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name="ciudades")

    def __str__(self):
        return f"{self.nombre} - {self.departamento.nombre}"

class Sede(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name="sedes")

    def __str__(self):
        return f"{self.nombre} - {self.municipio.nombre}"

class Salon(models.Model):
    numero = models.PositiveIntegerField()
    capacidad_sillas = models.PositiveIntegerField(null=False)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name="salones")

    def __str__(self):
        return f"{self.sede.nombre} - Salón {self.numero}"
    
    

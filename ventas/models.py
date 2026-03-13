from django.db import models

class Vendedor(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

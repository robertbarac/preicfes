from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from cartera.models import Deuda

def is_vvgomez(user):
    """Verifica si el usuario es 'vvgomez'"""
    return user.username == 'vvgomez'

@user_passes_test(is_vvgomez)
def toggle_edicion_deuda(request, pk):
    """
    Vista para habilitar o deshabilitar la edición de una deuda.
    Solo el usuario 'vvgomez' puede realizar esta acción.
    """
    deuda = get_object_or_404(Deuda, pk=pk)
    
    # Cambiar el estado de edición
    deuda.edicion_habilitada = not deuda.edicion_habilitada
    deuda.save(update_fields=['edicion_habilitada'])
    
    # Redirigir a la página de detalle del alumno
    # Usar la URL directa en lugar del namespace para evitar problemas
    return redirect(f'/academico/alumnos/{deuda.alumno.id}/')

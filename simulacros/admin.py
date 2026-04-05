from django.contrib import admin
from .models import Simulacro, ResultadoSimulacro

@admin.register(Simulacro)
class SimulacroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_creacion')
    search_fields = ('nombre',)
    
@admin.register(ResultadoSimulacro)
class ResultadoSimulacroAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'simulacro', 'puntaje_global', 'fecha_realizacion', 'registrador', 'estado')
    list_filter = ('simulacro', 'fecha_realizacion', 'registrador')
    search_fields = ('alumno__first_name', 'alumno__last_name', 'alumno__username', 'simulacro__nombre')

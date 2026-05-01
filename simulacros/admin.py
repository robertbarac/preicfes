from django.contrib import admin
from .models import Simulacro, ResultadoSimulacro, _DEFAULT_COMPONENTES_S1, _DEFAULT_COMPONENTES_S2


@admin.register(Simulacro)
class SimulacroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'mostrar_componentes_s1', 'mostrar_componentes_s2', 'fecha_creacion')
    search_fields = ('nombre',)

    fieldsets = (
        ('Información general', {
            'fields': ('nombre',),
        }),
        ('Sesión 1', {
            'fields': ('soluciones_s1', 'puntos_corte_s1', 'componentes_s1'),
            'description': (
                f'Orden por defecto S1: {_DEFAULT_COMPONENTES_S1}. '
                'Deja vacío ([]) para usar el orden por defecto.'
            ),
        }),
        ('Sesión 2', {
            'fields': ('soluciones_s2', 'puntos_corte_s2', 'componentes_s2'),
            'description': (
                f'Orden por defecto S2: {_DEFAULT_COMPONENTES_S2}. '
                'Deja vacío ([]) para usar el orden por defecto.'
            ),
        }),
    )

    @admin.display(description='Componentes S1')
    def mostrar_componentes_s1(self, obj):
        return ' → '.join(obj.get_componentes_s1())

    @admin.display(description='Componentes S2')
    def mostrar_componentes_s2(self, obj):
        return ' → '.join(obj.get_componentes_s2())


@admin.register(ResultadoSimulacro)
class ResultadoSimulacroAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'get_grupo', 'get_sede', 'get_municipio', 'simulacro', 'puntaje_global', 'fecha_realizacion', 'estado')
    list_filter = (
        'simulacro',
        'fecha_realizacion',
        'alumno__grupo_actual',
        'alumno__grupo_actual__salon__sede',
        'alumno__municipio',
    )
    search_fields = ('alumno__primer_apellido', 'alumno__nombres', 'simulacro__nombre')

    @admin.display(description='Grupo', ordering='alumno__grupo_actual__codigo')
    def get_grupo(self, obj):
        return obj.alumno.grupo_actual

    @admin.display(description='Sede', ordering='alumno__grupo_actual__salon__sede__nombre')
    def get_sede(self, obj):
        return obj.alumno.grupo_actual.salon.sede.nombre

    @admin.display(description='Municipio', ordering='alumno__municipio__nombre')
    def get_municipio(self, obj):
        return obj.alumno.municipio.nombre

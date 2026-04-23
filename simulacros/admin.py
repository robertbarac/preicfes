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
    list_display = ('alumno', 'simulacro', 'puntaje_global', 'fecha_realizacion', 'registrador', 'estado')
    list_filter = ('simulacro', 'fecha_realizacion', 'registrador')
    search_fields = ('alumno__primer_apellido', 'alumno__nombres', 'simulacro__nombre')


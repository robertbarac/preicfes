from django.contrib import admin
from .models import Alumno, Clase, Grupo, Materia, Nota, Asistencia
from ubicaciones.models import Municipio, Salon

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'primer_apellido', 'fecha_nacimiento', 'municipio', 'grupo_actual')  # Agregar fecha_nacimiento
    list_filter = ('municipio', 'grupo_actual', 'fecha_nacimiento')  # Agregar fecha_nacimiento (opcional)
    search_fields = ('nombres', 'primer_apellido', 'identificacion', 'fecha_nacimiento')  # Agregar fecha_nacimiento (opcional)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtrar municipios según el usuario logeado
        if db_field.name == "municipio":
            usuario = request.user
            if not usuario.is_superuser and usuario.municipio:
                # Mostrar solo el municipio del usuario
                kwargs["queryset"] = Municipio.objects.filter(id=usuario.municipio.id)
            else:
                # Mostrar todos los municipios si es superusuario
                kwargs["queryset"] = Municipio.objects.all()

        # Filtrar grupos según el municipio del alumno
        if db_field.name == "grupo_actual":
            alumno_id = request.resolver_match.kwargs.get('object_id')
            if alumno_id:
                alumno = Alumno.objects.get(id=alumno_id)
                if alumno.municipio:
                    # Filtrar grupos por el municipio del alumno
                    kwargs["queryset"] = Grupo.objects.filter(salon__sede__municipio=alumno.municipio)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# admin.site.register(Alumno, AlumnoAdmin)

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'salon')
    list_filter = ('salon', 'salon__sede__municipio')
    search_fields = ('codigo', 'salon__numero')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "salon":
            # Obtener el usuario logeado
            usuario = request.user

            # Filtrar salones por ciudad si el usuario no es superusuario
            if not usuario.is_superuser and usuario.municipio:
                kwargs["queryset"] = Salon.objects.filter(
                    sede__municipio=usuario.municipio
                ).order_by('numero')  # Ordenar por nombre del salón
            else:
                # Mostrar todos los salones si el usuario es superusuario
                kwargs["queryset"] = Salon.objects.order_by('numero')  # Ordenar por nombre del salón

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('materia', 'fecha', 'horario', 'salon', 'profesor', 'grupo')
    list_filter = ('fecha', 'horario', 'salon', 'materia', 'grupo__salon__sede', 'profesor', 'grupo__salon__sede__municipio')
    search_fields = ('materia__nombre', 'profesor__username', 'grupo__codigo')



@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    # Campos que se mostrarán en la lista de registros
    list_display = ('alumno', 'clase', 'nota')
    
    # Filtros laterales
    list_filter = ('clase', 'alumno')
    
    list_editable = ('nota',)
    
    # Campos de búsqueda
    search_fields = ('alumno__nombres', 'alumno__primer_apellido', 'clase__materia__nombre')
    
    # Orden por defecto
    ordering = ('clase', 'alumno')

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    # ... (configuraciones anteriores)
    list_display = ('clase', 'alumno', 'asistio')
    list_editable = ('asistio',)
    # Acciones personalizadas
    actions = ['marcar_asistio', 'marcar_no_asistio']

    def marcar_asistio(self, request, queryset):
        queryset.update(asistio=True)
    marcar_asistio.short_description = "Marcar como asistió"

    def marcar_no_asistio(self, request, queryset):
        queryset.update(asistio=False)
    marcar_no_asistio.short_description = "Marcar como no asistió"
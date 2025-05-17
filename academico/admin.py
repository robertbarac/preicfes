from django.contrib import admin
from .models import Alumno, Clase, Grupo, Materia, Nota, Asistencia
from ubicaciones.models import Municipio, Salon

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'primer_apellido', 'segundo_apellido', 'tipo_programa', 'fecha_nacimiento', 'municipio', 'grupo_actual')  # Incluir segundo_apellido
    list_filter = ('tipo_programa', 'municipio', 'grupo_actual', 'fecha_nacimiento', 'es_becado')  # Agregar tipo_programa y es_becado
    search_fields = ('grupo_actual__codigo', 'nombres', 'primer_apellido', 'segundo_apellido', 'identificacion', 'fecha_nacimiento')  # Incluir segundo_apellido
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('municipio', 'grupo_actual')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(municipio=request.user.municipio)
        return queryset

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
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('salon', 'salon__sede', 'salon__sede__municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(salon__sede__municipio=request.user.municipio)
        return queryset

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
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('grupo', 'grupo__salon', 'grupo__salon__sede', 'grupo__salon__sede__municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(grupo__salon__sede__municipio=request.user.municipio)
        return queryset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            if db_field.name == "grupo":
                kwargs["queryset"] = Grupo.objects.filter(salon__sede__municipio=request.user.municipio)
            elif db_field.name == "salon":
                kwargs["queryset"] = Salon.objects.filter(sede__municipio=request.user.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)



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
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('alumno', 'clase', 'alumno__municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(alumno__municipio=request.user.municipio)
        return queryset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            if db_field.name == "alumno":
                kwargs["queryset"] = Alumno.objects.filter(municipio=request.user.municipio)
            elif db_field.name == "clase":
                kwargs["queryset"] = Clase.objects.filter(grupo__salon__sede__municipio=request.user.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('clase', 'alumno', 'asistio')
    list_editable = ('asistio',)
    list_filter = ('asistio', 'clase__fecha')
    search_fields = ('alumno__nombres', 'alumno__primer_apellido', 'clase__materia__nombre')
    # Acciones personalizadas
    actions = ['marcar_asistio', 'marcar_no_asistio']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('alumno', 'clase', 'alumno__municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(alumno__municipio=request.user.municipio)
        return queryset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            if db_field.name == "alumno":
                kwargs["queryset"] = Alumno.objects.filter(municipio=request.user.municipio)
            elif db_field.name == "clase":
                kwargs["queryset"] = Clase.objects.filter(grupo__salon__sede__municipio=request.user.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    def marcar_asistio(self, request, queryset):
        queryset.update(asistio=True)
    marcar_asistio.short_description = "Marcar como asistió"
    
    def marcar_no_asistio(self, request, queryset):
        queryset.update(asistio=False)
    marcar_no_asistio.short_description = "Marcar como no asistió"
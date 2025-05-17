from django.contrib import admin
from .models import Cuota, Deuda, Egreso, HistorialModificacion, Recibo, MetaRecaudo, TarifaClase
from ubicaciones.models import Sede
from django.contrib.auth import get_user_model
from django.utils import timezone

Usuario = get_user_model()  # Obtener dinámicamente el modelo de usuario

@admin.register(Cuota)
class CuotaAdmin(admin.ModelAdmin):
    list_display = ('deuda', 'monto', 'monto_abonado', 'fecha_vencimiento', 'estado', 'metodo_pago')
    list_filter = ('estado', 'metodo_pago', 'fecha_vencimiento')
    search_fields = ('deuda__alumno__nombres', 'deuda__alumno__primer_apellido', 'deuda__alumno__municipio__nombre')
    date_hierarchy = 'fecha_vencimiento'
    list_editable = ('monto_abonado', 'estado', 'metodo_pago')  

    fieldsets = (
        ('Información Básica', {
            'fields': ('deuda', 'monto', 'monto_abonado', 'fecha_vencimiento')
        }),
        ('Estado y Método de Pago', {
            'fields': ('estado', 'metodo_pago')
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('deuda__alumno')
        # Si NO es superuser, filtrar por municipio
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(deuda__alumno__grupo_actual__salon__sede__municipio=request.user.municipio)
        return queryset

    def get_form(self, request, obj=None, **kwargs):
        """Filtra las deudas según el municipio del usuario logueado (excepto superusuarios)."""
        form = super().get_form(request, obj, **kwargs)
        # Si NO es superuser, filtrar por municipio
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            form.base_fields['deuda'].queryset = Deuda.objects.filter(
                alumno__grupo_actual__salon__sede__municipio=request.user.municipio
            )
        return form

    class Meta:
        permissions = (
            ('view_grafica', 'Puede ver la gráfica de ingresos y egresos'),
            ('view_abonos_hechos', 'Puede ver los abonos hechos'),
        )

# Registrar otros modelos si es necesario
@admin.register(Deuda)
class DeudaAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'valor_total', 'saldo_pendiente', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('alumno__nombres', 'alumno__primer_apellido')
    date_hierarchy = 'fecha_creacion'

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('alumno', 'alumno__grupo_actual__salon__sede__municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(alumno__grupo_actual__salon__sede__municipio=request.user.municipio)
        return queryset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtrar los alumnos disponibles en el formulario según el municipio del usuario
        if db_field.name == 'alumno' and not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            from academico.models import Alumno
            kwargs["queryset"] = Alumno.objects.filter(grupo_actual__salon__sede__municipio=request.user.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# @admin.register(Recibo)
# class ReciboAdmin(admin.ModelAdmin):
#     list_display = ('cuota', 'numero_recibo', 'fecha_emision', 'monto_abonado', 'metodo_pago')
#     list_filter = ('metodo_pago', 'fecha_emision')
#     search_fields = ('cuota__deuda__alumno__nombres', 'cuota__deuda__alumno__primer_apellido')
#     date_hierarchy = 'fecha_emision'

# @admin.register(HistorialModificacion)
# class HistorialModificacionAdmin(admin.ModelAdmin):
#     list_display = ('deuda', 'usuario', 'fecha_modificacion')
#     list_filter = ('fecha_modificacion', 'usuario')
#     search_fields = ('deuda__alumno__nombres', 'deuda__alumno__primer_apellido')
#     date_hierarchy = 'fecha_modificacion'

@admin.register(Egreso)
class EgresosAdmin(admin.ModelAdmin):
    list_display = ('sede', 'municipio', 'get_concepto_display', 'valor', 'estado', 'fecha')
    list_filter = ('estado', 'fecha', 'municipio', 'sede', 'concepto')
    search_fields = ('concepto', 'contratista')
    date_hierarchy = 'fecha'  # Navegación por fechas

    def get_queryset(self, request):
        queryset = super().get_queryset(request).select_related('sede', 'municipio')
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            queryset = queryset.filter(municipio=request.user.municipio)
        return queryset

    def get_concepto_display(self, obj):
        """Mostrar el nombre legible del concepto"""
        return dict(obj.CONCEPTO_CHOICES).get(obj.concepto, obj.concepto)
    get_concepto_display.short_description = 'Concepto'
    
    # Personalizar el formulario de edición
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and hasattr(request.user, 'municipio') and request.user.municipio:
            if db_field.name == "sede":
                # Filtrar sedes por municipio del usuario
                kwargs["queryset"] = Sede.objects.filter(municipio=request.user.municipio)
            elif db_field.name == "municipio":
                # Restringir la selección de municipio al del usuario
                from ubicaciones.models import Municipio
                kwargs["queryset"] = Municipio.objects.filter(id=request.user.municipio.id)
                kwargs["initial"] = request.user.municipio
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(MetaRecaudo)
class MetaRecaudoAdmin(admin.ModelAdmin):
    list_display = ('mes', 'anio', 'valor_meta')
    list_filter = ('anio', 'mes')
    ordering = ('-anio', 'mes')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Al crear una nueva meta
            # Establecer el año actual por defecto
            form.base_fields['anio'].initial = timezone.now().year
            # Establecer el mes actual por defecto
            form.base_fields['mes'].initial = timezone.now().month
        return form


@admin.register(TarifaClase)
class TarifaClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'get_tipo_dia_display', 'get_horario_display', 'valor', 'activa', 'fecha_actualizacion')
    list_filter = ('tipo_dia', 'activa')
    search_fields = ('nombre',)
    list_editable = ('valor', 'activa')
    
    def get_tipo_dia_display(self, obj):
        return dict(obj.DIAS_SEMANA)[obj.tipo_dia]
    get_tipo_dia_display.short_description = 'Día'
    
    def get_horario_display(self, obj):
        if obj.horario:
            return dict(obj.HORARIOS)[obj.horario]
        return 'Cualquier horario'
    get_horario_display.short_description = 'Horario'

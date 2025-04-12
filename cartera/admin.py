from django.contrib import admin
from .models import Cuota, Deuda, Egreso, HistorialModificacion, Recibo, MetaRecaudo
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
        return super().get_queryset(request).select_related('deuda__alumno')

    def get_form(self, request, obj=None, **kwargs):
        """Filtra las deudas según la ciudad del usuario logueado (excepto superusuarios)."""
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if hasattr(request.user, 'municipio') and request.user.municipio:
                form.base_fields['deuda'].queryset = Deuda.objects.filter(
                    alumno__municipio=request.user.municipio
                )
            else:
                form.base_fields['deuda'].queryset = Deuda.objects.all()  # Si el usuario no tiene ciudad, mostrar todas
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

@admin.register(Recibo)
class ReciboAdmin(admin.ModelAdmin):
    list_display = ('cuota', 'numero_recibo', 'fecha_emision', 'monto_abonado', 'metodo_pago')
    list_filter = ('metodo_pago', 'fecha_emision')
    search_fields = ('cuota__deuda__alumno__nombres', 'cuota__deuda__alumno__primer_apellido')
    date_hierarchy = 'fecha_emision'

@admin.register(HistorialModificacion)
class HistorialModificacionAdmin(admin.ModelAdmin):
    list_display = ('deuda', 'usuario', 'fecha_modificacion')
    list_filter = ('fecha_modificacion', 'usuario')
    search_fields = ('deuda__alumno__nombres', 'deuda__alumno__primer_apellido')
    date_hierarchy = 'fecha_modificacion'

@admin.register(Egreso)
class EgresosAdmin(admin.ModelAdmin):
    list_display = ('sede', 'concepto', 'valor', 'estado', 'fecha')
    list_filter = ('estado', 'fecha')
    search_fields = ('concepto', 'contratista')
    date_hierarchy = 'fecha'  # Navegación por fechas

    # Personalizar el formulario de edición
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sede":
            # Filtrar sedes por municipio del usuario (si no es superusuario)
            usuario = request.user
            if not usuario.is_superuser and usuario.municipio:
                kwargs["queryset"] = Sede.objects.filter(municipio=usuario.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

admin.site.register(MetaRecaudo, MetaRecaudoAdmin)
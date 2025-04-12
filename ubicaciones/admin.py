# ubicaciones/admin.py
from django.contrib import admin
from .models import Departamento, Municipio, Sede, Salon

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'departamento')
    search_fields = ('nombre',)
    list_filter = ('departamento',)

@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'municipio')
    search_fields = ('nombre',)
    list_filter = ('municipio__departamento', 'municipio',)
    
    def departamento(self, obj):
        return obj.municipio.departamento
    departamento.admin_order_fied = 'municipio__departamento'
    departamento.short_description = 'Departamento'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser:
            queryset = queryset.filter(municipio=request.user.municipio)
        return queryset

@admin.register(Salon)
class SalonAdmin(admin.ModelAdmin):
    list_display = ('numero', 'sede', 'municipio', 'capacidad_sillas')  
    search_fields = ('numero',)
    list_filter = ('sede__municipio', 'sede',)  # Filtrar por Municipio y Sede

    def municipio(self, obj):
        return obj.sede.municipio  # Mostrar municipio en la lista de salones
    municipio.admin_order_field = 'sede__municipio'  # Permite ordenar por municipio
    municipio.short_description = 'Municipio'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Si no es superuser, filtrar por municipio del usuario
        if not request.user.is_superuser:
            queryset = queryset.filter(sede__municipio=request.user.municipio)
        return queryset
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtrar las sedes disponibles en el formulario según el municipio del usuario
        if db_field.name == 'sede' and not request.user.is_superuser:
            kwargs["queryset"] = Sede.objects.filter(municipio=request.user.municipio)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

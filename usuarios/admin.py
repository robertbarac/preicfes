from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from .models import Usuario, Firma
from ubicaciones.models import Municipio

class UsuarioCreationForm(forms.ModelForm):
    """Formulario para creación de usuarios con control de municipio"""
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ('username', 'email', 'municipio')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and not self.request.user.is_superuser:
            # Restringir municipio al del usuario actual para no superusers
            self.fields['municipio'].queryset = Municipio.objects.filter(id=self.request.user.municipio.id)
            self.fields['municipio'].initial = self.request.user.municipio
            self.fields['municipio'].disabled = True

    def clean_password2(self):
        # Validar que las contraseñas coincidan
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return password2

    def save(self, commit=True):
        # Guardar la contraseña correctamente
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UsuarioChangeForm(forms.ModelForm):
    """Formulario para edición de usuarios con control de municipio"""
    class Meta:
        model = Usuario
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and not self.request.user.is_superuser:
            # Restringir municipio al del usuario actual para no superusers
            self.fields['municipio'].queryset = Municipio.objects.filter(id=self.request.user.municipio.id)
            self.fields['municipio'].initial = self.request.user.municipio
            self.fields['municipio'].disabled = True

class UsuarioAdmin(UserAdmin):
    add_form = UsuarioCreationForm
    form = UsuarioChangeForm
    
    # Campos a mostrar en el listado
    list_display = ('username', 'email', 'municipio', 'is_staff')
    list_filter = ('municipio', 'is_staff', 'is_superuser')
    
    # Camposets para la edición
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información personal', {'fields': ('first_name', 'last_name', 'email', 'cedula', 'telefono')}),
        ('Ubicación', {'fields': ('municipio',)}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'municipio', 'password1', 'password2'),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Inyecta el request en los formularios"""
        if obj is None:
            # Formulario de creación
            kwargs['form'] = self.add_form
            form = super().get_form(request, obj, **kwargs)
            form.request = request
            return form
        else:
            # Formulario de edición
            form = super().get_form(request, obj, **kwargs)
            form.request = request
            return form

    def get_queryset(self, request):
        """Filtra los usuarios visibles según municipio"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(municipio=request.user.municipio)
        return qs

    def save_model(self, request, obj, form, change):
        """Controla la asignación del municipio al guardar"""
        if not request.user.is_superuser and not change:
            # Al crear nuevo usuario, asignar municipio del usuario actual
            obj.municipio = request.user.municipio
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Controla permisos de edición"""
        if obj and not request.user.is_superuser:
            return obj.municipio == request.user.municipio
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Controla permisos de eliminación"""
        if obj and not request.user.is_superuser:
            return obj.municipio == request.user.municipio
        return super().has_delete_permission(request, obj)

admin.site.register(Usuario, UsuarioAdmin)


class FirmaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'preview_firma')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    readonly_fields = ('preview_firma',)
    
    fieldsets = (
        (None, {
            'fields': ('usuario', 'imagen', 'preview_firma')
        }),
    )
    
    def preview_firma(self, obj):
        """Muestra una vista previa de la imagen de la firma"""
        if obj.imagen:
            return format_html('<img src="{}" width="150" height="auto" />', obj.imagen.url)
        return "Sin imagen"
    
    preview_firma.short_description = "Vista previa"
    
    def get_queryset(self, request):
        """Filtra las firmas visibles según permisos"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Si no es superusuario, solo ve las firmas de usuarios de su municipio
            qs = qs.filter(usuario__municipio=request.user.municipio)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtra los usuarios disponibles para asignar firma"""
        if db_field.name == "usuario":
            if not request.user.is_superuser:
                # Si no es superusuario, solo puede asignar firmas a usuarios de su municipio
                kwargs["queryset"] = Usuario.objects.filter(
                    municipio=request.user.municipio,
                    is_staff=True
                )
            else:
                # Si es superusuario, solo puede asignar firmas a usuarios staff
                kwargs["queryset"] = Usuario.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Firma, FirmaAdmin)
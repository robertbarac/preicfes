from django import forms
from .models import Deuda, Cuota, AcuerdoPago
from ubicaciones.models import Departamento, Municipio
from django.core.validators import MinValueValidator

class DeudaForm(forms.ModelForm):
    class Meta:
        model = Deuda
        fields = ['alumno', 'valor_total', 'saldo_pendiente', 'estado']  # Actualizando los campos

class CuotaForm(forms.ModelForm):
    class Meta:
        model = Cuota
        fields = ['deuda', 'monto', 'monto_abonado', 'fecha_vencimiento', 'fecha_pago', 'estado', 'metodo_pago']  # Incluir fecha_pago

class CuotaUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['monto'].disabled = True

    class Meta:
        model = Cuota
        fields = ['monto', 'monto_abonado', 'fecha_pago', 'estado', 'metodo_pago']
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
            'monto_abonado': forms.NumberInput(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
            'fecha_pago': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
            'estado': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
            'metodo_pago': forms.Select(attrs={'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500'}),
        }


class AcuerdoPagoFilterForm(forms.Form):
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all(),
        required=False,
        label="Departamento",
        widget=forms.Select(attrs={'class': 'form-select mt-1 block w-full border border-gray-300 rounded-md shadow-sm'})
    )
    municipio = forms.ModelChoiceField(
        queryset=Municipio.objects.all(),
        required=False,
        label="Municipio",
        widget=forms.Select(attrs={'class': 'form-select mt-1 block w-full border border-gray-300 rounded-md shadow-sm'})
    )
    dias_restantes = forms.IntegerField(
        required=False,
        label="Días Restantes (Exacto)",
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={'class': 'form-input mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm', 'placeholder': 'Ej: 0'})
    )

class GenerarCuotasForm(forms.Form):
    monto_cuota_inicial = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=True,
        label="Monto de la Cuota Inicial",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    fecha_pago_inicial = forms.DateField(
        required=True,
        label="Fecha de Pago de la Cuota Inicial",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    metodo_pago_inicial = forms.ChoiceField(
        choices=Cuota.METODO_PAGO, # Usa la lista del modelo Cuota
        required=True,
        label="Método de Pago de la Cuota Inicial",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    frecuencia = forms.ChoiceField(
        choices=[
            ('semanal', 'Semanal'),
            ('quincenal', 'Quincenal'),
            ('mensual', 'Mensual'),
        ],
        required=True, 
        label="Frecuencia de Pago para Cuotas Restantes", 
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AcuerdoPagoForm(forms.ModelForm):
    class Meta:
        model = AcuerdoPago
        fields = ['fecha_prometida_pago', 'nota']
        widgets = {
            'fecha_prometida_pago': forms.DateInput(
                attrs={'type': 'date', 'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm'}
            ),
            'nota': forms.Textarea(
                attrs={'rows': 3, 'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm'}
            ),
        }

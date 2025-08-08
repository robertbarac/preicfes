from django import forms
from .models import Deuda, Cuota

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


class GenerarCuotasForm(forms.Form):
    FRECUENCIA_CHOICES = (
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    )
    frecuencia = forms.ChoiceField(choices=FRECUENCIA_CHOICES, label="Frecuencia de Pago", widget=forms.Select(attrs={'class': 'form-select'}))

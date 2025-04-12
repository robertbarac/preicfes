from django import forms
from .models import Deuda, Cuota

class DeudaForm(forms.ModelForm):
    class Meta:
        model = Deuda
        fields = ['alumno', 'valor_total', 'saldo_pendiente', 'estado']  # Actualizando los campos

class CuotaForm(forms.ModelForm):
    class Meta:
        model = Cuota
        fields = ['deuda', 'monto', 'monto_abonado', 'fecha_vencimiento', 'estado', 'metodo_pago']  # Asegurarse de que se incluyan los campos necesarios

class CuotaUpdateForm(forms.ModelForm):
    class Meta:
        model = Cuota
        fields = ['monto', 'monto_abonado', 'fecha_vencimiento', 'estado', 'metodo_pago']

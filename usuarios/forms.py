from django import forms
from django.utils import timezone

class CertificadoTrabajoForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text="Fecha en que el profesor comenzó a trabajar en el PreICFES"
    )
    
    fecha_fin = forms.DateField(
        label="Fecha de finalización",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text="Fecha en que el profesor finalizó o finalizará su trabajo en el PreICFES"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            # Verificar que la fecha de inicio sea anterior a la fecha de fin
            if fecha_inicio > fecha_fin:
                raise forms.ValidationError("La fecha de inicio debe ser anterior a la fecha de finalización")
        
        return cleaned_data

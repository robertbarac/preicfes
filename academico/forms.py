from django import forms
from .models import Alumno

class AlumnoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases base a todos los campos
        for field_name, field in self.fields.items():
            # Clases base para todos los inputs
            base_classes = 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            
            # Añadir clases específicas según el tipo de campo
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.NumberInput)):
                field.widget.attrs.update({'class': f'{base_classes}'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': f'{base_classes} py-2'})
            elif isinstance(field.widget, forms.DateInput):
                field.widget.attrs.update({
                    'class': f'{base_classes}',
                    'type': 'date'
                })
            
            # Mejorar los placeholders
            if field_name in ['celular', 'celular_padre', 'celular_madre']:
                field.widget.attrs['placeholder'] = '3XX XXX XXXX'
            elif 'nombres' in field_name:
                field.widget.attrs['placeholder'] = 'Ingrese los nombres'
            elif 'apellido' in field_name:
                field.widget.attrs['placeholder'] = 'Ingrese el apellido'
            elif field_name == 'identificacion':
                field.widget.attrs['placeholder'] = 'Número de identificación'

    class Meta:
        model = Alumno
        fields = [
            'nombres', 'primer_apellido', 'segundo_apellido',
            'fecha_nacimiento', 'identificacion', 'tipo_identificacion',
            'celular', 
            'nombres_padre', 'primer_apellido_padre', 'segundo_apellido_padre', 'celular_padre',
            'nombres_madre', 'primer_apellido_madre', 'segundo_apellido_madre', 'celular_madre',
            'municipio', 'grupo_actual'
        ]
        
        help_texts = {
            'celular': 'Número de celular del estudiante',
            'celular_padre': 'Número de celular del padre',
            'celular_madre': 'Número de celular de la madre',
            'fecha_nacimiento': 'Fecha de nacimiento del estudiante',
            'identificacion': 'Número de documento de identidad',
            'municipio': 'Ciudad de residencia',
            'grupo_actual': 'Grupo al que pertenece el estudiante'
        }

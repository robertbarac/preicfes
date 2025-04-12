# Generated by Django 5.1.3 on 2025-02-20 16:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='alumno',
            name='grupo_actual',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alumnos_actuales', to='academico.grupo'),
        ),
        migrations.CreateModel(
            name='Asistencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asistio', models.BooleanField(default=False)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asistencias', to='academico.alumno')),
                ('clase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asistencias', to='academico.clase')),
            ],
        ),
        migrations.CreateModel(
            name='Nota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota', models.DecimalField(decimal_places=2, max_digits=5)),
                ('alumno', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas', to='academico.alumno')),
                ('clase', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas', to='academico.clase')),
            ],
        ),
    ]

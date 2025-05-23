# Generated by Django 5.1.3 on 2025-04-25 00:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0022_alumno_estado_alumno_fecha_retiro'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='clase',
            name='profesor',
            field=models.ForeignKey(blank=True, limit_choices_to={'groups__name': 'Profesor'}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clases', to=settings.AUTH_USER_MODEL),
        ),
    ]

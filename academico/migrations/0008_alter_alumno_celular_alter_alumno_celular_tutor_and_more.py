# Generated by Django 5.1.3 on 2025-02-20 22:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academico', '0007_alter_alumno_celular_alter_alumno_celular_tutor_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alumno',
            name='celular',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='alumno',
            name='celular_tutor',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AlterField(
            model_name='alumno',
            name='nombres_tutor',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='alumno',
            name='primer_apellido_tutor',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]

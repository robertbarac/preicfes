# Generated by Django 5.1.3 on 2025-02-05 03:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Departamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Municipio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=30)),
                ('departamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ciudades', to='ubicaciones.departamento')),
            ],
        ),
        migrations.CreateModel(
            name='Sede',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('municipio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sedes', to='ubicaciones.municipio')),
            ],
        ),
        migrations.CreateModel(
            name='Salon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField()),
                ('capacidad_sillas', models.PositiveIntegerField()),
                ('sede', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='salones', to='ubicaciones.sede')),
            ],
        ),
    ]

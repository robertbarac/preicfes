# Generated by Django 5.1.3 on 2025-04-11 21:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_firma'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='firma',
            name='activa',
        ),
        migrations.RemoveField(
            model_name='firma',
            name='cargo',
        ),
        migrations.RemoveField(
            model_name='firma',
            name='fecha_actualizacion',
        ),
        migrations.RemoveField(
            model_name='firma',
            name='fecha_creacion',
        ),
    ]

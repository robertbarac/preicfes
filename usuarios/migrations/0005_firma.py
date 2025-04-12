# Generated by Django 5.1.3 on 2025-04-11 21:14

import django.db.models.deletion
import usuarios.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_alter_usuario_cedula_alter_usuario_municipio_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Firma',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagen', models.ImageField(help_text='Imagen de la firma digital (preferiblemente PNG con fondo transparente)', upload_to=usuarios.models.firma_upload_path)),
                ('cargo', models.CharField(help_text='Cargo que aparece debajo de la firma', max_length=100)),
                ('activa', models.BooleanField(default=True, help_text='Indica si la firma está activa para ser usada en documentos')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='firma', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Firma',
                'verbose_name_plural': 'Firmas',
            },
        ),
    ]

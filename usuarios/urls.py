from django.urls import path
from django.contrib.auth.views import LogoutView, PasswordChangeView
from .views import (
    CustomLoginView, ProfesorListView, ProfesorDetailView, 
    GenerarCertificadoTrabajoView, cambiar_contraseña
)


urlpatterns = [
    path(
        'login/', 
        CustomLoginView.as_view(template_name="usuarios/login.html"),
        name="login"
    ),
    path(
        'logout/',
        LogoutView.as_view(),
        # template_name="users/login.html"
        name='logout'
    ),
    path(
        'profesores/',
        ProfesorListView.as_view(),
        name='profesor_list'
    ),
    path(
        'profesores/<int:pk>/',
        ProfesorDetailView.as_view(),
        name='profesor_detail'
    ),
    path(
        'cambiar-contrasena/',
        cambiar_contraseña,
        name='cambiar_contraseña'
    ),
    path(
        'profesores/<int:profesor_id>/certificado-trabajo/',
        GenerarCertificadoTrabajoView.as_view(),
        name='generar_certificado_trabajo'
    ),
]

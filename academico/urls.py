from django.urls import path
from .views import (
    AlumnosListView, AlumnoDetailView, AlumnoCreateView, AlumnoUpdateView,
    ClasesProfesorListView, GenerarCertificadosSimulacroView, GenerarConstanciaPreICFESView, GrupoDetailView, 
    GrupoListView, ClaseListView, ClaseDetailView,
    RegistroAsistenciaNotaView, registrar_o_editar_inasistencia
)
from . import views

urlpatterns = [
    path('alumnos/', AlumnosListView.as_view(), name='alumnos_list'),
    path('alumnos/<int:pk>/', AlumnoDetailView.as_view(), name='alumno_detail'),
    path('alumnos/<int:pk>/retirar/', views.retirar_alumno, name='retirar_alumno'),
    path('retirados/', views.AlumnosRetiradosListView.as_view(), name='alumnos-retirados-list'),
    path('alumnos/agregar/', AlumnoCreateView.as_view(), name='alumno_agregar'),
    path('alumnos/<int:pk>/editar/', AlumnoUpdateView.as_view(), name='alumno_editar'),
    path('grupos/', GrupoListView.as_view(), name='grupo_list'),
    path('grupos/<int:pk>/', GrupoDetailView.as_view(), name='grupo_detalle'),
    path(
        'profesores/<int:profesor_id>/clases/',
        ClasesProfesorListView.as_view(),
        name='profesor_clases'
    ),
    path('clases/', ClaseListView.as_view(), name='clase_list'),
    path('clases/<int:pk>/', ClaseDetailView.as_view(), name='clase_detail'),
    path('clases/<int:pk>/registro/', RegistroAsistenciaNotaView.as_view(), name='registro_asistencia_nota'),
    path('cronograma/', views.CronogramaView.as_view(), name='cronograma'),
    path('alumno/constancia-preicfes/<int:alumno_id>/', GenerarConstanciaPreICFESView.as_view(), name='generar_constancia_preicfes'),
    path('clase/certificados-simulacro/<int:clase_id>/', 
         GenerarCertificadosSimulacroView.as_view(), 
         name='generar_certificados_simulacro'),
    path('alumno/<int:alumno_pk>/clase/<int:clase_pk>/registrar-inasistencia/', registrar_o_editar_inasistencia, name='registrar_inasistencia'),]
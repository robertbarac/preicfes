from django.urls import path
from . import views

app_name = 'simulacros'

urlpatterns = [
    path('grupo/<int:grupo_id>/calificar/', views.GrupoCalificarSimulacroView.as_view(), name='grupo_calificar_simulacro'),
    path('resultados/', views.ResultadosSimulacroListView.as_view(), name='resultados_simulacros'),
    path('resultados/pdf/', views.DescargarResultadosPDFView.as_view(), name='descargar_resultados_pdf'),
]

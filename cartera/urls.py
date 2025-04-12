from django.urls import path
from .views import (
    BecadosListView, GraficaIngresosEgresosView, 
    CuotasVencidasListView, DeudaCreateView, CuotaCreateView, CuotaUpdateView, CuotaDeleteView, ReciboPDFView,
    PazSalvoListView, PazSalvoPDFView, ProximosPagosListView, InformeDiarioView, generar_pdf_informe,
    MantenimientoCarteraView
)

app_name = 'cartera'

urlpatterns = [
    # path('abonos-hechos/', AbonosHechosListView.as_view(), name='abonos_hechos'),
    # path('cartera/', CarteraListView.as_view(), name='cartera'),
    path('grafica/', GraficaIngresosEgresosView.as_view(), name='grafica'),
    path('mantenimiento/', MantenimientoCarteraView.as_view(), name='mantenimiento'),
    path('cuotas-vencidas/', CuotasVencidasListView.as_view(), name='cuotas_vencidas'),
    path('deuda/agregar/<int:alumno_id>/', DeudaCreateView.as_view(), name='deuda_agregar'),
    path('cuota/agregar/<int:deuda_id>/', CuotaCreateView.as_view(), name='cuota_agregar'),
    path('cuota/editar/<int:pk>/', CuotaUpdateView.as_view(), name='cuota_editar'),
    path('cuota/eliminar/<int:pk>/', CuotaDeleteView.as_view(), name='cuota_eliminar'),
    path('cuota/recibo/<int:pk>/', ReciboPDFView.as_view(), name='cuota_recibo'),
    path('proximos-pagos/', ProximosPagosListView.as_view(), name='proximos_pagos'),
    path('paz-salvo/', PazSalvoListView.as_view(), name='paz_salvo'),
    path('becados/', BecadosListView.as_view(), name='becados_list'),
    path('paz-salvo/pdf/<int:alumno_id>/', PazSalvoPDFView.as_view(), name='paz_salvo_pdf'),
    path('informe-diario/', InformeDiarioView.as_view(), name='informe_diario'),
    path('informe-diario/pdf/', generar_pdf_informe, name='generar_pdf_informe'),
]
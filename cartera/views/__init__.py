from .alumnos_retirados_list import AlumnosRetiradosListView
from .becados_list import BecadosListView
from .cuota_create import CuotaCreateView
from .cuota_delete import CuotaDeleteView
from .cuota_update import CuotaUpdateView
from .cuotas_vencidas_list import CuotasVencidasListView
from .deuda_create import DeudaCreateView
from .generar_informe_pdf import generar_pdf_informe
from .grafica_ingresos_egresos import GraficaIngresosView
from .grafica_egresos import GraficaEgresosView
from .informe_diario import InformeDiarioView
from .mantenimiento_cartera import MantenimientoCarteraView
from .paz_salvo_list import PazSalvoListView
from .paz_salvo_pdf import PazSalvoPDFView
from .proximos_pagos_list import ProximosPagosListView
from .recibo_pdf import ReciboPDFView

__all__ = [
    'AlumnosRetiradosListView',
    'BecadosListView',
    'CuotasVencidasListView',
    'ProximosPagosListView',
    'CuotaCreateView',
    'CuotaUpdateView',
    'CuotaDeleteView',
    'DeudaCreateView',
    'GraficaIngresosView',
    'GraficaEgresosView',
    'MantenimientoCarteraView',
    'InformeDiarioView',
    'generar_pdf_informe',
    'PazSalvoListView',
    'PazSalvoPDFView',
    'ReciboPDFView'
]
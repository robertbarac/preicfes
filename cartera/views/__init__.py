from .becados_list import BecadosListView
from .cuotas_vencidas_list import CuotasVencidasListView
from .cuota_create import CuotaCreateView
from .cuota_update import CuotaUpdateView
from .cuota_delete import CuotaDeleteView
from .deuda_create import DeudaCreateView
from .grafica_ingresos_egresos import GraficaIngresosEgresosView
from .mantenimiento_cartera import MantenimientoCarteraView
from .informe_diario import InformeDiarioView
from .generar_informe_pdf import generar_pdf_informe
from .paz_salvo_list import PazSalvoListView
from .paz_salvo_pdf import PazSalvoPDFView
from .proximos_pagos_list import ProximosPagosListView
from .recibo_pdf import ReciboPDFView

__all__ = [
    'BecadosListView',
    'CuotasVencidasListView',
    'ProximosPagosListView',
    'CuotaCreateView',
    'CuotaUpdateView',
    'CuotaDeleteView',
    'DeudaCreateView',
    'GraficaIngresosEgresosView',
    'MantenimientoCarteraView',
    'InformeDiarioView',
    'generar_pdf_informe',
    'PazSalvoListView',
    'PazSalvoPDFView',
    'ReciboPDFView'
]
from .profesor_list import ProfesorListView
from .profesor_detail import ProfesorDetailView
from .custom_login import CustomLoginView
from .cambiar_contrasena import cambiar_contraseña
from .generar_certificado_trabajo import GenerarCertificadoTrabajoView


__all__ = [
    'CustomLoginView',
    'GenerarCertificadoTrabajoView',
    'ProfesorListView',
    'ProfesorDetailView',
    'cambiar_contraseña',
]
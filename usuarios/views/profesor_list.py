from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group

from usuarios.models import Usuario
from ubicaciones.models import Municipio

class ProfesorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Usuario
    template_name = 'usuarios/profesor_list.html'
    context_object_name = 'profesores'
    login_url = 'login'
    paginate_by = 20  # Paginación de 2 elementos por página

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        grupo_profesor = Group.objects.get(name='Profesor')
        queryset = Usuario.objects.filter(groups=grupo_profesor)
        
        user = self.request.user
        # Filtrado por rol
        if user.is_superuser:
            pass  # Superuser ve todo
        elif user.groups.filter(name='CoordinadorDepartamental').exists():
            if user.departamento:
                queryset = queryset.filter(departamento=user.departamento)
        else:
            # Otro personal (staff) ve solo su municipio
            queryset = queryset.filter(municipio=user.municipio)

        # Aplicar filtro de municipio desde el formulario
        municipio_id = self.request.GET.get('municipio')
        if municipio_id:
            queryset = queryset.filter(municipio_id=municipio_id)
            
        return queryset.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Listado de Profesores'
        
        user = self.request.user
        # Lógica de contexto por rol
        if user.is_superuser:
            context['municipios'] = Municipio.objects.all()
        elif user.groups.filter(name='CoordinadorDepartamental').exists():
            if user.departamento:
                context['municipios'] = Municipio.objects.filter(departamento=user.departamento)
            else:
                context['municipios'] = Municipio.objects.none()
        
        context['municipio_seleccionado'] = self.request.GET.get('municipio', '')
        context['is_coordinador'] = user.groups.filter(name='CoordinadorDepartamental').exists()

        # Añadir información de paginación al contexto
        paginator = context['paginator']
        page_obj = context['page_obj']
        page_number = page_obj.number
        page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
        context['page_range'] = page_range
        
        return context

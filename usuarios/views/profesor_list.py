from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group

from usuarios.models import Usuario

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
        
        # Si no es superuser, filtrar por municipio del usuario
        if not self.request.user.is_superuser:
            queryset = queryset.filter(municipio=self.request.user.municipio)
            
        return queryset.order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Listado de Profesores'
        
        # Añadir información de paginación al contexto
        paginator = context['paginator']
        page_obj = context['page_obj']
        
        # Obtener el número de página actual
        page_number = page_obj.number
        
        # Calcular el rango de páginas a mostrar (para evitar mostrar demasiadas páginas)
        page_range = list(paginator.get_elided_page_range(page_number, on_each_side=1, on_ends=1))
        context['page_range'] = page_range
        
        return context

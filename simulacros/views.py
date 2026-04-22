import os

import tempfile
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse

from academico.models import Grupo, Alumno
from ubicaciones.models import Sede
from .models import Simulacro, ResultadoSimulacro
from .procesar_simulacro import procesar_imagen
from .calculos import calificar, calcular_puntaje_icfes

# ReportLab imports
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from django.conf import settings

class GrupoCalificarSimulacroView(LoginRequiredMixin, View):
    def get(self, request, grupo_id):
        grupo = get_object_or_404(Grupo, id=grupo_id)
        alumnos = Alumno.objects.filter(grupo_actual=grupo).order_by('primer_apellido', 'segundo_apellido')
        simulacros = Simulacro.objects.all()
        
        context = {
            'grupo': grupo,
            'alumnos': alumnos,
            'simulacros': simulacros,
        }
        return render(request, 'simulacros/calificar_grupo.html', context)

    def post(self, request, grupo_id):
        grupo = get_object_or_404(Grupo, id=grupo_id)
        
        simulacro_id = request.POST.get('simulacro')
        fecha_realizacion = request.POST.get('fecha_realizacion')
        alumnos_ids = request.POST.getlist('alumnos_seleccionados')
        archivos = request.FILES.getlist('imagenes')
        
        if not simulacro_id or not fecha_realizacion or not alumnos_ids or not archivos:
            messages.error(request, "Faltan datos requeridos para procesar.")
            return redirect('simulacros:grupo_calificar_simulacro', grupo_id=grupo.id)
            
        simulacro = get_object_or_404(Simulacro, id=simulacro_id)
        
        if len(archivos) != len(alumnos_ids) * 2:
            messages.error(request, f"La cantidad de imágenes ({len(archivos)}) no coincide con el doble de alumnos seleccionados ({len(alumnos_ids) * 2}).")
            return redirect('simulacros:grupo_calificar_simulacro', grupo_id=grupo.id)
            
        # Ordenar archivos por nombre
        archivos_ordenados = sorted(archivos, key=lambda x: x.name)
        
        # Mantener el orden alfabético de alumnos
        alumnos_seleccionados = Alumno.objects.filter(id__in=alumnos_ids).order_by('primer_apellido', 'segundo_apellido')
        
        componentes_s1 = ['matematicas', 'lectura', 'sociales', 'naturales']
        componentes_s2 = ['matematicas', 'naturales', 'sociales', 'ingles']
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            for idx, alumno in enumerate(alumnos_seleccionados):
                file_s1 = archivos_ordenados[idx * 2]
                file_s2 = archivos_ordenados[idx * 2 + 1]
                
                path_s1 = os.path.join(tmpdirname, file_s1.name)
                path_s2 = os.path.join(tmpdirname, file_s2.name)
                
                with open(path_s1, 'wb+') as dest:
                    for chunk in file_s1.chunks():
                        dest.write(chunk)
                with open(path_s2, 'wb+') as dest:
                    for chunk in file_s2.chunks():
                        dest.write(chunk)
                
                try:
                    sec_s1 = procesar_imagen(path_s1, 'S1', debug=False)
                    sec_s2 = procesar_imagen(path_s2, 'S2', debug=False)
                    
                    resp_s1 = ''.join(sec_s1)
                    resp_s2 = ''.join(sec_s2)
                    
                    # Extraer cortes
                    c_s1 = simulacro.puntos_corte_s1
                    cortes_s1 = c_s1 if isinstance(c_s1, list) else c_s1.get('cortes', [])
                    
                    c_s2 = simulacro.puntos_corte_s2
                    cortes_s2 = c_s2 if isinstance(c_s2, list) else c_s2.get('cortes', [])
                    
                    comp_s1 = calificar(resp_s1, simulacro.soluciones_s1, cortes_s1, componentes_s1)
                    comp_s2 = calificar(resp_s2, simulacro.soluciones_s2, cortes_s2, componentes_s2)
                    
                    # Consolidar
                    consolidados = {}
                    for comp in set(componentes_s1 + componentes_s2):
                        consolidados[comp] = {'buenas': 0, 'totales': 0}
                        if comp in comp_s1:
                            consolidados[comp]['buenas'] += comp_s1[comp]['buenas']
                            consolidados[comp]['totales'] += comp_s1[comp]['totales']
                        if comp in comp_s2:
                            consolidados[comp]['buenas'] += comp_s2[comp]['buenas']
                            consolidados[comp]['totales'] += comp_s2[comp]['totales']
                            
                    puntajes = calcular_puntaje_icfes(consolidados)
                    
                    # Guardar en BD
                    ResultadoSimulacro.objects.update_or_create(
                        alumno=alumno,
                        simulacro=simulacro,
                        defaults={
                            'respuestas_s1': resp_s1,
                            'respuestas_s2': resp_s2,
                            'puntaje_global': puntajes['global'],
                            'puntaje_matematicas': puntajes.get('matematicas', 0),
                            'puntaje_lectura': puntajes.get('lectura', 0),
                            'puntaje_sociales': puntajes.get('sociales', 0),
                            'puntaje_naturales': puntajes.get('naturales', 0),
                            'puntaje_ingles': puntajes.get('ingles', 0),
                            'fecha_realizacion': fecha_realizacion,
                            'registrador': request.user
                        }
                    )
                except Exception as e:
                    messages.error(request, f"Error procesando a {alumno}: {e}")
                    continue
                    
        messages.success(request, "Simulacros procesados exitosamente.")
        return redirect(f"{reverse('simulacros:resultados_simulacros')}?grupo={grupo.id}&simulacro={simulacro.id}&fecha_inicio={fecha_realizacion}&fecha_fin={fecha_realizacion}")


class PermisosResultadosMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=['CoordinadorDepartamental', 'SecretariaAcademica']).exists()

class ResultadosSimulacroListView(LoginRequiredMixin, PermisosResultadosMixin, ListView):
    model = ResultadoSimulacro
    template_name = 'simulacros/resultados_grupo.html'
    context_object_name = 'resultados'
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        sede_id = self.request.GET.get('sede')
        grupo_id = self.request.GET.get('grupo')
        simulacro_id = self.request.GET.get('simulacro')
        fecha_inicio = self.request.GET.get('fecha_inicio')
        fecha_fin = self.request.GET.get('fecha_fin')
        
        if sede_id:
            qs = qs.filter(alumno__sede_id=sede_id)
        if grupo_id:
            qs = qs.filter(alumno__grupo_actual_id=grupo_id)
        if simulacro_id:
            qs = qs.filter(simulacro_id=simulacro_id)
        if fecha_inicio:
            qs = qs.filter(fecha_realizacion__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_realizacion__lte=fecha_fin)
            
        return qs.select_related('alumno', 'simulacro', 'alumno__grupo_actual').order_by('alumno__primer_apellido', 'alumno__segundo_apellido')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sedes'] = Sede.objects.all()
        context['grupos'] = Grupo.objects.all()
        context['simulacros'] = Simulacro.objects.all()
        return context

class DescargarResultadosPDFView(LoginRequiredMixin, PermisosResultadosMixin, View):
    def get(self, request):
        qs = ResultadoSimulacro.objects.all().select_related('alumno', 'simulacro', 'alumno__grupo_actual').order_by('alumno__primer_apellido', 'alumno__segundo_apellido')
        
        sede_id = request.GET.get('sede')
        grupo_id = request.GET.get('grupo')
        simulacro_id = request.GET.get('simulacro')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        
        if sede_id:
            qs = qs.filter(alumno__sede_id=sede_id)
        if grupo_id:
            qs = qs.filter(alumno__grupo_actual_id=grupo_id)
        if simulacro_id:
            qs = qs.filter(simulacro_id=simulacro_id)
        if fecha_inicio:
            qs = qs.filter(fecha_realizacion__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_realizacion__lte=fecha_fin)
            
        if not qs.exists():
            messages.warning(request, "No hay resultados para exportar.")
            return redirect('simulacros:resultados_simulacros')
            
        # Determinar nombre
        grupo_obj = qs.first().alumno.grupo_actual
        grupo_nombre = grupo_obj.codigo if grupo_obj else "Varios"
        sim_nombre = qs.first().simulacro.nombre
        fecha = qs.first().fecha_realizacion.strftime("%Y-%m-%d") if qs.first().fecha_realizacion else "N/A"
        
        filename = f"{grupo_nombre} - {sim_nombre} - {fecha}.pdf"
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        # Use A5 portrait
        doc = SimpleDocTemplate(response, pagesize=A5, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Paleta de colores
        ocean_blue = colors.HexColor('#006699')
        gold = colors.HexColor('#FFD700')
        black = colors.HexColor('#000000')
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            textColor=ocean_blue,
            alignment=1, # center
            spaceAfter=15,
            fontSize=16
        )
        
        name_style = ParagraphStyle(
            name='NameStyle',
            parent=styles['Heading2'],
            textColor=black,
            alignment=1,
            spaceAfter=10,
            fontSize=14
        )
        
        global_style = ParagraphStyle(
            name='GlobalStyle',
            parent=styles['Heading1'],
            textColor=ocean_blue,
            alignment=1,
            spaceAfter=20,
            fontSize=36,
            leading=40
        )
        
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        
        for i, res in enumerate(qs):
            # Agregar Logo si existe
            if os.path.exists(logo_path):
                img = RLImage(logo_path, width=1.5*inch, height=1.5*inch)
                elements.append(img)
            
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph("Resultados de Simulacro", title_style))
            elements.append(Paragraph(f"{sim_nombre}", ParagraphStyle(name='Sub', parent=styles['Normal'], alignment=1, spaceAfter=20)))
            
            # Datos del alumno
            nombre_completo = f"{res.alumno.primer_apellido} {res.alumno.segundo_apellido} {res.alumno.nombres}"
            elements.append(Paragraph(nombre_completo, name_style))
            elements.append(Paragraph(f"<b>Grupo:</b> {res.alumno.grupo_actual.codigo if res.alumno.grupo_actual else 'N/A'} | <b>Fecha:</b> {res.fecha_realizacion.strftime('%Y-%m-%d') if res.fecha_realizacion else 'N/A'}", ParagraphStyle(name='Cent', parent=styles['Normal'], alignment=1)))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Puntaje Global
            elements.append(Paragraph("PUNTAJE GLOBAL", ParagraphStyle(name='GTitle', parent=styles['Normal'], alignment=1, textColor=colors.gray, fontName="Helvetica-Bold")))
            elements.append(Paragraph(str(int(res.puntaje_global)), global_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Tabla de componentes
            data = [
                ['Componente', 'Puntaje'],
                ['Matemáticas', str(int(res.puntaje_matematicas))],
                ['Lectura Crítica', str(int(res.puntaje_lectura))],
                ['Sociales y Ciudadanas', str(int(res.puntaje_sociales))],
                ['Ciencias Naturales', str(int(res.puntaje_naturales))],
                ['Inglés', str(int(res.puntaje_ingles))]
            ]
            
            table = Table(data, colWidths=[3*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), ocean_blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), black),
                ('GRID', (0, 0), (-1, -1), 1, gold),
                ('PADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
            
            # Salto de página para el siguiente alumno
            if i < len(qs) - 1:
                elements.append(PageBreak())
        
        doc.build(elements)
        return response

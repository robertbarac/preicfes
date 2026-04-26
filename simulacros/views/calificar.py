# views/calificar.py
# Aquí va GrupoCalificarSimulacroView

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
from ..models import Simulacro, ResultadoSimulacro
from ..procesar_simulacro import procesar_imagen
from ..calculos import calificar, calcular_puntaje_icfes, modificar_puntajes

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
            
        # Ordenar archivos por nombre (convención de nombrado del escáner)
        archivos_ordenados = sorted(archivos, key=lambda x: x.name)
        
        # Respetar el orden en que el usuario arrastró los alumnos en el formulario
        # (ese orden ya corresponde al orden del PDF escaneado)
        alumnos_map = {str(a.id): a for a in Alumno.objects.filter(id__in=alumnos_ids)}
        alumnos_seleccionados = [alumnos_map[aid] for aid in alumnos_ids if aid in alumnos_map]
        
        componentes_s1 = simulacro.get_componentes_s1()
        componentes_s2 = simulacro.get_componentes_s2()
        
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
                    
                    # Calcular puntajes modificados
                    puntajes_modificados = modificar_puntajes(puntajes, simulacro.umbral)
                    
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
                            'puntaje_global_modificado': puntajes_modificados['global'],
                            'puntaje_matematicas_modificado': puntajes_modificados.get('matematicas', 0),
                            'puntaje_lectura_modificado': puntajes_modificados.get('lectura', 0),
                            'puntaje_sociales_modificado': puntajes_modificados.get('sociales', 0),
                            'puntaje_naturales_modificado': puntajes_modificados.get('naturales', 0),
                            'puntaje_ingles_modificado': puntajes_modificados.get('ingles', 0),
                            'fecha_realizacion': fecha_realizacion,
                            'registrador': request.user
                        }
                    )
                except Exception as e:
                    messages.error(request, f"Error procesando a {alumno}: {e}")
                    continue
                    
        messages.success(request, "Simulacros procesados exitosamente.")
        return redirect(f"{reverse('simulacros:resultados_simulacros')}?grupo={grupo.id}&simulacro={simulacro.id}&fecha_inicio={fecha_realizacion}&fecha_fin={fecha_realizacion}")

import math

def calificar(respuesta_estudiante, solucion, cortes, componentes):
    """
    Califica las respuestas del estudiante y devuelve un diccionario con las buenas y totales por componente.
    """
    if len(respuesta_estudiante) != len(solucion):
        return {comp: {'buenas': 0, 'totales': 0} for comp in componentes}
    
    if len(cortes) != len(componentes) - 1:
        raise ValueError("La cantidad de cortes no coincide con la cantidad de componentes.")
    
    resultados = {comp: {'buenas': 0, 'totales': 0} for comp in componentes}
    
    contador_buenas = 0
    contador_totales = 0
    indice_corte = 0
    cortes = sorted(cortes)

    for i in range(len(respuesta_estudiante)):
        contador_totales += 1
        if respuesta_estudiante[i] == solucion[i]:
            contador_buenas += 1
        
        if indice_corte < len(cortes) and (i + 1) == cortes[indice_corte]:
            comp_actual = componentes[indice_corte]
            resultados[comp_actual]['buenas'] = contador_buenas
            resultados[comp_actual]['totales'] = contador_totales
            contador_buenas = 0
            contador_totales = 0
            indice_corte += 1
    
    comp_actual = componentes[-1]
    resultados[comp_actual]['buenas'] = contador_buenas
    resultados[comp_actual]['totales'] = contador_totales
    
    return resultados


def calcular_puntaje_icfes(puntajes_componentes):
    """
    Genera la ponderación y calificación a base 100 de los 5 componentes.
    
    puntajes_componentes: dict estructurado como:
    {
        'naturales': {'buenas': X, 'totales': Y},
        'sociales': {'buenas': X, 'totales': Y},
        'ingles': {'buenas': X, 'totales': Y},
        'lectura': {'buenas': X, 'totales': Y},
        'matematicas': {'buenas': X, 'totales': Y}
    }
    """
    pesos = {
        'naturales': 3,
        'sociales': 3,
        'lectura': 3,
        'matematicas': 3,
        'ingles': 1
    }
    
    resultados = {}
    suma_ponderada = 0
    total_pesos = sum(pesos.values()) # Siempre será 13 según fórmula del usuario
    
    for comp, datos in puntajes_componentes.items():
        if datos['totales'] > 0:
            # Fórmula: buenas / totales * 100, redondeado al entero más próximo
            puntaje = round((datos['buenas'] / datos['totales']) * 100)
        else:
            puntaje = 0
        
        resultados[comp] = puntaje
        
        # Ponderación para el resultado global
        peso = pesos.get(comp, 1)
        suma_ponderada += puntaje * peso
        
    # El global se divide entre 13, se multiplica por 5 (para base 500) y se redondea al entero más próximo
    puntaje_global = round((suma_ponderada / total_pesos) * 5)
    resultados['global'] = puntaje_global
    
    return resultados

def modificar_puntajes(puntajes_reales, umbral):
    """
    Ajusta los puntajes según reglas fijas pero introduce variabilidad aleatoria:
    - ≤140 → objetivo base 245
    - 141‑240 → objetivo base 280
    - >240 → objetivo base 310
    A cada objetivo se le suma un *boost* aleatorio (6‑12) y cada componente recibe
    un *jitter* aleatorio de -2 a +2 para evitar patrones visibles.
    Los componentes se escalan proporcionalmente al objetivo con boost y se mantiene
    un máximo de 100.
    """
    pg_real = puntajes_reales.get('global', 0)

    # Definir objetivo base según rangos
    if pg_real <= 140:
        objetivo_base = 245
    elif pg_real <= 240:
        objetivo_base = 280
    else:
        objetivo_base = 310

    # Si ya supera el objetivo base, no ajustamos
    if pg_real >= objetivo_base:
        return puntajes_reales.copy()

    # Caso especial pg_real == 0 para evitar división por cero
    if pg_real == 0:
        base_comp = min(100, round(objetivo_base / 5))
        return {
            'global': objetivo_base,
            'matematicas': base_comp,
            'lectura': base_comp,
            'sociales': base_comp,
            'naturales': base_comp,
            'ingles': base_comp,
        }

    import random
    # Boost aleatorio moderado para que el ajuste no sea uniforme
    boost = random.randint(6, 12)
    objetivo = objetivo_base + boost

    # Factor proporcional usando el objetivo con boost
    factor = objetivo / pg_real

    # Escalar componentes manteniendo límite 100 y añadiendo jitter
    modificados = {}
    pesos = {'naturales': 3, 'sociales': 3, 'lectura': 3, 'matematicas': 3, 'ingles': 1}
    total_pesos = sum(pesos.values())
    suma_ponderada = 0
    for comp, valor in puntajes_reales.items():
        if comp == 'global':
            continue
        nuevo_valor = min(100, round(valor * factor))
        # Jitter aleatorio pequeño
        nuevo_valor = max(0, min(100, nuevo_valor + random.randint(-2, 2)))
        modificados[comp] = nuevo_valor
        peso = pesos.get(comp, 1)
        suma_ponderada += nuevo_valor * peso

    # Recalcular global a partir de los componentes modificados
    nuevo_global = round((suma_ponderada / total_pesos) * 5)
    # Garantizar que el global no quede por debajo del objetivo base
    if nuevo_global < objetivo_base:
        nuevo_global = objetivo_base
    modificados['global'] = min(500, nuevo_global)
    return modificados

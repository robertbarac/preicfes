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
    Si el puntaje global real está por debajo del umbral,
    se ajustan los puntajes dinámica y proporcionalmente para que el global quede
    al menos en el umbral, y los componentes se ajusten en consecuencia.
    """
    pg_real = puntajes_reales.get('global', 0)
    
    if pg_real >= umbral:
        return puntajes_reales.copy()
        
    import random
    
    # Diferencia que falta para llegar al umbral
    diff = umbral - pg_real
    
    # Le sumamos un "boost" que lo pone en el umbral + un número aleatorio pequeño para variar
    boost = diff + random.randint(0, 15)
    
    factor = (pg_real + boost) / pg_real if pg_real > 0 else 0
    
    if pg_real == 0:
        nuevo_global = umbral + random.randint(0, 15)
        # Componentes base proporcionales
        base_comp = round(nuevo_global / 5)
        return {
            'global': nuevo_global,
            'matematicas': min(100, base_comp),
            'lectura': min(100, base_comp),
            'sociales': min(100, base_comp),
            'naturales': min(100, base_comp),
            'ingles': min(100, base_comp),
        }
        
    modificados = {}
    suma_ponderada = 0
    pesos = {'naturales': 3, 'sociales': 3, 'lectura': 3, 'matematicas': 3, 'ingles': 1}
    total_pesos = sum(pesos.values())

    for comp, valor in puntajes_reales.items():
        if comp == 'global':
            continue
        nuevo_valor = min(100, round(valor * factor))
        modificados[comp] = nuevo_valor
        
        peso = pesos.get(comp, 1)
        suma_ponderada += nuevo_valor * peso
        
    nuevo_global = round((suma_ponderada / total_pesos) * 5)
    
    # Asegurarnos de que el global recalculado sí pasa el umbral
    if nuevo_global < umbral:
        nuevo_global = umbral + random.randint(0, 5)
        
    modificados['global'] = min(500, nuevo_global)
    return modificados


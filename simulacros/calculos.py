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

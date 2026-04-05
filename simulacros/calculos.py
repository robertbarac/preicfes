import math

def calificar(respuesta_estudiante, solucion, cortes):
    """
    Función base (legado del usuario) para extraer la lista de cantidad de buenas
    con respecto a cortes definidos.
    """
    if len(respuesta_estudiante) != len(solucion):
        return []

    contador = 0
    lista_conteo = []
    cortes = set(cortes) 

    for i in range(len(respuesta_estudiante)):
        estudiante_respuesta = respuesta_estudiante[i]
        respuesta_correcta = solucion[i]
        
        if estudiante_respuesta == respuesta_correcta:
            contador += 1
        
        if (i + 1) in cortes:
            lista_conteo.append(contador)
            contador = 0
    
    lista_conteo.append(contador)
    return lista_conteo


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
            # Fórmula: buenas / totales * 100, redondeadas hacia arriba.
            puntaje = math.ceil((datos['buenas'] / datos['totales']) * 100)
        else:
            puntaje = 0
        
        resultados[comp] = puntaje
        
        # Ponderación para el resultado global
        peso = pesos.get(comp, 1)
        suma_ponderada += puntaje * peso
        
    puntaje_global = math.ceil(suma_ponderada / total_pesos)
    resultados['global'] = puntaje_global
    
    return resultados

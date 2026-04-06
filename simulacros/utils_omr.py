import cv2
import numpy as np

def biggestContour(contours):
    biggest = np.array([])
    max_area = 0
    for i in contours:
        area = cv2.contourArea(i)
        if area > 5000:
            peri = cv2.arcLength(i, True)
            approx = cv2.approxPolyDP(i, 0.02 * peri, True)
            if area > max_area and len(approx) == 4:
                biggest = approx
                max_area = area
    return biggest, max_area

def alinear_documento(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")
        
    # Resize manteniendo proporciones para procesamiento estándar
    heightImg, widthImg = 1200, 900
    img = cv2.resize(img, (widthImg, heightImg))
    
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # ELIMINAMOS COMPLETAMENTE LA LÓGICA DE "CAMSCANNER".
    # Tu imagen original ya estaba perfecta y paralela. El intento de buscar un marco 
    # solo estaba distorsionando las columnas internas. 
    # Pasamos la imagen limpia, pura y recta.
    
    warped_blocks = [img.copy()]

    # Retornamos las variables necesarias para que el pipeline no falle
    return warped_blocks, img, imgGray, imgGray, imgGray, img.copy(), img.copy()

def approx_contour(cont):
    peri = cv2.arcLength(cont, True)
    approx = cv2.approxPolyDP(cont, 0.02 * peri, True)
    return approx

def reorder(myPoints):
    myPoints = myPoints.reshape((4, 2))
    myPointsNew = np.zeros((4, 1, 2), np.float32)
    add = myPoints.sum(1)
    myPointsNew[0] = myPoints[np.argmin(add)]
    myPointsNew[3] = myPoints[np.argmax(add)]
    diff = np.diff(myPoints, axis=1)
    myPointsNew[1] = myPoints[np.argmin(diff)]
    myPointsNew[2] = myPoints[np.argmax(diff)]
    return myPointsNew

def encontrar_ovalos(img_warped):
    """
    Escanea la imagen transformada, binariza de forma adaptativa (mata sombras)
    y busca contornos que correspondan exactamente a los óvalos de respuesta.
    """
    imgGray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    
    # 1. UMBRAL ADAPTATIVO (MAGIA CONTRA LAS SOMBRAS)
    # A diferencia del umbral fijo (170), esto calcula la iluminación en cuadritos de 51x51
    # ¡Esto evitará que la mitad de la foto se vuelva invisible!
    imgThresh = cv2.adaptiveThreshold(imgGray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 10)
    
    # Buscar contornos externos
    contours, _ = cv2.findContours(imgThresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    candidatos = []
    alto_total = img_warped.shape[0]
    
    # 2. PRIMER FILTRO GROSERO (Aspect Ratio, Area, y Altura)
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect_ratio = w / float(h)
        area = w * h
        
        # Desechar el 15% superior de la hoja (Datos personales, Títulos)
        if y < (alto_total * 0.15):
            continue
            
        if 1.0 < aspect_ratio < 2.5 and 50 < area < 4000:
            candidatos.append({'c': c, 'w': w, 'h': h, 'x': x, 'y': y})

    img_debug_ovalos = img_warped.copy()
    ovalos_validos = []
    
    if not candidatos:
        return imgThresh, img_debug_ovalos, ovalos_validos

    # 3. SEGUNDO FILTRO DE PRECISIÓN (Mediana)
    # Los números a la izquierda logran pasar el filtro de aspecto, 
    # pero NO miden exactamente los mismos milímetros que los óvalos impresos (las máquinas no mienten).
    anchos = [cand['w'] for cand in candidatos]
    altos = [cand['h'] for cand in candidatos]
    mediana_w = np.median(anchos)
    mediana_h = np.median(altos)

    # Permitir una variación del ±35% respecto a la mediana del lote
    for cand in candidatos:
        w = cand['w']
        h = cand['h']
        if (mediana_w * 0.65 < w < mediana_w * 1.35) and (mediana_h * 0.65 < h < mediana_h * 1.35):
            ovalos_validos.append(cand['c'])
            # Dibujamos en verde a los SOBREVIVIENTES
            cv2.rectangle(img_debug_ovalos, (cand['x'], cand['y']), (cand['x'] + w, cand['y'] + h), (0, 255, 0), 2)

    return imgThresh, img_debug_ovalos, ovalos_validos

def agrupar_y_evaluar_ovalos(burbujas_contours, imgThresh):
    """
    1. Agrupa por columnas naturales en la hoja.
    2. Agrupa por filas (preguntas) dentro de cada columna.
    3. Evalúa la saturación de pixeles (0.45 vacío -> 0.70+ lleno).
    """
    if not burbujas_contours:
        return []

    # 1. Extraer los datos y centros
    burbujas_data = []
    for c in burbujas_contours:
        x, y, w, h = cv2.boundingRect(c)
        cY = y + (h // 2)
        cX = x + (w // 2)
        burbujas_data.append({'c': c, 'x': x, 'y': y, 'w': w, 'h': h, 'cX': cX, 'cY': cY})

    # 2. AGRUPACIÓN POR COLUMNAS
    # Si la distancia horizontal (X) entre dos burbujas es inmensa (ej. separa columnas de preguntas)
    # primero agrupamos en columnas para que no se mezclen.
    burbujas_data = sorted(burbujas_data, key=lambda b: b['cX'])
    columnas = []
    col_actual = [burbujas_data[0]]
    # Si la separación horizontal es más de 3 veces el ancho de un óvalo, es una columna distinta
    tolerancia_x = burbujas_data[0]['w'] * 3  

    for i in range(1, len(burbujas_data)):
        b = burbujas_data[i]
        b_anterior = col_actual[-1]
        
        if (b['cX'] - b_anterior['cX']) < tolerancia_x:
            col_actual.append(b)
        else:
            columnas.append(col_actual)
            col_actual = [b]
    columnas.append(col_actual)

    # 3. EXTRAER RESPUESTAS COLUMNA POR COLUMNA
    respuestas_examen = []
    letras = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    for col_idx, columna in enumerate(columnas):
        # Ordenar verticalmente la columna
        columna = sorted(columna, key=lambda b: b['cY'])
        
        # Agrupar en Filas
        filas = []
        fila_actual = [columna[0]]
        tolerancia_y = columna[0]['h'] * 0.7 
        
        for i in range(1, len(columna)):
            b = columna[i]
            if abs(b['cY'] - fila_actual[-1]['cY']) < tolerancia_y:
                fila_actual.append(b)
            else:
                filas.append(fila_actual)
                fila_actual = [b]
        filas.append(fila_actual)

        # 4. Procesar y Extraer resultado fila por fila
        for idx_fila, f in enumerate(filas):
            f = sorted(f, key=lambda b: b['cX'])
            
            porcentajes_llenado = []
            for b in f:
                x, y, w, h = b['x'], b['y'], b['w'], b['h']
                roi = imgThresh[y:y+h, x:x+w]
                total_pixeles = w * h
                pixeles_blancos = cv2.countNonZero(roi)
                relleno = pixeles_blancos / total_pixeles
                porcentajes_llenado.append(relleno)

            # ESTE ES EL SECRETO REVELADO POR TUS DATOS (Vacío es ~0.45, Lleno es > 0.65)
            umbral_marcado = 0.65 
            marcados = []
            for opc_idx, p in enumerate(porcentajes_llenado):
                if p > umbral_marcado:
                    marcados.append(opc_idx)

            if len(marcados) == 0:
                respuestas_examen.append("Z")
            elif len(marcados) > 1:
                respuestas_examen.append("Z")
            else:
                opcion = marcados[0]
                if opcion < len(letras):
                    respuestas_examen.append(letras[opcion])
                else:
                    respuestas_examen.append("?")
                    
    return respuestas_examen

def stackImages(imgArray, scale, lables=[]):
    rows = len(imgArray)
    cols = len(imgArray[0])
    rowsAvailable = isinstance(imgArray[0], list)
    width = imgArray[0][0].shape[1]
    height = imgArray[0][0].shape[0]
    
    scaled_w = int(width * scale)
    scaled_h = int(height * scale)
    
    if rowsAvailable:
        for x in range ( 0, rows):
            for y in range(0, cols):
                imgArray[x][y] = cv2.resize(imgArray[x][y], (scaled_w, scaled_h))
                if len(imgArray[x][y].shape) == 2: 
                    imgArray[x][y]= cv2.cvtColor( imgArray[x][y], cv2.COLOR_GRAY2BGR)
        imageBlank = np.zeros((scaled_h, scaled_w, 3), np.uint8)
        hor = [imageBlank]*rows
        for x in range(0, rows):
            hor[x] = np.hstack(imgArray[x])
        ver = np.vstack(hor)
    else:
        for x in range(0, rows):
            imgArray[x] = cv2.resize(imgArray[x], (scaled_w, scaled_h))
            if len(imgArray[x].shape) == 2: 
                imgArray[x] = cv2.cvtColor(imgArray[x], cv2.COLOR_GRAY2BGR)
        hor= np.hstack(imgArray)
        ver = hor
        
    return ver

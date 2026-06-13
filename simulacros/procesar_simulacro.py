#!/usr/bin/env python3
"""
procesar_simulacro.py — Pipeline OMR por tiras verticales.

Uso:
    python3 procesar_simulacro.py S1 imagenes_muestra/SCAN0008_page-0031.jpg
    python3 procesar_simulacro.py S2 imagenes_muestra/SCAN0008_page-0032.jpg
"""
import cv2
import numpy as np
import os
import sys

# ================================================================
# CONSTANTES DE CORTE — Ajustar si los recortes no caen bien
# Imagen estándar: 1275 x 1650 px
# ================================================================

# === CONFIGURACIÓN S1 ===
# Ajustes exactos por columna (X_INI: donde empiezan los círculos, X_FIN: donde terminan)
# Y_INI: Dónde empiezan verticalmente (debajo de los textos), Y_FIN: Dónde terminan en el fondo
S1_CONF = {
    # Columna 1 (Preguntas 1-30)
    'c1_y_ini': 270, 'c1_y_fin': 1430,
    'c1_x_ini': 140, 'c1_x_fin': 350,
    
    # Columna 2 (Preguntas 31-60)
    'c2_y_ini': 270, 'c2_y_fin': 1430,
    'c2_x_ini': 430, 'c2_x_fin': 630,
    
    # Columna 3 (Preguntas 61-90)
    'c3_y_ini': 270, 'c3_y_fin': 1420,
    'c3_x_ini': 720, 'c3_x_fin': 920,
    
    # Columna 4 (Preguntas 91-120)
    'c4_y_ini': 270, 'c4_y_fin': 1430,
    'c4_x_ini': 1010, 'c4_x_fin': 1230
}

# === CONFIGURACIÓN S2 ===
# Control ABSOLUTO por tira. 
# y_ini: dónde empieza el corte (header), y_fin: dónde termina el corte (footer)
# x_ini: margen izquierdo, x_fin: margen derecho
S2_CONF = {
    # Tira 1 (P1-48, 4 opciones)
    'c1_y_ini': 210, 'c1_y_fin': 1580,
    'c1_x_ini': 120, 'c1_x_fin': 320,
    
    # Tira 2a (P49-79, 4 opciones)
    'c2a_y_ini': 200, 'c2a_y_fin': 1220,
    'c2a_x_ini': 370, 'c2a_x_fin': 560,
    
    # Tira 2b (P80-96, 8 opciones) -> Su propio header para saltar textos intermedios
    'c2b_y_ini': 1220, 'c2b_y_fin': 1520,
    'c2b_x_ini': 385,  'c2b_x_fin': 760, 
    
    # Tira 3 (P97-134, 8 opciones)
    'c3_y_ini': 220, 'c3_y_fin': 1550,
    'c3_x_ini': 830, 'c3_x_fin': 1200, 
}

# Umbral de relleno para considerar un círculo como marcado
# Al evaluar solo el "adentro" del círculo, un valor más bajo detecta marcas tenues
UMBRAL_MARCADO = 0.25

# ================================================================

# Tamaño de salida estándar al que se normalizará SIEMPRE la hoja
NORM_W = 1275
NORM_H = 1650


def _ordenar_esquinas(pts):
    """
    Dado un array (4,2) de puntos, retorna [top-left, top-right, bottom-right, bottom-left].
    """
    pts = pts.reshape(4, 2).astype(np.float32)
    s   = pts.sum(axis=1)
    d   = np.diff(pts, axis=1)
    return np.array([
        pts[np.argmin(s)],   # top-left     (menor x+y)
        pts[np.argmin(d)],   # top-right    (menor x-y)
        pts[np.argmax(s)],   # bottom-right (mayor x+y)
        pts[np.argmax(d)],   # bottom-left  (mayor x-y)
    ], dtype=np.float32)


def normalizar_hoja(img, debug_dir=None, base=None):
    """
    Detecta los 4 vértices de la hoja escaneada y aplica warpPerspective
    para producir SIEMPRE una imagen de NORM_W × NORM_H píxeles.

    Si no puede detectar la hoja (fondo sin contraste, imagen muy ruidosa),
    cae en un simple recorte centrado con deskew para no romper el flujo.

    Parámetros de debug opcionales:
      debug_dir — carpeta donde guardar imagen diagnóstica
      base      — prefijo del nombre de archivo
    """
    h_img, w_img = img.shape[:2]

    # 1. Convertir a escala de grises y suavizar
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (5, 5), 0)

    # 2. Umbralización adaptativa para separar hoja del fondo
    #    El fondo del escáner suele ser negro/gris oscuro; la hoja es blanca.
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 3. Operaciones morfológicas para cerrar pequeños huecos
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # 4. Encontrar contornos y quedarnos con el más grande (la hoja)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return _fallback_deskew(img)

    hoja_cnt = max(contours, key=cv2.contourArea)

    # La hoja debe ocupar al menos el 40 % de la imagen
    if cv2.contourArea(hoja_cnt) < 0.40 * w_img * h_img:
        return _fallback_deskew(img)

    # 5. Aproximar a polígono cuadrilátero
    peri  = cv2.arcLength(hoja_cnt, True)
    approx = cv2.approxPolyDP(hoja_cnt, 0.02 * peri, True)

    if len(approx) == 4:
        esquinas = _ordenar_esquinas(approx)
    else:
        # Si no sale exactamente 4 puntos, usamos el bounding rect
        x, y, w, h = cv2.boundingRect(hoja_cnt)
        esquinas = np.array([
            [x,     y    ],
            [x + w, y    ],
            [x + w, y + h],
            [x,     y + h],
        ], dtype=np.float32)

    # 6. Destino: los 4 vértices del tamaño estándar
    dst = np.array([
        [0,      0     ],
        [NORM_W, 0     ],
        [NORM_W, NORM_H],
        [0,      NORM_H],
    ], dtype=np.float32)

    # 7. Perspectiva y warp
    M   = cv2.getPerspectiveTransform(esquinas, dst)
    out = cv2.warpPerspective(img, M, (NORM_W, NORM_H),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    # 8. Debug opcional: guardar imagen con esquinas marcadas
    if debug_dir and base:
        diag = img.copy()
        for pt in esquinas.astype(int):
            cv2.circle(diag, tuple(pt), 12, (0, 0, 255), -1)
        cv2.polylines(diag, [esquinas.astype(int)], True, (0, 255, 0), 3)
        cv2.imwrite(os.path.join(debug_dir, f"{base}_normalizacion.jpg"), diag)

    return out


def _fallback_deskew(img):
    """
    Fallback: corrección de ángulo leve con HoughLines cuando no se detecta
    el contorno de la hoja. Devuelve la imagen lo más centrada posible en NORM_W×NORM_H.
    """
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
    angle = 0.0
    if lines is not None:
        angles = []
        for rho, theta in lines[:, 0]:
            a = (theta * 180 / np.pi) - 90
            if abs(a) < 10:
                angles.append(a)
        if angles:
            angle = float(np.median(angles))

    h, w = img.shape[:2]
    if abs(angle) >= 0.3:
        M   = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(img, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)

    # Redimensionar al tamaño estándar para que las coordenadas sigan funcionando
    return cv2.resize(img, (NORM_W, NORM_H), interpolation=cv2.INTER_AREA)


def hacer_tiras(img, modo):
    """
    Detecta los 4 grandes rectángulos que envuelven a cada columna de opciones.
    Devuelve la imagen recortada. Si la detección dinámica falla, utiliza las
    coordenadas fijas (S1_CONF, S2_CONF) como fallback robusto.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold adaptativo para resaltar trazos negros (como los rectángulos) sobre fondo blanco
    imgThresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 51, 10
    )
    
    # Unir líneas rotas por el escáner o deterioro
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    imgThresh_closed = cv2.morphologyEx(imgThresh, cv2.MORPH_CLOSE, kernel)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(imgThresh_closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    candidatos = []
    
    for c in contours:
        area = cv2.contourArea(c)
        if 50000 < area < 500000:
            x, y, w, h = cv2.boundingRect(c)
            ar = w / float(h)
            if 0.05 < ar < 0.4:
                # Extent asegura que la figura sea rectangular (llena el 80% de su bounding box)
                extent = area / float(w * h)
                if extent > 0.80:
                    cx, cy = x + w // 2, y + h // 2
                    # Evitar duplicados si hay contornos anidados
                    duplicado = False
                    for cand in candidatos:
                        # Si están muy cerca (ej. contorno interno y externo del grosor de la línea)
                        dist = ((cand['cx'] - cx)**2 + (cand['cy'] - cy)**2)**0.5
                        if dist < 30:
                            duplicado = True
                            break
                    if not duplicado:
                        candidatos.append({
                            'x': x, 'y': y, 'w': w, 'h': h,
                            'cx': cx, 'cy': cy
                        })

    # Si por alguna razón hay más de 4 candidatos, nos quedamos con los 4 de mayor área
    if len(candidatos) > 4:
        candidatos = sorted(candidatos, key=lambda r: r['area'], reverse=True)[:4]

    tiras_out = []

    # ======== FALLBACK A COORDENADAS FIJAS SI NO ENCONTRÓ LOS 4 ========
    if len(candidatos) < 4:
        print(f"⚠️ ADVERTENCIA: Solo se encontraron {len(candidatos)} rectángulos dinámicos.")
        print(f"✅ Usando coordenadas de fallback para {modo} en su lugar.")
        
        if modo == 'S1':
            keys = ['c1', 'c2', 'c3', 'c4']
            conf = S1_CONF
        else:
            keys = ['c1', 'c2a', 'c2b', 'c3']
            conf = S2_CONF
            
        for k in keys:
            y_ini, y_fin = conf[f'{k}_y_ini'], conf[f'{k}_y_fin']
            x_ini, x_fin = conf[f'{k}_x_ini'], conf[f'{k}_x_fin']
            # Recortar directo usando numpy slicing
            tira = img[y_ini:y_fin, x_ini:x_fin]
            tiras_out.append(tira)
    else:
        # ORDENAR DINÁMICAMENTE
        import functools
        def cmp_rects(r1, r2):
            if abs(r1['x'] - r2['x']) > 100:
                return r1['x'] - r2['x']
            return r1['y'] - r2['y']
        candidatos.sort(key=functools.cmp_rects if hasattr(functools, 'cmp_rects') else functools.cmp_to_key(cmp_rects))

        for rect in candidatos:
            x, y, w, h = rect['x'], rect['y'], rect['w'], rect['h']
            
            # Recorte directo 2D (sin deformar con warpPerspective, pues la hoja ya está recta)
            pad = 12
            y1 = max(0, y - pad)
            y2 = min(img.shape[0], y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(img.shape[1], x + w + pad)
            
            tira = img[y1:y2, x1:x2]
            tiras_out.append(tira)

    # Retornar con las configuraciones según el modo
    if modo == 'S1':
        return [
            (tiras_out[0], 4, 'S1_C1_P1-30'),
            (tiras_out[1], 4, 'S1_C2_P31-60'),
            (tiras_out[2], 4, 'S1_C3_P61-90'),
            (tiras_out[3], 4, 'S1_C4_P91-120'),
        ]
    elif modo == 'S2':
        return [
            (tiras_out[0], 4, 'S2_C1_P1-48'),
            (tiras_out[1], 4, 'S2_C2a_P49-79'),
            (tiras_out[2], 8, 'S2_C2b_P80-96'),
            (tiras_out[3], 8, 'S2_C3_P97-134'),
        ]

    raise ValueError(f"Modo desconocido: '{modo}'. Usa 'S1' o 'S2'.")


def encontrar_circulos_en_tira(tira, n_opciones=4):
    """
    Detecta contornos de círculos en una tira ya recortada.
    Retorna: (imgThresh, lista_de_contornos, imagen_debug)
    """
    gray = cv2.cvtColor(tira, cv2.COLOR_BGR2GRAY)
    imgThresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 51, 10
    )
    # Usamos RETR_LIST para que el marco exterior del rectángulo no oculte los círculos
    contours, _ = cv2.findContours(imgThresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Para círculos, el aspect ratio debe estar cerca de 1.0
    ar_min = 0.75
    ar_max = 1.35

    candidatos = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h == 0:
            continue
        ar   = w / float(h)
        area = w * h
        # Filtramos por proporciones de círculo y un área razonable
        if ar_min < ar < ar_max and 40 < area < 4500:
            cx, cy = x + w//2, y + h//2
            es_duplicado = False
            for cand in candidatos:
                if abs(cand['cx'] - cx) < 8 and abs(cand['cy'] - cy) < 8:
                    es_duplicado = True
                    # Al usar RETR_LIST, el mismo círculo se detecta por dentro y por fuera de su línea.
                    # Nos quedamos con el contorno de mayor área (el borde exterior).
                    if area > cand['area']:
                        cand['c'] = c
                        cand['w'], cand['h'] = w, h
                        cand['x'], cand['y'] = x, y
                        cand['area'] = area
                    break
            if not es_duplicado:
                candidatos.append({'c': c, 'w': w, 'h': h, 'x': x, 'y': y, 'cx': cx, 'cy': cy, 'area': area})

    img_debug = tira.copy()
    if not candidatos:
        return imgThresh, [], img_debug

    mw = np.median([c['w'] for c in candidatos])
    mh = np.median([c['h'] for c in candidatos])
    
    # Tolerancia para tamaños de círculos
    max_w_factor = 1.5
    max_h_factor = 1.5

    validos = []
    for c in candidatos:
        if (mw * 0.65 < c['w'] < mw * max_w_factor) and (mh * 0.65 < c['h'] < mh * max_h_factor):
            validos.append(c['c'])
            cv2.rectangle(img_debug,
                          (c['x'], c['y']),
                          (c['x'] + c['w'], c['y'] + c['h']),
                          (0, 200, 0), 2)

    return imgThresh, validos, img_debug


def evaluar_tira(contours, imgThresh, n_opciones):
    """
    Dado el conjunto de círculos detectados en UNA tira vertical de una sola
    columna de preguntas, determina la letra marcada en cada fila.
    """
    LETRAS = {4: ['A', 'B', 'C', 'D'], 8: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']}
    letras = LETRAS[n_opciones]

    if not contours:
        return []

    burbujas = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        burbujas.append({'x': x, 'y': y, 'w': w, 'h': h,
                         'cX': x + w // 2, 'cY': y + h // 2})

    # Agrupar en filas por coordenada Y
    burbujas = sorted(burbujas, key=lambda b: b['cY'])
    tol_y = burbujas[0]['h'] * 0.70
    filas, fila = [], [burbujas[0]]
    for b in burbujas[1:]:
        if abs(b['cY'] - fila[-1]['cY']) < tol_y:
            fila.append(b)
        else:
            filas.append(fila)
            fila = [b]
    filas.append(fila)

    # Centros X esperados para cada opción
    filas_ok = [f for f in filas if len(f) == n_opciones]
    if filas_ok:
        for f in filas_ok:
            f.sort(key=lambda b: b['cX'])
        centros = [np.median([f[i]['cX'] for f in filas_ok]) for i in range(n_opciones)]
    else:
        xs = [b['cX'] for b in burbujas]
        mn, mx = min(xs), max(xs)
        sp = (mx - mn) / (n_opciones - 1) if mx > mn else 1
        centros = [mn + sp * i for i in range(n_opciones)]

    # Evaluar cada fila
    respuestas = []
    for fila in filas:
        if len(fila) < 2:
            continue
        opciones = []
        for b in fila:
            idx = min(range(n_opciones), key=lambda i: abs(b['cX'] - centros[i]))
            
            # Recortamos el borde (15%) para evaluar SOLO el interior del círculo
            # Esto evita que la línea negra del propio círculo sume píxeles oscuros
            m_x = int(b['w'] * 0.15)
            m_y = int(b['h'] * 0.15)
            roi = imgThresh[b['y']+m_y : b['y']+b['h']-m_y, b['x']+m_x : b['x']+b['w']-m_x]
            
            if roi.size > 0:
                ratio = cv2.countNonZero(roi) / roi.size
            else:
                ratio = 0
            opciones.append((idx, ratio))

        # Ordenar opciones de la más oscura a la más clara
        opciones.sort(key=lambda x: x[1], reverse=True)
        mejor_idx, mejor_ratio = opciones[0]
        segundo_ratio = opciones[1][1] if len(opciones) > 1 else 0

        # Criterio de marcado:
        # 1. La opción más oscura debe superar el UMBRAL_MARCADO mínimo.
        # 2. Debe ser significativamente más oscura que la segunda opción (+10%).
        if mejor_ratio >= UMBRAL_MARCADO:
            if (mejor_ratio > segundo_ratio + 0.10):
                respuestas.append(letras[mejor_idx] if mejor_idx < len(letras) else '?')
            else:
                # Si hay dos muy parecidas de oscuras, es una doble marca
                respuestas.append('Z')
        else:
            # Si ninguna supera el umbral, está en blanco
            respuestas.append('Z')

    return respuestas


def procesar_imagen(image_path, modo, debug=False):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")

    if debug:
        print(f"  Imagen cargada: {img.shape[1]}x{img.shape[0]}px")
        # Relativo al archivo .py, sin importar desde dónde se corra
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cv_prototypes", "tiras")
        os.makedirs(debug_dir, exist_ok=True)
        base = os.path.basename(image_path).replace('.jpg', '').replace('.png', '')
    else:
        debug_dir = None
        base = None

    # Normalizar perspectiva: detecta la hoja y la estira a NORM_W × NORM_H siempre
    img = normalizar_hoja(img, debug_dir=debug_dir, base=base)
    if debug:
        print(f"  Hoja normalizada a {img.shape[1]}x{img.shape[0]}px")

    tiras = hacer_tiras(img, modo)

    secuencia = []
    for num, (tira_img, n_opciones, etiqueta) in enumerate(tiras, start=1):
        imgThresh, circulos, debug_img = encontrar_circulos_en_tira(tira_img, n_opciones)
        respuestas = evaluar_tira(circulos, imgThresh, n_opciones)
        secuencia.extend(respuestas)

        if debug:
            # Guardar el recorte limpio (para verificar que los cortes son correctos)
            nombre_corte = f"{base}_corte{num}.jpg"
            cv2.imwrite(os.path.join(debug_dir, nombre_corte), tira_img)

            # Guardar el recorte con los círculos detectados marcados en verde
            nombre_deteccion = f"{base}_corte{num}_deteccion.jpg"
            cv2.imwrite(os.path.join(debug_dir, nombre_deteccion), debug_img)

            print(f"  [{etiqueta}] {len(circulos)} círculos → {len(respuestas)} respuestas: {''.join(respuestas)}")
            print(f"    Guardado: {nombre_corte}  |  {nombre_deteccion}")

    return secuencia



if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 procesar_simulacro.py <S1|S2> <imagen.jpg>")
        sys.exit(1)

    modo   = sys.argv[1].upper()
    imagen = sys.argv[2]

    if modo not in ('S1', 'S2'):
        print("Error: modo debe ser S1 o S2")
        sys.exit(1)

    TOTAL = {'S1': 120, 'S2': 134}

    print(f"\n{'='*60}")
    print(f"  MODO: {modo}  |  Imagen: {imagen}")
    print(f"{'='*60}")

    try:
        seq = procesar_imagen(imagen, modo, debug=True)
        total_esperado = TOTAL[modo]
        print(f"\n{'='*60}")
        print(f"SECUENCIA FINAL ({len(seq)} / {total_esperado} esperadas):")
        print(''.join(seq))
        print('='*60)
        if len(seq) != total_esperado:
            print(f"\n⚠️  Diferencia de {abs(len(seq) - total_esperado)} preguntas.")
            print("   → Ajusta HEADER_PX, COL_X1, COL_X2, MARGIN_LEFT o MARGIN_RIGHT")
            print("     y vuelve a correr hasta que el conteo sea correcto.")
        else:
            print("\n✅ Conteo exacto. Revisa la secuencia para verificar precisión.")
        print(f"\nDebug de tiras en: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cv_prototypes', 'tiras')}/")
    except Exception as e:
        import traceback
        traceback.print_exc()

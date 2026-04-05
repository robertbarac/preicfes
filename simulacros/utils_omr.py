import cv2
import numpy as np

def ordenar_puntos(pts):
    """
    Ordena 4 puntos en el siguiente orden:
    superior-izquierdo, superior-derecho, inferior-derecho, inferior-izquierdo.
    """
    rect = np.zeros((4, 2), dtype="float32")
    
    # superior-izquierdo tiene suma min; inferior-derecho tiene suma max
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # superior-derecho tiene diff min; inferior-izquierdo tiene diff max
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def alinear_documento(image_path):
    """
    Paso 1 y 2: Carga la imagen, detecta los bordes y aplana la perspectiva
    asumiendo que las esquinas de la hoja son el contorno más grande.
    *(En prod: se adaptará para buscar específicamente las Marcas Fiduciarias negras)*
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")
    
    original = img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    contornos, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = sorted(contornos, key=cv2.contourArea, reverse=True)[:5]
    
    doc_cnt = None
    for c in contornos:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            doc_cnt = approx
            break
            
    if doc_cnt is None:
        raise ValueError("No se encontraron las 4 esquinas del documento para alinearlo.")

    pts = doc_cnt.reshape(4, 2)
    rect = ordenar_puntos(pts)
    
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")
    
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(original, M, (maxWidth, maxHeight))
    
    return warped

def binarizar_y_extraer(warped_img):
    """
    Paso 3, 4 y 5: Binariza para detectar lápiz, ubica contornos redondeados (burbujas)
    y usa countNonZero de NumPy para ver cuál está rellenada.
    """
    warped_gray = cv2.cvtColor(warped_img, cv2.COLOR_BGR2GRAY)
    
    # Binarización INVERSA: fondo(papel blanco) a negro, grafito/lápiz(negro) a blanco
    _, thresh = cv2.threshold(warped_gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    contornos, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    burbujas_encontradas = []
    for c in contornos:
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w / float(h)
        # Filtros de tamaño y proporción para asegurar que sea una burbuja
        # (Los parámetros 20 dependen de la resolución del escaneo final)
        if w >= 20 and h >= 20 and 0.9 <= ar <= 1.1:
            burbujas_encontradas.append(c)
    
    # Aquí iría el bloque donde agrupamos las burbujas por filas/preguntas.
    # Dado que aún no existe el diseño físico de la plantilla de respuestas,
    # este es el punto de extensión crítico a parametrizar según el PDF impreso.
    # 
    # Ejemplo de la magia NumPy:
    # pixels_blancos = np.count_nonzero(mask_burbuja == 255)
    
    return thresh, burbujas_encontradas

def procesar_archivo_simulacro(image_path, num_preguntas=120):
    """
    Punto de entrada principal para la carga de simulacros desde la vista de Django.
    Devuelve la cadena final de caracteres (ej: 'ABCDDCA...')
    """
    try:
        # 1. Alineación
        hoja_plana = alinear_documento(image_path)
        
        # 2. Binarización
        thresh, burbujas = binarizar_y_extraer(hoja_plana)
        
        # En este momento, asumiendo un mock de respuestas ya ordenadas:
        letras = ["A", "B", "C", "D"]
        resultados = []
        
        # ---> [LÓGICA PENDIENTE A ESPERA DEL FORMULARIO IMPRESO] <---
        # Se iteraría sobre las columnas de preguntas extrayendo el ganador
        # resultados.append(letras[índice_ganador])
        
        return "".join(resultados)
        
    except Exception as e:
        # En producción guardamos un log o lanzamos la excepción para UI
        print(f"Error procesando {image_path}: {e}")
        return None

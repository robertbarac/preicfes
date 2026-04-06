import cv2
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import utils_omr

def probar_imagen(image_path):
    print(f"Iniciando Detección de Óvalos (Contornos Libres) en: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        print(f"ERROR: No se pudo cargar '{image_path}'.")
        return

    # Extraemos bloques en perspectiva si detecta la hoja/márgenes mayores
    warped_blocks, img, imgGray, imgBlur, imgCanny, imgContours, imgBiggestContours = utils_omr.alinear_documento(image_path)
    
    # Procesaremos el primer bloque (Si es el documento entero o un recorte interno grande)
    img_a_procesar = warped_blocks[0]
    
    # 1. Encontrar los Contornos de los Óvalos
    imgThresh, img_debug_ovalos, ovalos = utils_omr.encontrar_ovalos(img_a_procesar)
    
    print(f"Óvalos detectados en este bloque: {len(ovalos)}")
    
    if len(ovalos) == 0:
        print("No encontré ningún óvalo válido. Quizá el contraste o la iluminación falló.")
    else:
        # 2. Agrupar espacialmente por Filas (cY) e Izquierda-Derecha (cX) y evaluar relleno
        respuestas = utils_omr.agrupar_y_evaluar_ovalos(ovalos, imgThresh)
        print("\n==================================")
        print(f"SECUENCIA DE RESPUESTAS FINALES:")
        print("".join(respuestas))
        print("==================================\n")
        print(len(respuestas))

    # 3. ENSAMBLAJE DE PANTALLA VISUAL (Stack Images)
    # Convertir threshold a 3 canales para compatibilidad de stackImages
    imgThreshColor = cv2.cvtColor(imgThresh, cv2.COLOR_GRAY2BGR)
    
    # Si por algún motivo no encontramos cajas o la hoja original vino muy pesada
    heightImg, widthImg = img.shape[:2]
    imgBlank = np.zeros((heightImg, widthImg, 3), np.uint8)
    
    labels = [
        ["Original", "Gris", "Bordes Canny"],
        ["Todos los Contornos", "Extracción Óvalos", "Filtro Threshold"]
    ]
    
    imageArray = (
        [img, imgGray, imgCanny],
        [imgContours, img_debug_ovalos, imgThreshColor]
    )
    
    stackedImages = utils_omr.stackImages(imageArray, 0.4, labels)
    
    # GUARDADO VISUAL PARA DEBUG SIN INTERFAZ QT (Ideal para WSL)
    out_dir = "cv_prototypes"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "debug_reciente.jpg")
    cv2.imwrite(out_path, stackedImages)
    print(f"\n=> [VISUALIZACIÓN] He guardado un análisis visual en: '{out_path}'")
    print("=> Por favor, abre esa imagen en tu computadora normal para que VEAS exactamente de dónde salieron esas 124 marcas verdes.")
    
    if "--headless" not in sys.argv:
        cv2.imshow("Oval Detection OMR", stackedImages)
        print("Presiona cualquier tecla para cerrar...")
        cv2.waitKey(0)
    else:
        print("[Modo Headless] omitiendo apertura de ventana.")
        
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso sugerido: python test_cv.py /ruta/a/tu/hoja_escaneada.jpg")
    else:
        ruta_archivo = sys.argv[1]
        try:
            probar_imagen(ruta_archivo)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error mortal: {e}")

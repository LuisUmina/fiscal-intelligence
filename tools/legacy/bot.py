import argparse
import time
import os
import zipfile
from pathlib import Path
from io import StringIO
from selenium import webdriver
#from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
#from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

#==========================================================================#
# 1. VARIABLES GLOBALES
#==========================================================================#

# Configuración de procesamiento
MAX_RUCS_POR_TXT = 100                # Máximo de RUCs por archivo TXT
ARCHIVO_EXCEL = "rucs.xlsx"           # Nombre del archivo Excel inicial (en ruta principal)
DEFAULT_PROJECT_NAME = "sunat_ruc_masivo_temp"
DEFAULT_SHEET_NAME = 0
DEFAULT_RUC_COLUMN = "ruc"

# Nombres de columnas del Excel
COL_RUC = "RUCs"                      # Columna que contiene los RUCs
COL_TXT_ASIGNADO = "TXT_Asignado"     # Columna para marcar a qué TXT pertenece
COL_ESTADO = "Estado"                 # Columna para marcar el estado (en Excel inicial)

# Nombres de archivos y carpetas dentro del proyecto
NOMBRE_CARPETA_TXT = "txt_rucs"      # Nombre de la carpeta donde se guardan los TXT
NOMBRE_CARPETA_ZIP = "zip_descargados"  # Nombre de la carpeta donde se guardan los ZIP
NOMBRE_LEYENDA = "leyenda_lotes.xlsx"    # Nombre del Excel leyenda

#==========================================================================#
# 2. FUNCIONES DE CONFIGURACION DEL NAVEGADOR
#==========================================================================#

def GenerarBrowser(flagIncognito=False, carpeta_descarga=None):
    try:
        chromeOptions = webdriver.ChromeOptions()
        chromeOptions.add_argument('--window-size=1280,800')
        chromeOptions.add_argument('--window-position=32000,32000')
        chromeOptions.add_argument('--ignore-certificate-errors')  # Ignora errores de certificado


        chromeOptions.add_argument('--disable-extensions')  # Deshabilitar extensions
        chromeOptions.add_argument('--disable-plugins')     # Deshabilitar plugins
        chromeOptions.add_argument('--no-sandbox')          # Bypass sandbox corporativo
        chromeOptions.add_argument('--disable-dev-shm-usage') # Evitar problemas de memoria


        chromeOptions.add_argument('--disable-gpu')
        chromeOptions.add_argument('--disable-web-security')
        chromeOptions.add_argument('--allow-running-insecure-content')
        chromeOptions.add_argument('--disable-background-timer-throttling')  # Mejora timing
        chromeOptions.add_argument('--disable-renderer-backgrounding')       # Mejora timing
        chromeOptions.add_argument('--disable-backgrounding-occluded-windows') # Mejora timing



        if flagIncognito:
            chromeOptions.add_argument("--incognito")

        
        # Configurar carpeta de descarga si se especifica
        if carpeta_descarga:
            # Convertir a ruta absoluta
            carpeta_descarga_abs = os.path.abspath(carpeta_descarga)
            prefs = {
                "download.default_directory": carpeta_descarga_abs,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chromeOptions.add_experimental_option("prefs", prefs)
        

        # Inicializar el navegador Chrome con las opciones configuradas
        #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chromeOptions)
        driver = webdriver.Chrome(options=chromeOptions)

        # Mover la ventana fuera del rango visible para no interrumpir al usuario.
        try:
            driver.set_window_position(32000, 32000)
            driver.set_window_size(1280, 800)
        except Exception:
            pass

        # Ejecutar script para desactivar WebDriver
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })

        return driver
    except Exception as e:
        print("Ocurrió un error al generar el navegador:", e)
        return None

#==========================================================================#
# 3. FUNCIONES DE SELENIUM BASICAS
#==========================================================================#

def BuscarComponentePorXpath(browser, path, max_intentos=20):
    """
    Busca un elemento con reintentos limitados (Parametro)
    """

    for intento in range(max_intentos):
        try:
            browser.find_element("xpath", path)
            return True

        except Exception as e:
            #print(f"Error en intento {intento+1}: {e}")
            time.sleep(1)

    print(f"Elemento no encontrado despues de {max_intentos} intentos: {path}")
    return False

def GetTextoPorXpath(browser, path, max_intentos=20):
    """
    Obtiene el texto de un elemento con reintentos limitados
    """

    for intento in range(max_intentos):
        try:
            componente = browser.find_element("xpath", path)
            return componente.text, True

        except Exception as e:
            #print(f"Error en intento {intento+1}: {e}")
            time.sleep(1)

    print(f"No se pudo obtener texto despues de {max_intentos} intentos: {path}")
    return "", False

def EscribirInputPorXpath(browser, path, texto, max_intentos=20):
    """
    Escribe texto en un campo de input por xpath con reintentos limitados
    """
    
    for intento in range(max_intentos):
        try:
            if BuscarComponentePorXpath(browser, path, max_intentos=20):
                componente = browser.find_element("xpath", path)
                componente.clear()
                componente.send_keys(texto)
                return True
            
        except Exception as e:
            #print(f"Error en intento {intento+1} escribiendo input: {e}")
            time.sleep(1)
    
    print(f"No se pudo escribir en el input despues de {max_intentos} intentos: {path}")
    return False

def DarClickPorXpath(browser, path, max_intentos=20):
    """
    Hace clic en un elemento por xpath con reintentos limitados
    """
    
    for intento in range(max_intentos):
        try:
            componente = browser.find_element("xpath", path)
            componente.click()
            return True
            
        except Exception as e:
            #print(f"Error en intento {intento+1} haciendo clic: {e}")
            time.sleep(1)
    
    print(f"No se pudo hacer clic despues de {max_intentos} intentos: {path}")
    return False

def GetElementosPorXpath(browser, path, min_elementos=1, max_intentos=20):
    """
    Espera a que aparezcan elementos (plural) con reintentos limitados
    Retorna la lista de elementos encontrados o lista vacía si no encuentra
    """
    
    for intento in range(max_intentos):
        try:
            elementos = browser.find_elements(By.XPATH, path)
            
            # Si encontró al menos min_elementos, retornar
            if len(elementos) >= min_elementos:
                print(f"[OK] Encontrados {len(elementos)} elementos")
                return elementos
            
            # Si no, esperar y reintentar
            time.sleep(1)
            
        except Exception as e:
            #print(f"Error en intento {intento+1}: {e}")
            time.sleep(1)
    
    print(f"No se encontraron suficientes elementos despues de {max_intentos} intentos")
    print(f"   XPath: {path}")
    return []


#==========================================================================#
# 1.1. FUNCIONES DE ORGANIZACION Y CARPETAS
#==========================================================================#

def crear_estructura_proyecto(nombre_proyecto, base_dir=None):
    """
    Crea la estructura de carpetas del proyecto
    Retorna un diccionario con las rutas de las carpetas creadas
    """
    # Crear carpeta principal del proyecto
    carpeta_proyecto = Path(base_dir) / nombre_proyecto if base_dir else Path(nombre_proyecto)
    carpeta_proyecto = str(carpeta_proyecto)
    
    if not os.path.exists(carpeta_proyecto):
        os.makedirs(carpeta_proyecto)
        print(f"[OK] Carpeta de proyecto creada: {carpeta_proyecto}")
    else:
        print(f"[OK] Carpeta de proyecto ya existe: {carpeta_proyecto}")
    
    # Crear subcarpetas
    carpeta_txt = os.path.join(carpeta_proyecto, NOMBRE_CARPETA_TXT)
    carpeta_zip = os.path.join(carpeta_proyecto, NOMBRE_CARPETA_ZIP)
    
    carpetas = {
        'proyecto': carpeta_proyecto,
        'txt': carpeta_txt,
        'zip': carpeta_zip
    }
    
    for nombre, ruta in [('TXT', carpeta_txt), ('ZIP', carpeta_zip)]:
        if not os.path.exists(ruta):
            os.makedirs(ruta)
            print(f"[OK] Carpeta {nombre} creada: {ruta}")
        else:
            print(f"[OK] Carpeta {nombre} ya existe: {ruta}")
    
    return carpetas

def obtener_ruta_leyenda(carpeta_txt):
    """
    Retorna la ruta completa del archivo leyenda
    """
    return os.path.join(carpeta_txt, NOMBRE_LEYENDA)

def obtener_ruta_txt(carpeta_txt, nombre_txt):
    """
    Retorna la ruta completa de un archivo TXT
    """
    return os.path.join(carpeta_txt, nombre_txt)

def subir_archivo_txt(browser, ruta_archivo_txt):
    """
    Sube un archivo TXT al input de SUNAT
    """
    try:
        # Esperar a que el input esté disponible
        if BuscarComponentePorXpath(browser, "//input[@id='txtfile']", max_intentos=20):
            # Obtener el elemento input
            input_file = browser.find_element(By.ID, "txtfile")
            
            # Convertir a ruta absoluta
            ruta_absoluta = os.path.abspath(ruta_archivo_txt)
            
            # Enviar la ruta del archivo directamente
            input_file.send_keys(ruta_absoluta)
            
            print(f"[OK] Archivo subido: {ruta_absoluta}")
            return True
        else:
            print("[X] No se encontró el input de archivo")
            return False
            
    except Exception as e:
        print(f"Error al subir archivo: {e}")
        return False


#==========================================================================#
# 4.2. FUNCIONES DE PROCESAMIENTO - OPCION 1
#==========================================================================#

def limpiar_ruc(ruc):
    """
    Limpia un RUC: elimina espacios y asegura que tenga pipe al final
    Retorna el RUC limpio con pipe al final
    """
    if pd.isna(ruc) or ruc == '':
        return None
    
    ruc_str = str(ruc).strip()
    
    # Si ya tiene pipe al final, mantenerlo; si no, agregarlo
    if ruc_str.endswith('|'):
        return ruc_str
    else:
        return ruc_str + '|'

def leer_excel_inicial(archivo_excel=ARCHIVO_EXCEL, sheet_name=None, columna_ruc=COL_RUC):
    """
    Lee el Excel inicial y retorna el DataFrame
    """
    try:
        df = pd.read_excel(archivo_excel, sheet_name=sheet_name)

        # Resolver columna RUC con una búsqueda tolerante por nombre.
        columna_resuelta = None
        if columna_ruc in df.columns:
            columna_resuelta = columna_ruc
        else:
            mapa_columnas = {str(col).strip().lower(): col for col in df.columns}
            candidatos = [columna_ruc, COL_RUC, "ruc", "rucs", "nro_ruc", "numero_ruc"]
            for candidato in candidatos:
                key = str(candidato).strip().lower()
                if key in mapa_columnas:
                    columna_resuelta = mapa_columnas[key]
                    break

        if columna_resuelta is None:
            print(f"[x] Error: No se encontró una columna de RUC en el Excel")
            return None

        # Normalizar la columna de RUC para que el resto del flujo siga igual
        if columna_resuelta != COL_RUC:
            df = df.rename(columns={columna_resuelta: COL_RUC})

        # Crear columna TXT_Asignado si no existe
        if COL_TXT_ASIGNADO not in df.columns:
            df[COL_TXT_ASIGNADO] = ""
            print(f"[OK] Columna '{COL_TXT_ASIGNADO}' creada en el Excel")
        
        # Filtrar RUCs válidos (no vacíos, no nulos)
        df = df[df[COL_RUC].notna() & (df[COL_RUC] != '')]
        df = df.reset_index(drop=True)
        
        print(f"[OK] Excel leído: {len(df)} RUCs válidos encontrados")
        return df
        
    except Exception as e:
        print(f"[x] Error al leer el Excel: {e}")
        import traceback
        traceback.print_exc()
        return None

def crear_txt_lote(carpeta_txt, numero_lote, rucs_lote):
    """
    Crea un archivo TXT con los RUCs del lote
    Retorna el nombre del archivo creado
    """
    nombre_txt = f"RUXLOT{numero_lote:03d}.txt"
    ruta_txt = obtener_ruta_txt(carpeta_txt, nombre_txt)
    
    try:
        with open(ruta_txt, 'w', encoding='utf-8') as f:
            for ruc in rucs_lote:
                ruc_limpio = limpiar_ruc(ruc)
                if ruc_limpio:  # Solo escribir RUCs válidos
                    f.write(ruc_limpio + '\n')
        
        print(f"  [OK] TXT creado: {nombre_txt} ({len(rucs_lote)} RUCs)")
        return nombre_txt
        
    except Exception as e:
        print(f"  [x] Error al crear {nombre_txt}: {e}")
        return None

def crear_leyenda_lotes(carpeta_txt, total_lotes):
    """
    Crea o actualiza el Excel leyenda con todos los lotes
    """
    ruta_leyenda = obtener_ruta_leyenda(carpeta_txt)
    
    try:
        # Crear DataFrame con todos los lotes
        datos_leyenda = []
        for i in range(1, total_lotes + 1):
            nombre_txt = f"RUXLOT{i:03d}.txt"
            datos_leyenda.append({
                'TXT': nombre_txt,
                'Estado': ''  # Estado vacío inicialmente
            })
        
        df_leyenda = pd.DataFrame(datos_leyenda)
        
        # Si ya existe la leyenda, leerla y actualizar solo los nuevos lotes
        if os.path.exists(ruta_leyenda):
            df_existente = pd.read_excel(ruta_leyenda)
            # Combinar manteniendo estados existentes
            df_leyenda = df_leyenda.merge(df_existente, on='TXT', how='left', suffixes=('', '_existente'))
            if 'Estado_existente' in df_leyenda.columns:
                df_leyenda['Estado'] = df_leyenda['Estado_existente'].fillna('')
                df_leyenda = df_leyenda[['TXT', 'Estado']]
        
        # Guardar leyenda
        df_leyenda.to_excel(ruta_leyenda, index=False)
        print(f"\n[OK] Leyenda creada/actualizada: {ruta_leyenda}")
        print(f"     Total de lotes: {total_lotes}")
        return True
        
    except Exception as e:
        print(f"[x] Error al crear la leyenda: {e}")
        import traceback
        traceback.print_exc()
        return False

def procesar_rucs(nombre_proyecto=None, archivo_excel=ARCHIVO_EXCEL, sheet_name=None, columna_ruc=COL_RUC, actualizar_excel=True, base_dir=None):
    """
    Opción 1: Procesa el Excel inicial, divide en TXT y crea la leyenda
    """
    print("==========================")
    print("OPCIÓN 1: PROCESAR RUCs")
    print("==========================")
    
    # Pedir nombre del proyecto
    if nombre_proyecto is None:
        nombre_proyecto = input("Ingrese el nombre del proyecto: ").strip()
    else:
        nombre_proyecto = str(nombre_proyecto).strip() or DEFAULT_PROJECT_NAME
    
    if not nombre_proyecto:
        print("[x] Error: El nombre del proyecto no puede estar vacío")
        return False
    
    # Crear estructura de carpetas
    print("\nCreando estructura de carpetas...")
    carpetas = crear_estructura_proyecto(nombre_proyecto, base_dir=base_dir)
    
    # Verificar que existe el Excel inicial
    if not os.path.exists(archivo_excel):
        print(f"\n[x] Error: No se encontró el archivo '{archivo_excel}'")
        print(f"   Asegúrate de que el archivo esté en la misma carpeta que bot.py")
        return False
    
    print(f"\n[OK] Archivo Excel encontrado: {archivo_excel}")
    
    # Leer Excel inicial
    print("\nLeyendo Excel inicial...")
    df = leer_excel_inicial(archivo_excel=archivo_excel, sheet_name=sheet_name, columna_ruc=columna_ruc)
    
    if df is None or len(df) == 0:
        print("[x] Error: No se pudieron leer RUCs del Excel o el Excel está vacío")
        return False
    
    # Dividir en lotes de 100
    total_rucs = len(df)
    total_lotes = (total_rucs + MAX_RUCS_POR_TXT - 1) // MAX_RUCS_POR_TXT  # División redondeada hacia arriba
    
    print(f"\nDividiendo {total_rucs} RUCs en {total_lotes} lotes de máximo {MAX_RUCS_POR_TXT}...")
    
    # Procesar cada lote
    print("\nCreando archivos TXT...")
    for i in range(total_lotes):
        inicio = i * MAX_RUCS_POR_TXT
        fin = min(inicio + MAX_RUCS_POR_TXT, total_rucs)
        rucs_lote = df[COL_RUC].iloc[inicio:fin].tolist()
        
        # Crear TXT
        nombre_txt = crear_txt_lote(carpetas['txt'], i + 1, rucs_lote)
        
        if nombre_txt:
            # Actualizar Excel con TXT_Asignado
            df.loc[inicio:fin-1, COL_TXT_ASIGNADO] = nombre_txt
    
    # Guardar Excel inicial actualizado solo cuando el flujo original lo necesita
    if actualizar_excel:
        try:
            df.to_excel(archivo_excel, index=False)
            print(f"\n[OK] Excel inicial actualizado: {archivo_excel}")
        except Exception as e:
            print(f"[x] Error al guardar el Excel inicial: {e}")
            return False
    else:
        print("\n[OK] Flujo automático: no se reescribe el Excel de entrada")
    
    # Crear leyenda
    print("\nCreando leyenda de lotes...")
    crear_leyenda_lotes(carpetas['txt'], total_lotes)
    
    print("\n" + "="*50)
    print("[OK] PROCESO COMPLETADO EXITOSAMENTE")
    print("="*50)
    print(f"  Total RUCs procesados: {total_rucs}")
    print(f"  Total lotes creados: {total_lotes}")
    print(f"  Carpeta TXT: {carpetas['txt']}")
    print(f"  Leyenda: {obtener_ruta_leyenda(carpetas['txt'])}")
    
    return True




#==========================================================================#
# 4.3. FUNCIONES DE PROCESAMIENTO - OPCION 2
#==========================================================================#

def leer_leyenda_pendientes(ruta_leyenda):
    """
    Lee la leyenda y retorna lista de TXT pendientes (estado vacío o "Error")
    """
    try:
        df = pd.read_excel(ruta_leyenda)
        if 'Estado' in df.columns:
            df['Estado'] = df['Estado'].fillna('').astype(str)
        
        # Filtrar pendientes: estado vacío, None, o "Error"
        df_pendientes = df[
            (df['Estado'].isna()) | 
            (df['Estado'] == '') | 
            (df['Estado'] == 'Error')
        ]
        
        return df_pendientes['TXT'].tolist(), df
        
    except Exception as e:
        print(f"[x] Error al leer la leyenda: {e}")
        return [], None

def actualizar_estado_leyenda(ruta_leyenda, nombre_txt, nuevo_estado, df_leyenda):
    """
    Actualiza el estado de un TXT en la leyenda
    """
    try:
        if 'Estado' in df_leyenda.columns:
            df_leyenda['Estado'] = df_leyenda['Estado'].fillna('').astype(object)
        df_leyenda.loc[df_leyenda['TXT'] == nombre_txt, 'Estado'] = nuevo_estado
        df_leyenda.to_excel(ruta_leyenda, index=False)
        return True
    except Exception as e:
        print(f"[x] Error al actualizar leyenda: {e}")
        return False

def _decodificar_bytes(contenido_bytes):
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return contenido_bytes.decode(encoding)
        except Exception:
            continue
    return contenido_bytes.decode("latin-1", errors="replace")

def _leer_texto_como_df(texto):
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    if not lineas:
        return pd.DataFrame()

    # Priorizamos pipe porque los TXT de resultados vienen delimitados por '|'.
    separadores = ["|", "\t", ";", ",", None]

    for separador in separadores:
        try:
            df = pd.read_csv(
                StringIO(texto),
                sep=separador,
                engine="python" if separador is not None else "python",
                dtype=str,
            )
            if not df.empty:
                # Para separadores explícitos exigimos más de una columna real.
                # Así evitamos devolver un DataFrame de una sola columna con la línea completa.
                if separador is not None and df.shape[1] > 1:
                    df.columns = [str(c).strip() for c in df.columns]
                    cols_vacias = []
                    for col in df.columns:
                        serie = df[col].fillna("").astype(str).str.strip()
                        if col.startswith("Unnamed") and (serie == "").all():
                            cols_vacias.append(col)
                    if cols_vacias:
                        df = df.drop(columns=cols_vacias)
                    return df

                if separador is None:
                    return df

            # Si el archivo tiene una sola línea de datos, pandas puede tomarla como encabezado.
            # Reintentamos sin encabezado para conservar el contenido.
            df_sin_encabezado = pd.read_csv(
                StringIO(texto),
                sep=separador,
                engine="python" if separador is not None else "python",
                dtype=str,
                header=None,
            )
            if not df_sin_encabezado.empty:
                if separador is not None and df_sin_encabezado.shape[1] > 1:
                    df_sin_encabezado.columns = [f"campo_{i+1}" for i in range(df_sin_encabezado.shape[1])]
                    return df_sin_encabezado

                if separador is None:
                    return df_sin_encabezado
        except Exception:
            continue

    return pd.DataFrame({"contenido": lineas})

def _leer_invalidos_como_df(texto):
    """Convierte TXT de inválidos a formato estable: 1 fila por línea."""
    filas = []
    for linea in texto.splitlines():
        linea_limpia = linea.strip()
        if not linea_limpia:
            continue

        campos = [c.strip() for c in linea_limpia.split("|")]
        filas.append(
            {
                "linea_raw": linea_limpia,
                "nro_campos": len(campos),
            }
        )

    return pd.DataFrame(filas)

def consolidar_resultados_desde_zips(carpeta_zip, carpeta_salida):
    """Lee los ZIP descargados y genera un Excel con hojas de correctos e inválidos."""
    resultados_correctos = []
    resultados_invalidos = []
    carpeta_zip = str(carpeta_zip)
    carpeta_salida = str(carpeta_salida)

    if not os.path.exists(carpeta_zip):
        print(f"[x] No existe la carpeta ZIP: {carpeta_zip}")
        return {
            "correctos": 0,
            "invalidos": 0,
            "archivo_consolidado": "",
        }

    archivos_zip = sorted(
        [
            os.path.join(carpeta_zip, nombre)
            for nombre in os.listdir(carpeta_zip)
            if nombre.lower().endswith(".zip")
        ]
    )

    if not archivos_zip:
        print(f"[x] No se encontraron ZIP para consolidar en: {carpeta_zip}")
        return {
            "correctos": 0,
            "invalidos": 0,
            "archivo_consolidado": "",
        }

    for ruta_zip in archivos_zip:
        nombre_zip = os.path.basename(ruta_zip)
        try:
            with zipfile.ZipFile(ruta_zip, "r") as archivo_zip:
                for miembro in archivo_zip.namelist():
                    if miembro.endswith("/"):
                        continue
                    if not miembro.lower().endswith(".txt"):
                        continue

                    with archivo_zip.open(miembro) as archivo_txt:
                        contenido = _decodificar_bytes(archivo_txt.read())
                        nombre_miembro = miembro.lower()
                        es_invalido = (
                            "invalid" in nombre_miembro
                            or "inval" in nombre_miembro
                            or "rucs_invalidos" in nombre_miembro
                            or "rucsinvalidos" in nombre_miembro
                        )

                        if es_invalido:
                            df_txt = _leer_invalidos_como_df(contenido)
                        else:
                            df_txt = _leer_texto_como_df(contenido)

                    if df_txt.empty:
                        continue

                    df_txt = df_txt.copy()
                    df_txt["zip_origen"] = nombre_zip
                    df_txt["txt_origen"] = os.path.basename(miembro)

                    if es_invalido:
                        resultados_invalidos.append(df_txt)
                    else:
                        resultados_correctos.append(df_txt)

        except Exception as exc:
            print(f"[x] Error al leer ZIP {nombre_zip}: {exc}")

    df_correctos = pd.concat(resultados_correctos, ignore_index=True) if resultados_correctos else pd.DataFrame()
    df_invalidos = pd.concat(resultados_invalidos, ignore_index=True) if resultados_invalidos else pd.DataFrame()

    ruta_consolidado = os.path.join(carpeta_salida, "sunat_ruc_masivo.xlsx")

    Path(carpeta_salida).mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(ruta_consolidado, engine="openpyxl") as writer:
        df_correctos.to_excel(writer, sheet_name="Correctos", index=False)
        df_invalidos.to_excel(writer, sheet_name="Invalidos", index=False)

    print(f"[OK] Excel consolidado generado: {ruta_consolidado}")
    print("[OK] Hojas: Correctos e Invalidos")
    print(f"[OK] Filas correctas consolidadas: {len(df_correctos)}")
    print(f"[OK] Filas invalidas consolidadas: {len(df_invalidos)}")

    return {
        "correctos": len(df_correctos),
        "invalidos": len(df_invalidos),
        "archivo_consolidado": ruta_consolidado,
    }

def procesar_txt_sunat(browser, ruta_txt, nombre_txt, carpeta_zip, numero_lote):
    """
    Procesa un TXT en SUNAT: sube, envía, espera y descarga
    Retorna True si fue exitoso, False si hubo error
    """
    url_sunat = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsmulruc/jrmS00Alias"
    
    try:
        # Navegar a SUNAT
        print(f"  [...] Navegando a SUNAT...")
        browser.get(url_sunat)
        time.sleep(2)

        # Seleccionar opcion de txt
        xpath_validar_mediante_archivo = "/html/body/div/div/div/div/div[2]/div[2]/ul/li[2]/a"
        if not DarClickPorXpath(browser, xpath_validar_mediante_archivo):
            print(f"  [x] No se pudo hacer clic en Validar mediante archivo")
            return False
        
        # Subir archivo TXT
        print(f"  [...] Subiendo archivo: {nombre_txt}")
        if not subir_archivo_txt(browser, ruta_txt):
            return False
        
        time.sleep(2)
        
        # Hacer clic en Enviar
        print(f"  [...] Haciendo clic en 'Enviar'...")
        xpath_enviar = "/html/body/div/div/div/div/div[2]/form[2]/div[2]/div[1]/button"
        if not DarClickPorXpath(browser, xpath_enviar):
            print(f"  [x] No se pudo hacer clic en Enviar")
            return False
        
        time.sleep(3)
        
        # Esperar a que termine el procesamiento
        print(f"  [...] Esperando procesamiento...")
        # Esperar a que aparezca la tabla con el encabezado
        xpath_encabezado = "//*[contains(text(), ' Consulta Múltiple de RUC')]"
        if not BuscarComponentePorXpath(browser, xpath_encabezado, max_intentos=30):
            print(f"  [x] No se encontró la tabla de resultados después de esperar")
            return False
        print(f"  [OK] Tabla de resultados encontrada")
        
        time.sleep(1)

        # Descargar ZIP
        print(f"  [...] Descargando ZIP...")
        xpath_descargar = "//a[contains(text(), '.zip')]"
        if not DarClickPorXpath(browser, xpath_descargar):
            print(f"  [x] No se pudo hacer clic en Descargar")
            return False
        
        # Esperar a que se descargue (ajustar tiempo según necesidad)
        time.sleep(7.5)

        
        print(f"  [OK] Procesado exitosamente: {nombre_txt}")
        return True
        
    except Exception as e:
        print(f"  [x] Error al procesar {nombre_txt}: {e}")
        import traceback
        traceback.print_exc()
        return False

def descargar_portal_sunat(nombre_proyecto=None, base_dir=None):
    """
    Opción 2: Lee los TXT de la leyenda y descarga los ZIP de SUNAT
    """
    print("================================")
    print("OPCIÓN 2: DESCARGAR PORTAL SUNAT")
    print("================================")
    
    # Pedir nombre del proyecto
    if nombre_proyecto is None:
        nombre_proyecto = input("Ingrese el nombre del proyecto: ").strip()
    else:
        nombre_proyecto = str(nombre_proyecto).strip() or DEFAULT_PROJECT_NAME
    
    if not nombre_proyecto:
        print("[x] Error: El nombre del proyecto no puede estar vacío")
        return False
    
    # Verificar que existe el proyecto
    carpeta_proyecto = Path(base_dir) / nombre_proyecto if base_dir else Path(nombre_proyecto)
    carpeta_proyecto = str(carpeta_proyecto)
    if not os.path.exists(carpeta_proyecto):
        print(f"\n[X] Error: No se encontró la carpeta del proyecto '{nombre_proyecto}'")
        print(f"   Asegúrate de ejecutar primero la Opción 1 para crear el proyecto")
        return False
    
    # Obtener rutas de carpetas
    carpeta_txt = os.path.join(carpeta_proyecto, NOMBRE_CARPETA_TXT)
    carpeta_zip = os.path.join(carpeta_proyecto, NOMBRE_CARPETA_ZIP)
    ruta_leyenda = obtener_ruta_leyenda(carpeta_txt)
    
    # Verificar que existe la leyenda
    if not os.path.exists(ruta_leyenda):
        print(f"\n[X] Error: No se encontró el archivo leyenda '{ruta_leyenda}'")
        print(f"   Asegúrate de ejecutar primero la Opción 1 para crear la leyenda")
        return False
    
    print(f"\n[OK] Proyecto encontrado: {carpeta_proyecto}")
    print(f"[OK] Leyenda encontrada: {ruta_leyenda}")
    
    # Leer leyenda y filtrar pendientes
    print("\nLeyendo leyenda y filtrando TXT pendientes...")
    txt_pendientes, df_leyenda = leer_leyenda_pendientes(ruta_leyenda)
    
    if not txt_pendientes:
        print("\n[OK] No hay TXT pendientes para procesar")
        return True
    
    print(f"[OK] Encontrados {len(txt_pendientes)} TXT pendientes")
    
    # Inicializar navegador con carpeta de descarga configurada
    print("\nIniciando navegador...")
    browser = GenerarBrowser(flagIncognito=False, carpeta_descarga=carpeta_zip)
    
    if browser is None:
        print("[x] Error: No se pudo inicializar el navegador")
        return False
    
    try:
        # Procesar cada TXT pendiente
        print(f"\nProcesando {len(txt_pendientes)} TXT...")
        print("="*50)
        
        procesados = 0
        errores = 0
        
        for i, nombre_txt in enumerate(txt_pendientes, 1):
            print(f"\n[{i}/{len(txt_pendientes)}] Procesando: {nombre_txt}")
            
            # Obtener ruta completa del TXT
            ruta_txt = obtener_ruta_txt(carpeta_txt, nombre_txt)
            
            if not os.path.exists(ruta_txt):
                print(f"  [x] Archivo TXT no encontrado: {ruta_txt}")
                actualizar_estado_leyenda(ruta_leyenda, nombre_txt, "Error", df_leyenda)
                errores += 1
                continue
            
            # Procesar TXT en SUNAT
            if procesar_txt_sunat(browser, ruta_txt, nombre_txt, carpeta_zip, i):
                # Actualizar estado a "Completado"
                actualizar_estado_leyenda(ruta_leyenda, nombre_txt, "Completado", df_leyenda)
                procesados += 1
            else:
                # Actualizar estado a "Error"
                actualizar_estado_leyenda(ruta_leyenda, nombre_txt, "Error", df_leyenda)
                errores += 1
            
            # Pequeña pausa entre procesamientos
            time.sleep(2)
        
        # Resumen final
        print("\n" + "="*50)
        print("[OK] PROCESO COMPLETADO")
        print("="*50)
        print(f"  Total procesados: {procesados}")
        print(f"  Errores: {errores}")
        print(f"  Pendientes restantes: {len(txt_pendientes) - procesados - errores}")

        carpeta_salida = str(Path(base_dir).resolve()) if base_dir else carpeta_proyecto
        resumen_consolidado = consolidar_resultados_desde_zips(carpeta_zip, carpeta_salida)
        if resumen_consolidado["archivo_consolidado"]:
            print("\n[OK] Consolidacion final completada")
        
    except Exception as e:
        print(f"\n[x] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cerrar navegador
        print("\nCerrando navegador...")
        browser.quit()
        print("[OK] Navegador cerrado")
    
    return True


def ejecutar_modo_automatico(archivo_excel, nombre_proyecto=DEFAULT_PROJECT_NAME):
    """Ejecuta el flujo completo sin interacción: crea TXT y luego descarga ZIP."""
    base_dir = Path(archivo_excel).resolve().parent
    ok = procesar_rucs(
        nombre_proyecto=nombre_proyecto,
        archivo_excel=archivo_excel,
        sheet_name=DEFAULT_SHEET_NAME,
        columna_ruc=DEFAULT_RUC_COLUMN,
        actualizar_excel=False,
        base_dir=base_dir,
    )
    if not ok:
        return False

    return descargar_portal_sunat(nombre_proyecto=nombre_proyecto, base_dir=base_dir)


def parse_args():
    parser = argparse.ArgumentParser(description="Bot legacy SUNAT")
    parser.add_argument("--excel-path", dest="excel_path", help="Ruta del Excel origen")
    parser.add_argument("--project-name", dest="project_name", default=DEFAULT_PROJECT_NAME, help="Nombre del proyecto a usar")
    return parser.parse_args()







#==========================================================================#
# 5. MENU
#==========================================================================#

def mostrar_menu():
    """
    Menu principal del bot
    """
    while True:
        os.system('cls')
        print("="*50)
        print("=== BOT SUNAT - CONSULTA MÚLTIPLE DE RUCs ===")
        print("="*50)
        print("\n--- Menú Principal ---")
        print("1. Procesar RUCs")
        print("   [...] Divide el Excel en TXT y crea la leyenda")
        print("\n2. Descargar portal SUNAT")
        print("   [...] Procesa los TXT y descarga los ZIP")
        print("\n3. Salir")
        
        opcion = input("\nSelecciona una opción (1, 2, 3): ").strip()
        
        if opcion == '1':
            procesar_rucs()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '2':
            descargar_portal_sunat()
            input("\nPresiona Enter para continuar...")
        
        elif opcion == '3':
            print("\nSaliendo del programa...")
            break
        
        else:
            print("\n[X] Opción no válida, intenta nuevamente.")
            time.sleep(2)

#==========================================================================#
# 6. MAIN
#==========================================================================#

if __name__ == "__main__":
    args = parse_args()
    if args.excel_path:
        ejecutar_modo_automatico(args.excel_path, args.project_name)
    else:
        mostrar_menu()
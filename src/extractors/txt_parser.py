import os
from unittest import skip
import pandas as pd
from config.settings import TXT_FORMATS

def get_txt_format_type(filename):
    #print(f"Archivo: {filename}")

    # Nombre a minuscula
    filename_lower = filename.lower()

    # Quitamos el .txt
    nombre_sin_ext = filename_lower.rsplit(".", 1)[0]
    
    # Nuevo formato
    if "ruc_maestro" in nombre_sin_ext:
        return "ruc_maestro"

    # Validar caracteres en nombre
    if len(nombre_sin_ext) != 33:
        return None

    # Identificar el tipo
    tipo = nombre_sin_ext[22:25]
    #print(f"Tipo: {tipo}")
    if tipo == "801":
        return "801"
    elif tipo == "804":
        return "804"
    else:
        return None

def extract_rucs_from_file(filepath, tipo):
    # Traer caracteristicas del tipo de archivo
    config = TXT_FORMATS[tipo]
    delimiter = config["txt_delimiter"]
    ruc_column = config["ruc_column"] - 1
    has_header = config["has_header"]

    # Leemos el txt
    if has_header:
        # Ignorar la cabecera real (corrupta) y saltar la linea
        df = pd.read_csv(
            filepath,
            sep=delimiter,
            header=None,
            skiprows=1,
            #encoding="utf-8"
            encoding="latin-1"
        )
    else:
        df = pd.read_csv(
            filepath,
            sep=delimiter,
            header=None,
            #encoding="utf-8"
            encoding="latin-1"
        )


    # Extraccion de RUCs
    col_ruc = df.iloc[:, ruc_column]
    rucs = col_ruc.dropna().astype(str).str.strip()
    rucs = rucs[rucs != ""].tolist()

    return rucs

def extract_rucs_from_folder(folder_path):
    """Devuelve (lista_rucs_unicos, lista_ruc_archivo, errores_txt).

    - lista_rucs_unicos: RUCs únicos encontrados en la carpeta.
    - lista_ruc_archivo: relación RUC -> archivo (una fila por archivo, sin duplicar dentro del mismo TXT).
    - errores_txt: lista con errores por archivo (para mostrarlos en pantalla).
    """

    # Set no permite tener duplicados
    todos_los_rucs = set()

    # Para definir de que archivo provienen
    rucs_archivos = []

    # Para guardar fallos por TXT sin detener el proceso
    errores_txt = []

    # Iteramos por todos los archivos de de la ruta 
    for filename in os.listdir(folder_path):
        ruta_completa = os.path.join(folder_path, filename)

        if not os.path.isfile(ruta_completa):
            continue
        
        if not filename.lower().endswith(".txt"):
            continue

        tipo = get_txt_format_type(filename)
        if tipo is None:
            continue

        try:
            rucs_del_archivo = extract_rucs_from_file(ruta_completa, tipo)
            todos_los_rucs.update(rucs_del_archivo)

            # Un RUC por archivo solo una vez (sin duplicados dentro del mismo TXT)
            for ruc in set(rucs_del_archivo):
                rucs_archivos.append({"ruc": ruc, "archivo": filename})
        except Exception as exc:
            errores_txt.append({"archivo": filename, "error": str(exc)})
            continue

    return list(todos_los_rucs), rucs_archivos, errores_txt


"""

if __name__ == "__main__":
    rucs, rucs_archivos, errores_txt = extract_rucs_from_folder("tst")
    print(f"Total RUCs únicos: {len(rucs)}")
    print(f"Total filas RUC-archivo: {len(rucs_archivos)}")
    print(f"Errores TXT: {len(errores_txt)}")
    print(rucs)
"""
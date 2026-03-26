import requests
from bs4 import BeautifulSoup
from config.settings import SUNAT_URL_CONSULTA, SUNAT_HEADERS
import pandas as pd
from io import StringIO

_session = requests.Session()

def _request_sunat_post(data, timeout=15):
    
    try:
        r = _session.post(SUNAT_URL_CONSULTA, data=data, headers=SUNAT_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r

    except requests.RequestException:
        return None

# Carga de cookies
def _warmup_sesion(ruc):
    data = {
        "accion": "consPorRuc",   # Accion de la pagina principal
        "nroRuc": str(ruc),
        "desRuc": "",
        "modo": "1",
        "tipo": "1",
    }
    _request_sunat_post(data)  # Solo para inicializar cookies

# Apartado: Representante Legal
def consultar_representantes_legales(ruc):
    """Apartado Representante Legal (accion getRepLeg)."""

    # Datos del formulario
    data = {
        "accion": "getRepLeg",
        "contexto": "ti-it",
        "modo": "1",
        "desRuc": "",
        "nroRuc": ruc,
    }

    # Request
    response = _request_sunat_post(data)
    if response is None:
        return {"status": "error", "mensaje": "request_failed", "tablas": []}

    # Hay este apartado ?
    texto = response.text.lower()
    if "No se encontro información para representantes legales.".lower() in texto or "Pagina de Error".lower() in texto:
        print(f" - [...] Apartado de REPRESENTANTES LEGALES no disponible para el RUC: {ruc}")
        return {"status": "no_data", "mensaje": "apartado_no_disponible", "tablas": []}

    #tablas = pd.read_html(StringIO(response.text))
    #print(tablas)

    # BeautifulSoup 
    soup = BeautifulSoup(response.text, "html.parser")

    # Validacion de tabla
    tabla = soup.find("table", class_="table")
    if not tabla or not tabla.find("tbody"):
        return {"status": "no_data", "mensaje": "tabla_no_encontrada", "tablas": []}

    resultados = []

    for fila in tabla.find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        documento =     columnas[0].text.strip()
        nro_documento = columnas[1].text.strip()
        nombre =        columnas[2].text.strip()
        cargo =         columnas[3].text.strip()
        fecha_desde =   columnas[4].text.strip()

        resultados.append({
            "ruc": ruc,
            "documento": documento,
            "nro_documento": nro_documento,
            "nombre": nombre,
            "cargo": cargo,
            "fecha_desde": fecha_desde,
        })
    #print(resultados)
    return {"status": "ok", "mensaje": "", "tablas": resultados}

# Apartado: Trabajadores
def consultar_trabajadores(ruc):
    """Apartado Trabajadores (accion getCantTrab)."""

    # Datos del formulario
    data = {
        "accion": "getCantTrab",
        "contexto": "ti-it",
        "modo": "1",
        "desRuc": "",
        "nroRuc": ruc,
    }

    # Request
    response = _request_sunat_post(data)
    if response is None:
        return {"status": "error", "mensaje": "request_failed", "tablas": []}

    # Hay este apartado ?
    texto = response.text.lower()
    if  "Pagina de Error".lower() in texto:
        print(f" - [...] Apartado de TRABAJADORES no disponible para el RUC: {ruc}")
        return {"status": "no_data", "mensaje": "apartado_no_disponible", "tablas": []}

    #tablas = pd.read_html(StringIO(response.text))
    #print(tablas)

    # BeautifulSoup 
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Validacion de tabla
    tabla = soup.find("table", class_="table")
    if not tabla or not tabla.find("tbody"):
        return {"status": "no_data", "mensaje": "tabla_no_encontrada", "tablas": []}

    resultados = []
    
    for fila in tabla.find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        periodo =                       columnas[0].text.strip()
        nro_trabajadores =              columnas[1].text.strip()
        nro_pensionistas =              columnas[2].text.strip()
        nro_prestadores_servicios  =    columnas[3].text.strip()

        resultados.append({
            "ruc": ruc,
            "periodo": periodo,
            "nro_trabajadores": nro_trabajadores,
            "nro_pensionistas": nro_pensionistas,
            "nro_prestadores_servicios": nro_prestadores_servicios,
        })
    
    return {"status": "ok", "mensaje": "", "tablas": resultados}

# Apartado: Establecimientos
def consultar_establecimientos(ruc):
    """Apartado Establecimientos (accion getLocAnex)."""

    # Datos del formulario
    data = {
        "accion": "getLocAnex",
        "contexto": "ti-it",
        "modo": "1",
        "desRuc": "",
        "nroRuc": ruc,
    }

    # Request
    response = _request_sunat_post(data)
    if response is None:
        return {"status": "error", "mensaje": "request_failed", "tablas": []}

    #print(response.text)

    # Hay este apartado ?
    texto = response.text.lower()
    if "No se encontró información para locales anexos.".lower() in texto or "Pagina de Error".lower() in texto:
        print(f" - [...] Apartado de ESTABLECIMIENTOS no disponible para el RUC: {ruc}")
        return {"status": "no_data", "mensaje": "apartado_no_disponible", "tablas": []}

    # LOG
    #tablas = pd.read_html(StringIO(response.text))
    #print(tablas)
    
    # BeautifulSoup 
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Validacion de tabla
    tabla = soup.find("table", class_="table")
    if not tabla or not tabla.find("tbody"):
        return {"status": "no_data", "mensaje": "tabla_no_encontrada", "tablas": []}

    resultados = []
    
    for fila in tabla.find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        #codigo =                columnas[0].text.strip()
        #tipo_establecimiento =  columnas[1].text.strip()
        #direccion =             columnas[2].text.strip()
        #actividad_economica  =  columnas[3].text.strip()

        codigo = " ".join(columnas[0].get_text().split())
        tipo_establecimiento = " ".join(columnas[1].get_text().split())
        direccion = " ".join(columnas[2].get_text().split())
        actividad_economica = " ".join(columnas[3].get_text().split())

        resultados.append({
            "ruc": ruc,
            "codigo": codigo,
            "tipo_establecimiento": tipo_establecimiento,
            "direccion": direccion,
            "actividad_economica": actividad_economica,
        })
    
    return {"status": "ok", "mensaje": "", "tablas": resultados}

"""
if __name__ == "__main__":
    ruc = "20505670443" # CONTIENE LOS 3  - Validado
    #ruc = "10101348763" # SIN REPRESENTANTES LEGALES - Validado
    #ruc = "20101071562" # SIN ESTABLECIMIENTOS - Validado
    #ruc = "20505670443"

    # Carga de cookies
    _warmup_sesion(ruc)

    print("\n SUNAT GENERAL \n")
    consultar_general(ruc)

    print("\n REPRESENTANTES LEGALES \n")
    consultar_representantes_legales(ruc)

    print("\n TRABAJADORES \n")
    consultar_trabajadores(ruc)

    print("\n ESTABLECIMIENTOS \n")
    consultar_establecimientos(ruc)
"""


import requests
from bs4 import BeautifulSoup
from config.settings import SUNAT_RUC_LOOKUP_URL, SUNAT_REQUEST_HEADERS
import pandas as pd
from io import StringIO

_session = requests.Session()

def _request_sunat_post(data, timeout=15):
    
    try:
        r = _session.post(SUNAT_RUC_LOOKUP_URL, data=data, headers=SUNAT_REQUEST_HEADERS, timeout=timeout)
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

        codigo =                " ".join(columnas[0].get_text().split())
        tipo_establecimiento =  " ".join(columnas[1].get_text().split())
        direccion =             " ".join(columnas[2].get_text().split())
        actividad_economica =   " ".join(columnas[3].get_text().split())

        resultados.append({
            "ruc": ruc,
            "codigo": codigo,
            "tipo_establecimiento": tipo_establecimiento,
            "direccion": direccion,
            "actividad_economica": actividad_economica,
        })
    
    return {"status": "ok", "mensaje": "", "tablas": resultados}


# Apartado: Infotmacion Historica
def consultar_informacion_historica(ruc):
    """Apartado Informacion Historica (accion getinfHis)."""
    
    # Datos del formulario
    data = {
        "accion": "getinfHis",
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
    if  "Pagina de Error".lower() in texto:
        print(f" - [...] Apartado de INFORMACION HISTORICA no disponible para el RUC: {ruc}")
        return {"status": "no_data", "mensaje": "apartado_no_disponible", "tablas": []}

    # BeautifulSoup 
    soup = BeautifulSoup(response.text, "html.parser")

    # Validacion de tabla
    tablas = soup.find_all("table", class_="table")
    if len(tablas) < 3:
        return {"status": "error", "mensaje": "q_tablas_no_encontrada", "tablas": []}

    # Tabla Interna: 1
    resultados_table_1 = []

    for fila in tablas[0].find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        nombre_razon_social =   " ".join(columnas[0].get_text().split())
        fecha_baja_1 =          " ".join(columnas[1].get_text().split())

        resultados_table_1.append({
            "ruc": ruc,
            "nombre_razon_social": nombre_razon_social,
            "fecha_baja": fecha_baja_1,
        })

    # Tabla Interna: 2
    resultados_table_2 = []

    for fila in tablas[1].find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        condicion_contribuyente =   " ".join(columnas[0].get_text().split())
        fecha_desde =               " ".join(columnas[1].get_text().split())
        fecha_hasta =               " ".join(columnas[2].get_text().split())

        resultados_table_2.append({
            "ruc": ruc,
            "condicion_contribuyente": condicion_contribuyente,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        })

    # Tabla Interna: 3
    resultados_table_3 = []

    for fila in tablas[2].find("tbody").find_all("tr"):
        columnas = fila.find_all("td")

        domicilio_fiscal =  " ".join(columnas[0].get_text().split())
        fecha_baja_3 =      " ".join(columnas[1].get_text().split())

        resultados_table_3.append({
            "ruc": ruc,
            "domicilio_fiscal": domicilio_fiscal,
            "fecha_baja": fecha_baja_3,
        })

    return {
    "status": "ok",
    "mensaje": "",
    "tablas": {
        "hist_company_name": resultados_table_1,
        "hist_taxpayer_status": resultados_table_2,
        "hist_fiscal_address": resultados_table_3,
    },
}



if __name__ == "__main__":
    ruc = "20505670443" # CONTIENE LOS 3  - Validado
    #ruc = "10101348763" # SIN REPRESENTANTES LEGALES - Validado
    #ruc = "20101071562" # SIN ESTABLECIMIENTOS - Validado
    #ruc = "20505670443"

    # Carga de cookies
    _warmup_sesion(ruc)

    #print("\n REPRESENTANTES LEGALES \n")
    #consultar_representantes_legales(ruc)

    #print("\n TRABAJADORES \n")
    #consultar_trabajadores(ruc)

    #print("\n ESTABLECIMIENTOS \n")
    #consultar_establecimientos(ruc)

    print("\n INFORMACION HISTORICA \n")
    consultar_informacion_historica(ruc)




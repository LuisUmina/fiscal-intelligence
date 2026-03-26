import requests
from bs4 import BeautifulSoup
from config.settings import SUNAT_SSCO_URL
import pandas as pd
from io import StringIO

def _request_sunat_get(timeout=15):
    
    try:
        r = requests.get(SUNAT_SSCO_URL, timeout=timeout)
        r.raise_for_status()
        return r

    except requests.RequestException:
        return None

# Apartado: Tabla de Sujetos Sin Capacidad Operativa
def consultar_sujetos_sin_capacidad():
    """Obtiene el padrón de Sujetos Sin Capacidad Operativa (SSCO) desde SUNAT."""

    # Request
    response = _request_sunat_get()
    if response is None:
        return {"status": "error", "mensaje": "request_failed", "tablas": []}

    response.encoding = "utf-8"

    tablas = pd.read_html(StringIO(response.text))
    #print(tablas)

    if not tablas:
        return {"status": "no_data", "mensaje": "tabla_no_encontrada", "tablas": []}

    
    df = tablas[0]

    # La primera fila viene como cabecera real
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)


    # Limpiar nombres de columnas
    df.columns = [str(c).strip() for c in df.columns]
    
    resultados = df.to_dict(orient="records")

    #print(resultados)

    return {"status": "ok", "mensaje": "", "tablas": resultados}

"""
if __name__ == "__main__":
    
    print("\n SUJETOS SIN CAPACIDAD OPERATIVA: \n")
    consultar_sujetos_sin_capacidad()
"""
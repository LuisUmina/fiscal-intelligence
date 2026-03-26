from playwright.sync_api import sync_playwright
from config.settings import SUNAT_FIELD_MAPEO, SUNAT_URL_CONSULTA

def init_navegador():
    """Inicializa navegador una sola vez - REUTILIZABLE para batch"""
    p = sync_playwright().start()
    browser = p.chromium.launch(channel="chrome", headless=False)
    page = browser.new_page()
    page.on("dialog", handle_dialog)
    return p, browser, page

def cerrar_navegador(p, browser):
    """Cierra navegador correctamente"""
    browser.close()
    p.stop()

def click_sunat_safe(page, locator, max_intentos=10):
    for intento in range(max_intentos):
        try:
            # Click
            locator.click()

            # Esperar a que algo cambie en el DOM 
            page.wait_for_load_state("domcontentloaded")

            # ERROR 1: Popup SUNAT
            if page.locator("xpath=/html/body/div/div[1]").count() > 0:
                texto = page.locator("xpath=/html/body/div/div[1]").inner_text()

                if "La aplicación ha retornado el siguiente problema" in texto:
                    print(f"[X_1] Error SUNAT popup (intento {intento+1})")

                    page.locator("xpath=/html/body/div/div[6]/input").click()
                    continue

            # ERROR 2: Redirección SUNAT
            if page.locator("xpath=/html/body").count() > 0:
                texto_body = page.locator("xpath=/html/body").inner_text()

                if "The requested URL was rejected" in texto_body:
                    print(f"[X_2] Redirección SUNAT detectada (intento {intento+1})")

                    page.locator("xpath=/html/body/a").click()
                    continue

            return True

        except Exception as e:
            print(f"[X] Error click intento {intento+1}: {e}")

    return False

# Manejo de alertas
dialog_message = {"value": None}

def handle_dialog(dialog):
    #print(f"[ALERT] {dialog.message}")
    dialog_message["value"] = dialog.message
    dialog.accept()

def consultar_informacion(page, ruc):

    dialog_message["value"] = None

    mapeo = SUNAT_FIELD_MAPEO
    data = {
        "ruc": ruc,
        "ruc_sunat": "",
        "tipo_contribuyente": "",
        "nombre_comercial": "",
        "fecha_inscripcion": "",
        "fecha_inicio_actividades": "",
        "estado_contribuyente": "",
        "condicion_contribuyente": "",
        "domicilio_fiscal": "",
        "sistema_emision_comprobante": "",
        "actividad_comercio_exterior": "",
        "sistema_contabilidad": "",
        "actividades_economicas": "", 
        "comprobantes_pago": "", 
        "sistema_emision_electronica": "", 
        "emisor_electronico_desde": "",
        "comprobantes_electronicos": "",
        "afiliado_ple_desde": "",
        "padrones": "", 
        "fecha_consulta_sunat": "",
        "mensaje_importante":""
    }

    try:
        # Pagina
        page.goto(SUNAT_URL_CONSULTA)

        # Esperar input
        input_ruc = page.locator("xpath=/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[1]/div/input")
        input_ruc.wait_for()
        input_ruc.fill(ruc)

        # Clic en "Buscar"
        btn_buscar = page.locator("xpath=/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[5]/div/button[1]")
        if not click_sunat_safe(page, btn_buscar):
            print(f"[X] Error al hacer clic en BUSCAR")
            return {"status": "error", "mensaje": "clic_invalido", "tablas": []}
        
        # Validar alerta
        if dialog_message["value"]:
            if "RUC válido" in dialog_message["value"]:
                return {"status": "no_data", "mensaje": "ruc_invalido", "tablas": []}

        # Tabla de datos    
        panel = page.locator("xpath=//div[contains(@class,'panel panel-primary')]")
        panel.wait_for(timeout=10000)

        items = panel.locator(".list-group-item")

        for i in range(items.count()):
            item = items.nth(i)

            # CASO 0: Importante
            if item.locator("strong").count() > 0:
                texto = item.locator("p").first.inner_text().strip()

                if "IMPORTANTE" in texto:
                    data["mensaje_importante"] = texto
                    continue

            # Si no tiene informacion (h4) no lo procesa
            if item.locator("h4").count() == 0:
                continue
            
            # Cabecera de tabla
            key_html = item.locator("h4").first.inner_text().replace(":", "").strip()

            # Filtramos las filas que queremos 
            if key_html not in mapeo:
                continue

            key_final = mapeo[key_html]

            # CASO 1: Value and key is h4
            if key_final in ["ruc_sunat"]:
                value = item.locator("h4").nth(1).inner_text().strip()
                data[key_final]= value

            # CASO 2: Value p and key is h4       
            elif key_final in ["tipo_contribuyente", "nombre_comercial", "estado_contribuyente", "condicion_contribuyente", "domicilio_fiscal", "sistema_contabilidad", "emisor_electronico_desde", "comprobantes_electronicos", "afiliado_ple_desde"]:
                value = item.locator("p").first.inner_text().strip()
                data[key_final]= value  

            # CASO 3.1: Four columns on element (Value p and key is h4)      
            elif key_final in ["fecha_inscripcion", "fecha_inicio_actividades"]:
                value_1 = item.locator("p").first.inner_text().strip()
                data["fecha_inscripcion"] = value_1

                value_2 = item.locator("p").nth(1).inner_text().strip()
                data["fecha_inicio_actividades"] = value_2

            # CASO 3.2: Four columns on element (Value p and key is h4)      
            elif key_final in ["sistema_emision_comprobante", "actividad_comercio_exterior"]:
                value_1 = item.locator("p").first.inner_text().strip()
                data["sistema_emision_comprobante"] = value_1

                value_2 = item.locator("p").nth(1).inner_text().strip()
                data["actividad_comercio_exterior"] = value_2
            
            # CASO 4: Table element  
            elif key_final in ["actividades_economicas", "comprobantes_pago", "sistema_emision_electronica", "padrones",]:
                # Validar que exista la tabla
                if item.locator("table").count() > 0:
                    filas_tabla = item.locator("table tr")

                    valores = []
                    for j in range(filas_tabla.count()):
                        texto = filas_tabla.nth(j).inner_text().strip()
                        if texto:
                            valores.append(texto)

                    data[key_final] = " | ".join(valores)
            
        # CASO 5: Extract date 
        date_div = page.locator("xpath=//div[contains(@class,'panel-footer text-center')]")
        date = date_div.locator("small").first.inner_text().strip()
        data["fecha_consulta_sunat"] = date
            
        #for key, value in data.items():
        #    print(f"\n - {key}: {value}")
        
        return {"status": "ok", "mensaje": "", "tablas": data}
    
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "error", "mensaje": "scraping_failed", "tablas": []}

"""
def main():
    p, browser, page = init_navegador()

    consultar_informacion(page, "20101024645")
    consultar_informacion(page, "20505670443")
    consultar_informacion(page, "20602997783")
    consultar_informacion(page, "23432432452")
    consultar_informacion(page, "20602997783")
    consultar_informacion(page, "asdasdasd")
    consultar_informacion(page, "20101024645")
    consultar_informacion(page, "11213321312")
    consultar_informacion(page, "1")

    cerrar_navegador(p, browser)

if __name__ == "__main__":
    main()
"""
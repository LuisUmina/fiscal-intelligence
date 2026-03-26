from playwright.sync_api import sync_playwright
from config.settings import SUNAT_FIELD_MAPPING, SUNAT_RUC_LOOKUP_URL

def init_browser():
    """Initialize browser once; reusable for batch processing."""

    p = sync_playwright().start()
    browser = p.chromium.launch(channel="chrome", headless=False)
    page = browser.new_page()
    page.on("dialog", handle_dialog)
    return p, browser, page

def close_browser(p, browser):
    """Close browser and Playwright context safely."""
    
    browser.close()
    p.stop()

def click_sunat_safe(page, locator, max_attempts=10):
    """Click a SUNAT element with retries and basic error recovery."""

    for attempt in range(max_attempts):
        try:
            # Trigger click
            locator.click()

            # Wait until DOM content is loaded
            page.wait_for_load_state("domcontentloaded")

            # ERROR 1: SUNAT popup
            if page.locator("xpath=/html/body/div/div[1]").count() > 0:
                popup_text = page.locator("xpath=/html/body/div/div[1]").inner_text()

                if "La aplicación ha retornado el siguiente problema" in popup_text:
                    print(f"[X_1] SUNAT popup error (attempt {attempt+1})")

                    page.locator("xpath=/html/body/div/div[6]/input").click()
                    continue

            # ERROR 2: SUNAT rejection/redirect
            if page.locator("xpath=/html/body").count() > 0:
                body_text = page.locator("xpath=/html/body").inner_text()

                if "The requested URL was rejected" in body_text:
                    print(f"[X_2] SUNAT redirect detected (attempt {attempt+1})")

                    page.locator("xpath=/html/body/a").click()
                    continue

            return True

        except Exception as e:
            print(f"[X] Click error on attempt {attempt+1}: {e}")

    return False

# Alert handling
dialog_message = {"value": None}

def handle_dialog(dialog):
    """Capture and accept browser dialogs triggered by SUNAT."""

    #print(f"[ALERT] {dialog.message}")
    dialog_message["value"] = dialog.message
    dialog.accept()

def fetch_general_company_info(page, ruc):
    """Extract the general taxpayer/company section for a given RUC."""

    dialog_message["value"] = None

    field_mapping = SUNAT_FIELD_MAPPING
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
        # Open page
        page.goto(SUNAT_RUC_LOOKUP_URL)

        # Wait for input
        input_ruc = page.locator("xpath=/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[1]/div/input")
        input_ruc.wait_for()
        input_ruc.fill(ruc)

        # Click "Buscar"
        btn_buscar = page.locator("xpath=/html/body/div[1]/div[2]/div/div[2]/div[2]/form/div[5]/div/button[1]")
        if not click_sunat_safe(page, btn_buscar):
            print(f"[X] Error clicking BUSCAR")
            return {"status": "error", "mensaje": "clic_invalido", "tablas": []}
        
        # Validate alert
        if dialog_message["value"]:
            if "RUC válido" in dialog_message["value"]:
                return {"status": "no_data", "mensaje": "ruc_invalido", "tablas": []}

        # Data panel
        panel = page.locator("xpath=//div[contains(@class,'panel panel-primary')]")
        panel.wait_for(timeout=10000)

        items = panel.locator(".list-group-item")

        for i in range(items.count()):
            item = items.nth(i)

            # CASE 0: Important message
            if item.locator("strong").count() > 0:
                important_text = item.locator("p").first.inner_text().strip()

                if "IMPORTANTE" in important_text:
                    data["mensaje_importante"] = important_text
                    continue

            # Skip if no section header exists
            if item.locator("h4").count() == 0:
                continue
            
            # Section header
            section_key = item.locator("h4").first.inner_text().replace(":", "").strip()

            # Keep only mapped sections
            if section_key not in field_mapping:
                continue

            mapped_key = field_mapping[section_key]

            # CASE 1: value and key are both in h4
            if mapped_key in ["ruc_sunat"]:
                value = item.locator("h4").nth(1).inner_text().strip()
                data[mapped_key]= value

            # CASE 2: value is in p and key is in h4
            elif mapped_key in ["tipo_contribuyente", "nombre_comercial", "estado_contribuyente", "condicion_contribuyente", "domicilio_fiscal", "sistema_contabilidad", "emisor_electronico_desde", "comprobantes_electronicos", "afiliado_ple_desde"]:
                value = item.locator("p").first.inner_text().strip()
                data[mapped_key]= value  

            # CASE 3.1: Two values in same section (p values, h4 key)
            elif mapped_key in ["fecha_inscripcion", "fecha_inicio_actividades"]:
                first_value = item.locator("p").first.inner_text().strip()
                data["fecha_inscripcion"] = first_value

                second_value = item.locator("p").nth(1).inner_text().strip()
                data["fecha_inicio_actividades"] = second_value

            # CASE 3.2: Two values in same section (p values, h4 key)
            elif mapped_key in ["sistema_emision_comprobante", "actividad_comercio_exterior"]:
                first_value = item.locator("p").first.inner_text().strip()
                data["sistema_emision_comprobante"] = first_value

                second_value = item.locator("p").nth(1).inner_text().strip()
                data["actividad_comercio_exterior"] = second_value
            
            # CASE 4: table element
            elif mapped_key in ["actividades_economicas", "comprobantes_pago", "sistema_emision_electronica", "padrones",]:
                # Ensure table exists
                if item.locator("table").count() > 0:
                    table_rows = item.locator("table tr")

                    table_values = []
                    for j in range(table_rows.count()):
                        row_text = table_rows.nth(j).inner_text().strip()
                        if row_text:
                            table_values.append(row_text)

                    data[mapped_key] = " | ".join(table_values)
            
        # CASE 5: extract query date
        footer_div = page.locator("xpath=//div[contains(@class,'panel-footer text-center')]")
        query_date = footer_div.locator("small").first.inner_text().strip()
        data["fecha_consulta_sunat"] = query_date
            
        #for key, value in data.items():
        #    print(f"\n - {key}: {value}")
        
        return {"status": "ok", "mensaje": "", "tablas": data}
    
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"status": "error", "mensaje": "scraping_failed", "tablas": []}

"""
def main():
    p, browser, page = init_browser()

    fetch_general_company_info(page, "20101024645")
    fetch_general_company_info(page, "20505670443")
    fetch_general_company_info(page, "20602997783")
    fetch_general_company_info(page, "23432432452")
    fetch_general_company_info(page, "20602997783")
    fetch_general_company_info(page, "asdasdasd")
    fetch_general_company_info(page, "20101024645")
    fetch_general_company_info(page, "11213321312")
    fetch_general_company_info(page, "1")

    close_browser(p, browser)

if __name__ == "__main__":
    main()
"""
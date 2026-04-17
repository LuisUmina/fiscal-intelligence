import os
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from src.extractors.sunat_consulta_ruc_request import (
    _warmup_sesion,
    consultar_establecimientos,
    consultar_representantes_legales,
    consultar_trabajadores,
    consultar_informacion_historica,
)
from src.extractors.sunat_ruc_scraper import (
    close_browser,
    fetch_general_company_info,
    init_browser,
)
from src.extractors.sunat_ssco import consultar_sujetos_sin_capacidad
from src.extractors.txt_parser import extract_rucs_from_folder
from src.transformers.excel_exporter import (
    exportar_lista_a_excel,
    exportar_rucs_unicos_excel,
    exportar_ruc_a_excel_por_hojas,
)
from src.transformers.preparar_ssco import preparar_ssco_tablas


EmitFn = Callable[..., None]
StopFn = Callable[[], bool]


def _emit(emit: Optional[EmitFn], *event):
    if emit:
        emit(*event)


def _to_error_row(row_vacio: dict) -> dict:
    row = dict(row_vacio)
    if "documento" in row:
        row["documento"] = "ERROR"
    elif "periodo" in row:
        row["periodo"] = "ERROR"
    elif "codigo" in row:
        row["codigo"] = "ERROR"
    return row


def _leer_rucs_desde_excel(ruta_excel: Path, nombre_columna: str = "ruc") -> list[str]:
    """Lee RUCs únicos desde un Excel de una sola columna."""
    df = pd.read_excel(ruta_excel)

    if nombre_columna not in df.columns:
        raise ValueError(f"No se encontro la columna '{nombre_columna}' en {ruta_excel}")

    rucs = (
        df[nombre_columna]
        .dropna()
        .astype(str)
        .str.strip()
    )
    rucs = rucs[rucs != ""]

    return rucs.tolist()


def ejecutar_pipeline_sunat(
    carpeta_txt: str,
    carpeta_output: Optional[str] = None,
    exportar_excel: bool = True,
    emit: Optional[EmitFn] = None,
    should_stop: Optional[StopFn] = None,
):
    """Ejecuta el pipeline completo de SUNAT.

    Parámetros:
    - carpeta_txt: carpeta con TXT de entrada.
    - carpeta_output: carpeta destino para Excel (requerida si exportar_excel=True).
    - exportar_excel: si True, genera archivos Excel al final.
    - emit: callback opcional para eventos de progreso.
      Formato recomendado de eventos: ("step", ...), ("log", ...), ("kpi", ...), ("pipe", ...).
    - should_stop: callback opcional para corte manual; debe retornar True para detener.
    """

    if exportar_excel and not carpeta_output:
        raise ValueError("carpeta_output es obligatoria cuando exportar_excel=True")

    should_stop = should_stop or (lambda: False)

    ok_c = 0
    err_c = 0
    reps = []
    trabs = []
    ests = []
    scraper_general = []
    hist_company_name = []
    hist_taxpayer_status = []
    hist_fiscal_address = []

    # Paso 1 - Lectura de TXT
    _emit(emit, "pipe", "s1", "running")
    _emit(emit, "step", "Leyendo archivos TXT...", 0.04)
    _emit(emit, "log", f"[INFO] Carpeta de entrada: {carpeta_txt}", "info")

    txt_files = [f for f in os.listdir(carpeta_txt) if f.lower().endswith(".txt")]
    _emit(emit, "kpi", "txt", str(len(txt_files)))
    _emit(emit, "log", f"[INFO] TXT encontrados: {len(txt_files)}", "info")
    _emit(emit, "pipe", "s1", "ok")

    # Paso 2 - Extracción de RUCs
    _emit(emit, "pipe", "s2", "running")
    _emit(emit, "step", "Extrayendo RUCs de los TXT...", 0.08)

    rucs, errores_txt = extract_rucs_from_folder(carpeta_txt)
    _emit(emit, "kpi", "rucs", str(len(rucs)))
    _emit(emit, "log", f"[INFO] RUCs unicos extraidos: {len(rucs)}", "info")

    if carpeta_output:
        ruta_rucs_unicos = Path(carpeta_output) / "rucs_unicos.xlsx"
        exportar_rucs_unicos_excel(rucs, ruta_rucs_unicos)
        _emit(emit, "log", f"[OK] rucs_unicos.xlsx generado: {ruta_rucs_unicos}", "ok")

        # A partir de este punto, la fuente de verdad para consultas es rucs_unicos.xlsx.
        rucs = _leer_rucs_desde_excel(ruta_rucs_unicos)
        _emit(emit, "kpi", "rucs", str(len(rucs)))
        _emit(emit, "log", f"[INFO] RUCs cargados desde rucs_unicos.xlsx: {len(rucs)}", "info")

    for item in errores_txt:
        archivo = item.get("archivo", "")
        error_txt = item.get("error", "")
        _emit(emit, "log", f"[WARN] TXT omitido: {archivo} | {error_txt}", "warn")

    _emit(emit, "pipe", "s2", "ok")

    if not rucs:
        _emit(emit, "log", "[WARN] No se encontraron RUCs para procesar.", "warn")
        return {
            "status": "no_data",
            "stopped": False,
            "representantes": reps,
            "trabajadores": trabs,
            "establecimientos": ests,
            "scraper_general": scraper_general,
            "hist_company_name": hist_company_name,
            "hist_taxpayer_status": hist_taxpayer_status,
            "hist_fiscal_address": hist_fiscal_address,
            "errores_txt": errores_txt,
            "ssco": {"status": "no_data", "tablas": []},
            "ok_count": ok_c,
            "error_count": err_c,
        }

    # Paso 3 - Warmup
    _emit(emit, "pipe", "s3", "running")
    _emit(emit, "step", "Inicializando sesion SUNAT...", 0.12)
    _warmup_sesion(rucs[0])
    _emit(emit, "log", "[INFO] Sesion SUNAT inicializada.", "info")
    _emit(emit, "pipe", "s3", "ok")

    # Inicialización de navegador para scraper de información general
    pw, browser, page = None, None, None
    try:
        pw, browser, page = init_browser()
        _emit(emit, "log", "[INFO] Navegador de scraping inicializado.", "info")
    except Exception as exc:
        _emit(emit, "log", f"[WARN] Scraper no disponible: {exc}", "warn")
        pw, browser, page = None, None, None

    # Paso 4 - Consulta masiva
    _emit(emit, "pipe", "s4", "running")
    _emit(emit, "log", f"[INFO] Iniciando consulta masiva: {len(rucs)} RUCs", "info")

    total = len(rucs)
    for i, ruc in enumerate(rucs, 1):
        if should_stop():
            _emit(emit, "log", "[STOP] Proceso detenido.", "warn")
            if pw is not None and browser is not None:
                try:
                    close_browser(pw, browser)
                    _emit(emit, "log", "[INFO] Navegador de scraping cerrado.", "info")
                except Exception as exc:
                    _emit(emit, "log", f"[WARN] No se pudo cerrar navegador scraper: {exc}", "warn")
            return {
                "status": "stopped",
                "stopped": True,
                "representantes": reps,
                "trabajadores": trabs,
                "establecimientos": ests,
                "scraper_general": scraper_general,
                "hist_company_name": hist_company_name,
                "hist_taxpayer_status": hist_taxpayer_status,
                "hist_fiscal_address": hist_fiscal_address,
                "errores_txt": errores_txt,
                "ssco": {"status": "no_data", "tablas": []},
                "ok_count": ok_c,
                "error_count": err_c,
            }

        prog = 0.12 + (i / total) * 0.60
        _emit(emit, "step", f"Consultando SUNAT  {i} de {total}  |  RUC {ruc}", prog)
        _warmup_sesion(ruc)

        consultas = [
            (
                consultar_representantes_legales,
                reps,
                {
                    "ruc": ruc,
                    "documento": "SIN_DATOS",
                    "nro_documento": "",
                    "nombre": "",
                    "cargo": "",
                    "fecha_desde": "",
                },
            ),
            (
                consultar_trabajadores,
                trabs,
                {
                    "ruc": ruc,
                    "periodo": "SIN_DATOS",
                    "nro_trabajadores": "",
                    "nro_pensionistas": "",
                    "nro_prestadores_servicios": "",
                },
            ),
            (
                consultar_establecimientos,
                ests,
                {
                    "ruc": ruc,
                    "codigo": "SIN_DATOS",
                    "tipo_establecimiento": "",
                    "direccion": "",
                    "actividad_economica": "",
                },
            ),
        ]

        for fn, target_list, row_vacio in consultas:
            resp = fn(ruc)
            if resp["status"] == "ok":
                target_list.extend(resp["tablas"])
                ok_c += 1
            elif resp["status"] == "no_data":
                target_list.append(row_vacio)
                err_c += 1
            else:
                target_list.append(_to_error_row(row_vacio))
                err_c += 1

            _emit(emit, "kpi", "ok", str(ok_c))
            _emit(emit, "kpi", "err", str(err_c))

        # Consulta general SUNAT vía scraper (Playwright)
        if page is not None:
            resp_scraper = fetch_general_company_info(page, ruc)
            if resp_scraper["status"] == "ok":
                data_scraper = resp_scraper.get("tablas", {})
                if isinstance(data_scraper, dict):
                    scraper_general.append(data_scraper)
                else:
                    scraper_general.append({"ruc": ruc, "estado_scraper": "FORMATO_INVALIDO"})
                ok_c += 1
            elif resp_scraper["status"] == "no_data":
                scraper_general.append({"ruc": ruc, "estado_scraper": "SIN_DATOS"})
                err_c += 1
            else:
                scraper_general.append({"ruc": ruc, "estado_scraper": "ERROR"})
                err_c += 1

            _emit(emit, "kpi", "ok", str(ok_c))
            _emit(emit, "kpi", "err", str(err_c))

        # Consulta histórica (3 subtablas)
        resp_hist = consultar_informacion_historica(ruc)
        if resp_hist["status"] == "ok":
            tablas_hist = resp_hist.get("tablas", {})
            hist_company_name.extend(tablas_hist.get("hist_company_name", []))
            hist_taxpayer_status.extend(tablas_hist.get("hist_taxpayer_status", []))
            hist_fiscal_address.extend(tablas_hist.get("hist_fiscal_address", []))
            ok_c += 1
        elif resp_hist["status"] == "no_data":
            hist_company_name.append(
                {
                    "ruc": ruc,
                    "nombre_razon_social": "SIN_DATOS",
                    "fecha_baja": "",
                }
            )
            hist_taxpayer_status.append(
                {
                    "ruc": ruc,
                    "condicion_contribuyente": "SIN_DATOS",
                    "fecha_desde": "",
                    "fecha_hasta": "",
                }
            )
            hist_fiscal_address.append(
                {
                    "ruc": ruc,
                    "domicilio_fiscal": "SIN_DATOS",
                    "fecha_baja": "",
                }
            )
            err_c += 1
        else:
            hist_company_name.append(
                {
                    "ruc": ruc,
                    "nombre_razon_social": "ERROR",
                    "fecha_baja": "",
                }
            )
            hist_taxpayer_status.append(
                {
                    "ruc": ruc,
                    "condicion_contribuyente": "ERROR",
                    "fecha_desde": "",
                    "fecha_hasta": "",
                }
            )
            hist_fiscal_address.append(
                {
                    "ruc": ruc,
                    "domicilio_fiscal": "ERROR",
                    "fecha_baja": "",
                }
            )
            err_c += 1

        _emit(emit, "kpi", "ok", str(ok_c))
        _emit(emit, "kpi", "err", str(err_c))

    _emit(emit, "pipe", "s4", "ok")
    _emit(
        emit,
        "log",
        f"[OK] Consulta masiva completada. Correctas: {ok_c} | Sin datos o error: {err_c}",
        "ok",
    )

    # Paso 5 - Padrón SSCO
    _emit(emit, "pipe", "s5", "running")
    _emit(emit, "step", "Descargando padron SSCO...", 0.78)
    _emit(emit, "log", "[INFO] Descargando Sujetos sin Capacidad Operativa...", "info")
    ssco = consultar_sujetos_sin_capacidad()
    _emit(emit, "pipe", "s5", "ok" if ssco["status"] == "ok" else "warn")

    # Paso 6 - Exportación
    if exportar_excel:
        _emit(emit, "pipe", "s6", "running")
        _emit(emit, "step", "Exportando archivos Excel...", 0.90)
        _emit(emit, "log", f"[INFO] Guardando en: {carpeta_output}", "info")

        Path(carpeta_output).mkdir(parents=True, exist_ok=True)
        exportar_ruc_a_excel_por_hojas(
            reps,
            trabs,
            ests,
            f"{carpeta_output}/sunat_ruc_individual.xlsx",
            scraper_general=scraper_general,
            hist_company_name=hist_company_name,
            hist_taxpayer_status=hist_taxpayer_status,
            hist_fiscal_address=hist_fiscal_address,
        )
        _emit(
            emit,
            "log",
            "[OK] sunat_ruc_individual.xlsx generado (hojas: Representantes, Trabajadores, Establecimientos, General, Hist_RazonSocial, Hist_Condicion, Hist_Domicilio).",
            "ok",
        )

        if ssco["status"] == "ok":
            tablas_preparadas = preparar_ssco_tablas(ssco["tablas"])
            exportar_lista_a_excel(
                tablas_preparadas,
                f"{carpeta_output}/Sujetos sin capacidad operativa.xlsx",
            )
            _emit(emit, "log", "[OK] Sujetos sin capacidad operativa.xlsx generado.", "ok")
        else:
            _emit(emit, "log", "[WARN] No se pudo descargar el padron SSCO.", "warn")

        _emit(emit, "pipe", "s6", "ok")

    if pw is not None and browser is not None:
        try:
            close_browser(pw, browser)
            _emit(emit, "log", "[INFO] Navegador de scraping cerrado.", "info")
        except Exception as exc:
            _emit(emit, "log", f"[WARN] No se pudo cerrar navegador scraper: {exc}", "warn")

    return {
        "status": "ok",
        "stopped": False,
        "representantes": reps,
        "trabajadores": trabs,
        "establecimientos": ests,
        "scraper_general": scraper_general,
        "hist_company_name": hist_company_name,
        "hist_taxpayer_status": hist_taxpayer_status,
        "hist_fiscal_address": hist_fiscal_address,
        "errores_txt": errores_txt,
        "ssco": ssco,
        "ok_count": ok_c,
        "error_count": err_c,
    }

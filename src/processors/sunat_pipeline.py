import os
from pathlib import Path
from typing import Callable, Optional

from src.extractors.sunat_consulta_ruc_request import (
    _warmup_sesion,
    consultar_establecimientos,
    consultar_representantes_legales,
    consultar_trabajadores,
)
from src.extractors.sunat_ssco import consultar_sujetos_sin_capacidad
from src.extractors.txt_parser import extract_rucs_from_folder
from src.transformers.excel_exporter import (
    exportar_lista_a_excel,
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

    rucs, rucs_archivos, errores_txt = extract_rucs_from_folder(carpeta_txt)
    _emit(emit, "kpi", "rucs", str(len(rucs)))
    _emit(emit, "log", f"[INFO] RUCs unicos extraidos: {len(rucs)}", "info")

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
            "rucs_archivos": rucs_archivos,
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

    # Paso 4 - Consulta masiva
    _emit(emit, "pipe", "s4", "running")
    _emit(emit, "log", f"[INFO] Iniciando consulta masiva: {len(rucs)} RUCs", "info")

    total = len(rucs)
    for i, ruc in enumerate(rucs, 1):
        if should_stop():
            _emit(emit, "log", "[STOP] Proceso detenido.", "warn")
            return {
                "status": "stopped",
                "stopped": True,
                "representantes": reps,
                "trabajadores": trabs,
                "establecimientos": ests,
                "rucs_archivos": rucs_archivos,
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
            f"{carpeta_output}/DATOS_RUC.xlsx",
            rucs_archivos=rucs_archivos,
        )
        _emit(
            emit,
            "log",
            "[OK] DATOS_RUC.xlsx generado (hojas: Representantes, Trabajadores, Establecimientos).",
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

    return {
        "status": "ok",
        "stopped": False,
        "representantes": reps,
        "trabajadores": trabs,
        "establecimientos": ests,
        "rucs_archivos": rucs_archivos,
        "errores_txt": errores_txt,
        "ssco": ssco,
        "ok_count": ok_c,
        "error_count": err_c,
    }

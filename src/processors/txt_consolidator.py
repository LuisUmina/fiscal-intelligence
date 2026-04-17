from pathlib import Path

import pandas as pd

from config.settings import TXT_FILE_FORMATS
from src.extractors.txt_parser import get_txt_format_type


_COLUMNAS_CONSOLIDADAS = [
    ("periodo", {"801": 1, "804": 3}),
    ("codigo_unico_operacion_cuo", {"801": 2, "804": 4}),
    ("numero_correlativo_asiento_contable", {"801": 3, "804": None}),
    ("fecha_emision", {"801": 4, "804": 5}),
    ("tipo_comprobante_pago_documento", {"801": 6, "804": 7}),
    ("serie_comprobante_pago_documento", {"801": 7, "804": 8}),
    ("numero_comprobante_pago", {"801": 9, "804": 10}),
    ("tipo_documento_identidad_proveedor", {"801": 11, "804": 12}),
    ("numero_ruc_proveedor", {"801": 12, "804": 13}),
    ("proveedor_razon_social", {"801": 13, "804": 14}),
    ("base_imponible_adquisiciones_gravadas", {"801": 14, "804": (15, 17, 19)}),
    ("monto_igv_promocion_municipal", {"801": 15, "804": (16, 18, 20)}),
    ("valor_adquisiciones_no_gravadas", {"801": 20, "804": 21}),
    ("monto_impuesto_selectivo_consumo", {"801": 21, "804": 22}),
    ("impuesto_bolsas_plastico", {"801": 22, "804": 23}),
    ("otros_conceptos_tributos_cargos", {"801": 23, "804": 24}),
    ("importe_total_adquisiciones", {"801": 24, "804": 25}),
    ("codigo_moneda", {"801": 25, "804": 26}),
    ("clasificacion_bienes_servicios_adquiridos", {"801": 35, "804": None}),
]


def _leer_txt_crudo(ruta_txt: str, tipo: str) -> pd.DataFrame:
    config = TXT_FILE_FORMATS[tipo]
    df = pd.read_csv(
        ruta_txt,
        sep=config["txt_delimiter"],
        header=None,
        skiprows=1 if config["has_header"] else 0,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        encoding="latin-1",
    )
    return df


def _obtener_columna(df: pd.DataFrame, numero_columna: int) -> pd.Series:
    indice = numero_columna - 1
    if indice < 0 or indice >= len(df.columns):
        return pd.Series([""] * len(df), index=df.index)

    return df.iloc[:, indice].astype(str).str.strip()


def _sumar_columnas(df: pd.DataFrame, columnas: tuple[int, ...]) -> pd.Series:
    total = pd.Series([0] * len(df), index=df.index, dtype="float64")
    for numero_columna in columnas:
        serie = _obtener_columna(df, numero_columna)
        serie = serie.str.replace(" ", "", regex=False)
        serie = serie.str.replace(",", ".", regex=False)
        total = total + pd.to_numeric(serie, errors="coerce").fillna(0)

    return total


def consolidar_txts(carpeta_txt: str) -> pd.DataFrame:
    filas = []

    for filename in sorted(Path(carpeta_txt).iterdir()):
        if not filename.is_file() or filename.suffix.lower() != ".txt":
            continue

        tipo = get_txt_format_type(filename.name)
        if tipo not in ("801", "804"):
            continue

        df_txt = _leer_txt_crudo(str(filename), tipo)
        fila = {}

        for nombre_final, origenes in _COLUMNAS_CONSOLIDADAS:
            origen = origenes.get(tipo)
            if origen is None:
                fila[nombre_final] = ""
            elif isinstance(origen, tuple):
                fila[nombre_final] = _sumar_columnas(df_txt, origen)
            else:
                fila[nombre_final] = _obtener_columna(df_txt, origen)

        df_consolidado = pd.DataFrame(fila)
        df_consolidado["txt_tipo"] = tipo
        df_consolidado["txt_archivo_origen"] = filename.name
        filas.append(df_consolidado)

    if not filas:
        return pd.DataFrame(columns=[col for col, _ in _COLUMNAS_CONSOLIDADAS] + ["txt_tipo", "txt_archivo_origen"])

    return pd.concat(filas, ignore_index=True)


def exportar_consolidado_txt_excel(carpeta_txt: str, ruta_salida: str) -> pd.DataFrame:
    df = consolidar_txts(carpeta_txt)
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="consolidado_txt", index=False)
    return df
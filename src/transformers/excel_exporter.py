import pandas as pd
import re
from pathlib import Path

_CHARS_ILEGALES = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]')

def _limpiar_df(df):
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(
            lambda v: _CHARS_ILEGALES.sub('', v) if isinstance(v, str) else v
        )
    return df

def exportar_lista_a_excel(filas, ruta_salida):
    """Exporta una lista de dicts a un archivo Excel."""
    df = pd.DataFrame(filas)
    df = _limpiar_df(df)
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(ruta_salida, index=False)


def exportar_ruc_a_excel_por_hojas(reps, trabs, ests, ruta_salida, rucs_archivos=None):
    """Exporta representantes, trabajadores y establecimientos en un mismo Excel con 3 hojas.
    Opcionalmente agrega hoja RUCs_Unicos (RUC + archivo) si se pasa rucs_archivos."""
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        for nombre_hoja, filas in [
            ("Representantes", reps),
            ("Trabajadores", trabs),
            ("Establecimientos", ests),
        ]:
            df = pd.DataFrame(filas)
            df = _limpiar_df(df)
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
        if rucs_archivos:
            df_rucs = pd.DataFrame(rucs_archivos)
            df_rucs = _limpiar_df(df_rucs)
            df_rucs.to_excel(writer, sheet_name="RUCs_Unicos", index=False)


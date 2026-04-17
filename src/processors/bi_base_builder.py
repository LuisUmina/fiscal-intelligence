from pathlib import Path

import pandas as pd


def _buscar_columna_ruc(df: pd.DataFrame) -> str:
    """Busca una columna de RUC de forma simple y tolerante."""
    candidatos = {"ruc", "rucs", "nro_ruc", "numero_ruc", "num_ruc"}

    for col in df.columns:
        normalizada = str(col).strip().lower()
        if normalizada in candidatos:
            return col

    for col in df.columns:
        if "ruc" in str(col).strip().lower():
            return col

    raise ValueError("No se encontro una columna de RUC en el Excel.")


def _normalizar_ruc_serie(serie: pd.Series) -> pd.Series:
    """Normaliza una serie de RUC a texto limpio para joins."""
    return serie.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def _leer_hoja_si_existe(ruta_excel: Path, sheet_name: str) -> pd.DataFrame:
    """Lee una hoja; si no existe devuelve DataFrame vacío."""
    try:
        return pd.read_excel(ruta_excel, sheet_name=sheet_name)
    except ValueError:
        return pd.DataFrame()


def _mantener_solo_filas_validas(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina filas SIN_DATOS o ERROR cuando la hoja tiene una columna de estado."""
    if df.empty or len(df.columns) < 2:
        return df

    segunda_columna = df.columns[1]
    estado = (
        df[segunda_columna]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(" ", "_", regex=False)
    )
    return df[~estado.isin(["SIN_DATOS", "ERROR"])].copy()


def _preparar_join_directo(df: pd.DataFrame, prefijo: str) -> pd.DataFrame:
    """Prepara una hoja para left join directo por RUC."""
    if df.empty:
        return pd.DataFrame(columns=["_join_ruc"])

    col_ruc = _buscar_columna_ruc(df)
    df_join = df.copy()
    df_join = df_join.rename(columns={c: f"{prefijo}{c}" for c in df_join.columns})

    col_ruc_prefijo = f"{prefijo}{col_ruc}"
    df_join[col_ruc_prefijo] = _normalizar_ruc_serie(df_join[col_ruc_prefijo])
    df_join = df_join[df_join[col_ruc_prefijo] != ""]
    df_join = df_join.drop_duplicates(subset=[col_ruc_prefijo]).reset_index(drop=True)
    df_join["_join_ruc"] = df_join[col_ruc_prefijo]

    return df_join


def _preparar_trabajadores_promedio(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa Trabajadores por RUC y calcula el promedio de sus métricas."""
    if df.empty:
        return pd.DataFrame(columns=["_join_ruc"])

    col_ruc = _buscar_columna_ruc(df)
    df_trab = df.copy()
    df_trab["_join_ruc"] = _normalizar_ruc_serie(df_trab[col_ruc])
    df_trab = df_trab[df_trab["_join_ruc"] != ""]

    metricas = [
        "nro_trabajadores",
        "nro_pensionistas",
        "nro_prestadores_servicios",
    ]
    metricas_existentes = [col for col in metricas if col in df_trab.columns]

    if not metricas_existentes:
        return pd.DataFrame(columns=["_join_ruc"])

    for col in metricas_existentes:
        serie = df_trab[col].astype(str).str.strip()
        serie = serie.str.replace(" ", "", regex=False)
        serie = serie.str.replace(",", ".", regex=False)
        df_trab[col] = pd.to_numeric(serie, errors="coerce")

    agg = df_trab.groupby("_join_ruc", as_index=False)[metricas_existentes].mean()
    agg = agg.rename(
        columns={col: f"b2_trabajadores_prom_{col}" for col in metricas_existentes}
    )

    return agg


def _agregar_flags_trabajadores(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega flags SI/NO/N/A para promedios de trabajadores por RUC."""
    mapeo = {
        "b2_trabajadores_prom_nro_trabajadores": "b2_trabajadores_flag_tiene_trabajadores",
        "b2_trabajadores_prom_nro_pensionistas": "b2_trabajadores_flag_tiene_pensionistas",
        "b2_trabajadores_prom_nro_prestadores_servicios": "b2_trabajadores_flag_tiene_prestadores_servicios",
    }

    for col_prom, col_flag in mapeo.items():
        if col_prom not in df.columns:
            continue

        serie = pd.to_numeric(df[col_prom], errors="coerce")
        df[col_flag] = "N/A"
        df.loc[serie.notna() & (serie <= 0), col_flag] = "NO"
        df.loc[serie.notna() & (serie > 0), col_flag] = "SI"

    return df


def _preparar_establecimientos_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa Establecimientos por RUC y calcula cantidad de filas por RUC."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "_join_ruc",
                "b3_establecimientos_cantidad_establecimientos",
                "b3_establecimientos_flag_tiene_establecimientos",
            ]
        )

    col_ruc = _buscar_columna_ruc(df)
    df_est = df.copy()
    df_est["_join_ruc"] = _normalizar_ruc_serie(df_est[col_ruc])
    df_est = df_est[df_est["_join_ruc"] != ""]

    conteo = (
        df_est.groupby("_join_ruc", as_index=False)
        .size()
        .rename(columns={"size": "b3_establecimientos_cantidad_establecimientos"})
    )
    conteo["b3_establecimientos_flag_tiene_establecimientos"] = "NO"
    conteo.loc[
        conteo["b3_establecimientos_cantidad_establecimientos"] > 0,
        "b3_establecimientos_flag_tiene_establecimientos",
    ] = "SI"

    return conteo


def _normalizar_columnas_establecimientos(df: pd.DataFrame) -> pd.DataFrame:
    """Completa valores por defecto de Establecimientos para RUC sin cruce."""
    col_cantidad = "b3_establecimientos_cantidad_establecimientos"
    col_tiene = "b3_establecimientos_flag_tiene_establecimientos"

    if col_cantidad not in df.columns:
        df[col_cantidad] = 0
    df[col_cantidad] = pd.to_numeric(df[col_cantidad], errors="coerce").fillna(0).astype(int)

    if col_tiene not in df.columns:
        df[col_tiene] = "NO"
    df[col_tiene] = df[col_tiene].fillna("NO")

    return df


def _preparar_representantes_resumen(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa Representantes por RUC y calcula cantidad de filas por RUC."""
    if df.empty:
        return pd.DataFrame(
            columns=[
                "_join_ruc",
                "b4_representantes_cantidad_representantes",
                "b4_representantes_flag_tiene_representantes",
            ]
        )

    col_ruc = _buscar_columna_ruc(df)
    df_rep = df.copy()
    df_rep["_join_ruc"] = _normalizar_ruc_serie(df_rep[col_ruc])
    df_rep = df_rep[df_rep["_join_ruc"] != ""]

    conteo = (
        df_rep.groupby("_join_ruc", as_index=False)
        .size()
        .rename(columns={"size": "b4_representantes_cantidad_representantes"})
    )
    conteo["b4_representantes_flag_tiene_representantes"] = "NO"
    conteo.loc[
        conteo["b4_representantes_cantidad_representantes"] > 0,
        "b4_representantes_flag_tiene_representantes",
    ] = "SI"

    return conteo


def _normalizar_columnas_representantes(df: pd.DataFrame) -> pd.DataFrame:
    """Completa valores por defecto de Representantes para RUC sin cruce."""
    col_cantidad = "b4_representantes_cantidad_representantes"
    col_tiene = "b4_representantes_flag_tiene_representantes"

    if col_cantidad not in df.columns:
        df[col_cantidad] = 0
    df[col_cantidad] = pd.to_numeric(df[col_cantidad], errors="coerce").fillna(0).astype(int)

    if col_tiene not in df.columns:
        df[col_tiene] = "NO"
    df[col_tiene] = df[col_tiene].fillna("NO")

    return df


def construir_base_bi_basica(
    carpeta_output: str,
    nombre_archivo: str = "base_bi.xlsx",
) -> dict:
    """Construye base BI con left joins simples y legibles por RUC.

    Orden de cruces:
    1. Base desde rucs_unicos.xlsx
    2. Left join con sunat_ruc_masivo.xlsx (hoja Correctos)
    3. Left join con sunat_ruc_individual.xlsx (hoja General)
    4. Left join con sunat_ruc_individual.xlsx (hoja Trabajadores, promedios por RUC)
    5. Left join con sunat_ruc_individual.xlsx (hoja Establecimientos, conteo por RUC)
    6. Left join con sunat_ruc_individual.xlsx (hoja Representantes, conteo por RUC)
    """
    carpeta = Path(carpeta_output)
    ruta_rucs_unicos = carpeta / "rucs_unicos.xlsx"
    ruta_datos_ruc = carpeta / "sunat_ruc_individual.xlsx"
    ruta_consolidado = carpeta / "sunat_ruc_masivo.xlsx"
    ruta_salida = carpeta / nombre_archivo

    if not ruta_rucs_unicos.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_rucs_unicos}")
    if not ruta_datos_ruc.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_datos_ruc}")
    if not ruta_consolidado.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta_consolidado}")

    # Base izquierda: rucs_unicos.xlsx
    df_rucs = pd.read_excel(ruta_rucs_unicos)
    col_ruc_unicos = _buscar_columna_ruc(df_rucs)
    col_b0_ruc = f"b0_{col_ruc_unicos}"

    base_bi = df_rucs[[col_ruc_unicos]].copy()
    base_bi = base_bi.rename(columns={col_ruc_unicos: col_b0_ruc})
    base_bi[col_b0_ruc] = _normalizar_ruc_serie(base_bi[col_b0_ruc])
    base_bi = base_bi[base_bi[col_b0_ruc] != ""]
    base_bi = base_bi.drop_duplicates(subset=[col_b0_ruc]).reset_index(drop=True)
    base_bi["_join_ruc"] = base_bi[col_b0_ruc]

    # Left join 1: base_rucs <- sunat_ruc_masivo.xlsx (Correctos)
    df_masivo = _leer_hoja_si_existe(ruta_consolidado, "Correctos")
    df_masivo_join = _preparar_join_directo(df_masivo, "b1_")
    base_bi = base_bi.merge(df_masivo_join, on="_join_ruc", how="left")

    # Left join 2: base_rucs <- sunat_ruc_individual.xlsx (General)
    df_general = _leer_hoja_si_existe(ruta_datos_ruc, "General")
    df_general = _mantener_solo_filas_validas(df_general)
    df_general_join = _preparar_join_directo(df_general, "b2_general_")
    base_bi = base_bi.merge(df_general_join, on="_join_ruc", how="left")

    # Left join 3: base_rucs <- sunat_ruc_individual.xlsx (Trabajadores, promedio por RUC)
    df_trabajadores = _leer_hoja_si_existe(ruta_datos_ruc, "Trabajadores")
    df_trabajadores = _mantener_solo_filas_validas(df_trabajadores)
    df_trabajadores_join = _preparar_trabajadores_promedio(df_trabajadores)
    base_bi = base_bi.merge(df_trabajadores_join, on="_join_ruc", how="left")
    base_bi = _agregar_flags_trabajadores(base_bi)

    # Left join 4: base_rucs <- sunat_ruc_individual.xlsx (Establecimientos, conteo por RUC)
    df_establecimientos = _leer_hoja_si_existe(ruta_datos_ruc, "Establecimientos")
    df_establecimientos = _mantener_solo_filas_validas(df_establecimientos)
    df_establecimientos_join = _preparar_establecimientos_resumen(df_establecimientos)
    base_bi = base_bi.merge(df_establecimientos_join, on="_join_ruc", how="left")
    base_bi = _normalizar_columnas_establecimientos(base_bi)

    # Left join 5: base_rucs <- sunat_ruc_individual.xlsx (Representantes, conteo por RUC)
    df_representantes = _leer_hoja_si_existe(ruta_datos_ruc, "Representantes")
    df_representantes = _mantener_solo_filas_validas(df_representantes)
    df_representantes_join = _preparar_representantes_resumen(df_representantes)
    base_bi = base_bi.merge(df_representantes_join, on="_join_ruc", how="left")
    base_bi = _normalizar_columnas_representantes(base_bi)

    base_bi = base_bi.drop(columns=["_join_ruc"])
    columnas_ordenadas = [col_b0_ruc] + [c for c in base_bi.columns if c != col_b0_ruc]
    base_bi = base_bi[columnas_ordenadas]

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        base_bi.to_excel(writer, sheet_name="base_bi", index=False)

    col_data = [c for c in base_bi.columns if c != col_b0_ruc]
    coincidencias = int(base_bi[col_data].notna().any(axis=1).sum()) if col_data else 0

    return {
        "archivo_salida": str(ruta_salida),
        "total_rucs": int(len(base_bi)),
        "coincidencias_correctos": coincidencias,
    }

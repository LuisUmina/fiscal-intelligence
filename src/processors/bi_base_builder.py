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


def construir_base_bi_basica(
    carpeta_output: str,
    nombre_archivo: str = "BASE_BI.xlsx",
) -> dict:
    """Construye una base BI inicial:
    - b0_: base de RUCs unicos
    - b1_: join con hoja Correctos
    - b2_trabajadores_: join agregado por RUC desde hoja Trabajadores
    - b3_general_: join con hoja General
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

    df_rucs = pd.read_excel(ruta_rucs_unicos)
    col_ruc_unicos = _buscar_columna_ruc(df_rucs)
    col_b0_ruc = f"b0_{col_ruc_unicos}"

    base_rucs = df_rucs[[col_ruc_unicos]].copy()
    base_rucs = base_rucs.rename(columns={col_ruc_unicos: col_b0_ruc})
    base_rucs[col_b0_ruc] = base_rucs[col_b0_ruc].astype(str).str.strip()
    base_rucs = base_rucs[base_rucs[col_b0_ruc] != ""]
    base_rucs = base_rucs.drop_duplicates(subset=[col_b0_ruc]).reset_index(drop=True)
    base_rucs["_join_ruc"] = base_rucs[col_b0_ruc]

    df_correctos = pd.read_excel(ruta_consolidado, sheet_name="Correctos")
    if df_correctos.empty:
        df_correctos = pd.DataFrame(columns=["b1_ruc", "_join_ruc"])
    else:
        col_ruc_correctos = _buscar_columna_ruc(df_correctos)
        df_correctos = df_correctos.copy()
        df_correctos = df_correctos.rename(columns={c: f"b1_{c}" for c in df_correctos.columns})
        col_b1_ruc = f"b1_{col_ruc_correctos}"

        df_correctos[col_b1_ruc] = df_correctos[col_b1_ruc].astype(str).str.strip()
        df_correctos = df_correctos[df_correctos[col_b1_ruc] != ""]
        df_correctos = df_correctos.drop_duplicates(subset=[col_b1_ruc]).reset_index(drop=True)
        df_correctos["_join_ruc"] = df_correctos[col_b1_ruc]

    base_bi = base_rucs.merge(df_correctos, on="_join_ruc", how="left")

    # Rellenar NaN en b1_ con "SIN_DATOS"
    cols_b1 = [c for c in base_bi.columns if c.startswith("b1_")]
    for col in cols_b1:
        base_bi[col] = base_bi[col].fillna("SIN_DATOS")

    # Join b2: Trabajadores (agregado por RUC para evitar duplicados por periodo)
    df_trabajadores = pd.read_excel(ruta_datos_ruc, sheet_name="Trabajadores")
    if not df_trabajadores.empty:
        col_ruc_trab = _buscar_columna_ruc(df_trabajadores)
        df_trabajadores = df_trabajadores.copy()
        df_trabajadores["_join_ruc"] = df_trabajadores[col_ruc_trab].astype(str).str.strip()
        df_trabajadores = df_trabajadores[df_trabajadores["_join_ruc"] != ""]

        metricas = [
            "nro_trabajadores",
            "nro_pensionistas",
            "nro_prestadores_servicios",
        ]
        metricas_existentes = [col for col in metricas if col in df_trabajadores.columns]

        for col in metricas_existentes:
            serie = df_trabajadores[col].astype(str).str.strip()
            serie = serie.str.replace(" ", "", regex=False)
            serie = serie.str.replace(",", ".", regex=False)
            df_trabajadores[col] = pd.to_numeric(serie, errors="coerce")

        if metricas_existentes:
            agg = df_trabajadores.groupby("_join_ruc", as_index=False)[metricas_existentes].mean()

            rename_prom = {
                col: f"b2_trabajadores_prom_{col}" for col in metricas_existentes
            }
            agg = agg.rename(columns=rename_prom)

            for col in metricas_existentes:
                col_prom = f"b2_trabajadores_prom_{col}"
                col_flg = f"b2_trabajadores_flg_{col}"
                agg[col_flg] = (agg[col_prom] > 0).astype(int)

            base_bi = base_bi.merge(agg, on="_join_ruc", how="left")

    # Join b3: General (sin agregacion, un registro por RUC)
    df_scraper = pd.read_excel(ruta_datos_ruc, sheet_name="General")
    if not df_scraper.empty:
        col_ruc_scraper = _buscar_columna_ruc(df_scraper)
        df_scraper = df_scraper.copy()
        df_scraper = df_scraper.rename(columns={c: f"b3_general_{c}" for c in df_scraper.columns})
        col_b3_ruc = f"b3_general_{col_ruc_scraper}"

        df_scraper[col_b3_ruc] = df_scraper[col_b3_ruc].astype(str).str.strip()
        df_scraper = df_scraper[df_scraper[col_b3_ruc] != ""]
        df_scraper = df_scraper.drop_duplicates(subset=[col_b3_ruc]).reset_index(drop=True)
        df_scraper["_join_ruc"] = df_scraper[col_b3_ruc]

        base_bi = base_bi.merge(df_scraper, on="_join_ruc", how="left")

    # Rellenar NaN en b3_general con "SIN_DATOS"
    cols_b3 = [c for c in base_bi.columns if c.startswith("b3_general_")]
    for col in cols_b3:
        base_bi[col] = base_bi[col].fillna("SIN_DATOS")

    # Rellenar NaN en b2_trabajadores
    # Promedios: convertir a texto y rellenar con "SIN_DATOS" donde no hay cruce
    for col in base_bi.columns:
        if col.startswith("b2_trabajadores_prom_"):
            base_bi[col] = base_bi[col].astype(object)
            base_bi[col] = base_bi[col].fillna("SIN_DATOS")
        elif col.startswith("b2_trabajadores_flg_"):
            base_bi[col] = base_bi[col].fillna(-1).astype(int)

    # Rellenar resto de b2_ (si las hay)
    cols_b2_otros = [c for c in base_bi.columns if c.startswith("b2_") and not c.startswith("b2_trabajadores_")]
    for col in cols_b2_otros:
        if base_bi[col].dtype == "object":
            base_bi[col] = base_bi[col].fillna("SIN_DATOS")
        else:
            base_bi[col] = base_bi[col].fillna(0)

    base_bi = base_bi.drop(columns=["_join_ruc"])

    columnas_ordenadas = [col_b0_ruc] + [c for c in base_bi.columns if c != col_b0_ruc]
    base_bi = base_bi[columnas_ordenadas]

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        base_bi.to_excel(writer, sheet_name="Base_BI", index=False)

    col_data = [c for c in base_bi.columns if c != col_b0_ruc]
    if col_data:
        coincidencias = int(base_bi[col_data].notna().any(axis=1).sum())
    else:
        coincidencias = 0

    return {
        "archivo_salida": str(ruta_salida),
        "total_rucs": int(len(base_bi)),
        "coincidencias_correctos": coincidencias,
    }

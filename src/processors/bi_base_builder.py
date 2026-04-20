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
    """Agrega flags SI/NO para promedios de trabajadores por RUC."""
    mapeo = {
        "b2_trabajadores_prom_nro_trabajadores": "b2_trabajadores_flag_tiene_trabajadores",
        "b2_trabajadores_prom_nro_pensionistas": "b2_trabajadores_flag_tiene_pensionistas",
        "b2_trabajadores_prom_nro_prestadores_servicios": "b2_trabajadores_flag_tiene_prestadores_servicios",
    }

    for col_prom, col_flag in mapeo.items():
        if col_prom not in df.columns:
            continue

        serie = pd.to_numeric(df[col_prom], errors="coerce")
        df[col_flag] = "NO"
        df.loc[serie.notna() & (serie > 0), col_flag] = "SI"

    return df


def _normalizar_columnas_trabajadores(df: pd.DataFrame) -> pd.DataFrame:
    """Completa valores por defecto de Trabajadores para RUC sin cruce."""
    promedios = [
        "b2_trabajadores_prom_nro_trabajadores",
        "b2_trabajadores_prom_nro_pensionistas",
        "b2_trabajadores_prom_nro_prestadores_servicios",
    ]

    for col in promedios:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

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


def _consolidar_estado_condicion_contribuyente(df: pd.DataFrame) -> pd.DataFrame:
    """Consolida estado y condicion del contribuyente entre masivo e individual."""
    col_estado_v1 = "b1_Estado del Contribuyente"
    col_condicion_v1 = "b1_Condicion del Contribuyente"
    col_estado_v2 = "b2_general_estado_contribuyente"
    col_condicion_v2 = "b2_general_condicion_contribuyente"

    col_estado_final = "b1_b2_estado_contribuyente_final"
    col_condicion_final = "b1_b2_condicion_contribuyente_final"
    col_estado_coincide = "b1_b2_estado_contribuyente_coincide"
    col_condicion_coincide = "b1_b2_condicion_contribuyente_coincide"

    def _serie_texto(nombre_columna: str) -> pd.Series:
        if nombre_columna not in df.columns:
            return pd.Series([""] * len(df), index=df.index)
        return df[nombre_columna].fillna("").astype(str).str.strip()

    estado_v1 = _serie_texto(col_estado_v1)
    condicion_v1 = _serie_texto(col_condicion_v1)
    estado_v2 = _serie_texto(col_estado_v2)
    condicion_v2 = _serie_texto(col_condicion_v2)

    estado_tiene_dato = estado_v1.ne("") | estado_v2.ne("")
    condicion_tiene_dato = condicion_v1.ne("") | condicion_v2.ne("")

    df[col_estado_coincide] = ""
    df.loc[estado_tiene_dato, col_estado_coincide] = "NO"
    df.loc[estado_v1.ne("") & estado_v2.ne("") & (estado_v1 == estado_v2), col_estado_coincide] = "SI"

    df[col_condicion_coincide] = ""
    df.loc[condicion_tiene_dato, col_condicion_coincide] = "NO"
    df.loc[condicion_v1.ne("") & condicion_v2.ne("") & (condicion_v1 == condicion_v2), col_condicion_coincide] = "SI"

    df[col_estado_final] = estado_v2.where(estado_v2.ne(""), estado_v1)
    df.loc[~estado_tiene_dato, col_estado_final] = ""

    df[col_condicion_final] = condicion_v2.where(condicion_v2.ne(""), condicion_v1)
    df.loc[~condicion_tiene_dato, col_condicion_final] = ""

    return df


def _agregar_abreviatura_tipo_contribuyente(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega la abreviatura del tipo de contribuyente junto a la columna original."""
    col_origen = "b1_Tipo de Contribuyente"
    col_destino = "b1_tipo_contribuyente_abreviatura"

    if col_origen not in df.columns:
        return df

    serie_origen = df[col_origen].fillna("").astype(str).str.strip().str.upper()

    reglas_exactas = {
        "E.I.R.L.": ["E.I.R.L.", "EMPRESA INDIVIDUAL DE RESP. LTDA", "EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"],
        "S.A.": ["SOCIEDAD ANONIMA"],
        "S.R.L.": ["SOC.COM.RESPONS. LTDA", "SOCIEDAD COMERCIAL DE RESPONSABILIDAD LIMITADA"],
        "S.A.C.": ["SOCIEDAD ANONIMA CERRADA"],
        "P.N.": ["PERSONA NATURAL CON NEGOCIO"],
        "Asociación": ["ASOCIACION"],
        "S.A.A.": ["SOCIEDAD ANONIMA ABIERTA"],
        "EMP. ESTATAL": ["EMPRESA ESTATAL DE DERECHO PRIVADO"],
        "ENT. AUXILIO": ["ENTIDADES DE AUXILIO MUTUO"],
        "INT. PUBLICAS": ["INSTITUCIONES PUBLICAS"],
        "AG. EXTRANJ.": ["SUCURSALES O AG. DE EMP. EXTRANJ."],
        "S.C.": ["SOCIEDAD CIVIL"],
    }

    reglas_contiene = [
        ("P.N.", "PERSONA NATURAL CON NEGOCIO"),
        ("J.P.", "JUNTA DE PROPIETARIOS"),
        ("GOB.REG.", "GOBIERNO REGIONAL LOCAL"),
        ("COMU. NAT.", "COMUNIDAD CAMPESINA NATIVA"),
        ("EMP. ECN. MXTA", "EMPRESA DE ECONOMIA MIXTA"),
        ("COOP. SAIS", "COOPERATIVAS SAIS CAPS"),
        ("GOB. CENT.", "GOBIERNO CENTRAL"),
    ]

    def _abreviar_tipo(valor: str) -> str:
        texto = str(valor).strip().upper()
        if not texto:
            return ""

        for abreviatura, variantes in reglas_exactas.items():
            if texto in variantes:
                return abreviatura

        for abreviatura, patron in reglas_contiene:
            if patron in texto:
                return abreviatura

        return "Otros"

    serie_abreviada = serie_origen.apply(_abreviar_tipo)

    df[col_destino] = serie_abreviada

    columnas = list(df.columns)
    if col_destino in columnas:
        columnas.remove(col_destino)
        indice_origen = columnas.index(col_origen)
        columnas.insert(indice_origen + 1, col_destino)
        df = df[columnas]

    return df


def _obtener_valores_ssco(ruta_ssco: Path) -> list[str]:
    """Devuelve todos los valores SSCO de RUC y representante legal limpio."""
    if not ruta_ssco.exists():
        return []

    df_ssco = pd.read_excel(ruta_ssco)
    if df_ssco.empty:
        return []

    col_ruc_ssco = None
    col_rep_ssco = None
    for col in df_ssco.columns:
        normalizada = str(col).strip().lower()
        if col_ruc_ssco is None and normalizada == "ruc":
            col_ruc_ssco = col
        if col_rep_ssco is None and normalizada == "ruc o documento de identidad del representante legal (1)_limpia":
            col_rep_ssco = col

    valores_ssco = []
    if col_ruc_ssco is not None:
        valores_ssco.extend(df_ssco[col_ruc_ssco].fillna("").astype(str).tolist())
    if col_rep_ssco is not None:
        valores_ssco.extend(df_ssco[col_rep_ssco].fillna("").astype(str).tolist())

    return [v for v in valores_ssco if v != ""]


def _agregar_flag_ssco_empresa(base_bi: pd.DataFrame, col_ruc_base: str, valores_ssco: list[str]) -> pd.DataFrame:
    """Agrega flag SI/NO si un valor SSCO esta contenido en el RUC base."""
    col_flag = "b5_ssco_flag_empresa"
    base_bi[col_flag] = "NO"

    if not valores_ssco:
        return base_bi

    base_bi[col_flag] = base_bi[col_ruc_base].astype(str).apply(
        lambda ruc: "SI" if any(valor_ssco in ruc for valor_ssco in valores_ssco) else "NO"
    )

    return base_bi


def _agregar_flag_ssco_representante_legal(
    base_bi: pd.DataFrame,
    df_representantes: pd.DataFrame,
    col_ruc_base: str,
    valores_ssco: list[str],
) -> pd.DataFrame:
    """Agrega flag y detalle de representantes legales encontrados en SSCO."""
    col_flag = "b5_ssco_flag_representante_legal"
    col_docs = "b5_ssco_docs_representante_legal"
    col_nombres = "b5_ssco_nombres_representante_legal"

    base_bi[col_flag] = "NO"
    base_bi[col_docs] = ""
    base_bi[col_nombres] = ""

    if df_representantes.empty or not valores_ssco:
        return base_bi

    if "nro_documento" not in df_representantes.columns or "nombre" not in df_representantes.columns:
        return base_bi

    def _limpiar_documento(valor: str) -> str:
        texto = str(valor)
        return texto.replace(".0", "")

    col_ruc_rep = _buscar_columna_ruc(df_representantes)
    df_rep = df_representantes[[col_ruc_rep, "nro_documento", "nombre"]].copy()
    df_rep[col_ruc_rep] = _normalizar_ruc_serie(df_rep[col_ruc_rep])
    df_rep["nro_documento"] = df_rep["nro_documento"].fillna("").astype(str).apply(_limpiar_documento)
    df_rep["nombre"] = df_rep["nombre"].fillna("").astype(str)

    encontrados_por_ruc: dict[str, dict[str, list[str]]] = {}

    for _, fila in df_rep.iterrows():
        ruc = fila[col_ruc_rep]
        nro_documento = fila["nro_documento"]
        nombre = fila["nombre"]

        if nro_documento == "":
            continue

        if any(valor_ssco in nro_documento for valor_ssco in valores_ssco):
            if ruc not in encontrados_por_ruc:
                encontrados_por_ruc[ruc] = {"docs": [], "nombres": []}

            if nro_documento not in encontrados_por_ruc[ruc]["docs"]:
                encontrados_por_ruc[ruc]["docs"].append(nro_documento)
            if nombre not in encontrados_por_ruc[ruc]["nombres"]:
                encontrados_por_ruc[ruc]["nombres"].append(nombre)

    for idx, fila in base_bi.iterrows():
        ruc_base = str(fila[col_ruc_base])
        match = encontrados_por_ruc.get(ruc_base)
        if match:
            base_bi.at[idx, col_flag] = "SI"
            base_bi.at[idx, col_docs] = "|".join(match["docs"])
            base_bi.at[idx, col_nombres] = "|".join(match["nombres"])

    return base_bi


def _agregar_estado_observacion(base_bi: pd.DataFrame) -> pd.DataFrame:
    """Agrega columna final de observacion por capas de riesgo y SSCO."""
    col_obs = "b6_estado_observacion"

    col_trab = "b2_trabajadores_flag_tiene_trabajadores"
    col_est = "b3_establecimientos_flag_tiene_establecimientos"
    col_estado_final = "b1_b2_estado_contribuyente_final"
    col_cond_final = "b1_b2_condicion_contribuyente_final"
    col_ssco_empresa = "b5_ssco_flag_empresa"
    col_ssco_rep = "b5_ssco_flag_representante_legal"

    def _serie_texto(nombre_columna: str) -> pd.Series:
        if nombre_columna not in base_bi.columns:
            return pd.Series([""] * len(base_bi), index=base_bi.index)
        return base_bi[nombre_columna].fillna("").astype(str).str.strip().str.upper()

    trabajadores = _serie_texto(col_trab)
    establecimientos = _serie_texto(col_est)
    estado_final = _serie_texto(col_estado_final)
    condicion_final = _serie_texto(col_cond_final)
    ssco_empresa = _serie_texto(col_ssco_empresa)
    ssco_rep = _serie_texto(col_ssco_rep)

    # CAPA 1
    base_bi[col_obs] = "Sin observacion"
    riesgo_capa_1 = (
        ((trabajadores == "NO") & (establecimientos == "NO"))
        | (estado_final != "ACTIVO")
        | (condicion_final != "HABIDO")
    )
    base_bi.loc[riesgo_capa_1, col_obs] = "Con riesgo de capacidad operativa"

    # CAPA 2: SSCO directo (prioridad maxima)
    ssco_directo = ssco_empresa == "SI"
    base_bi.loc[ssco_directo, col_obs] = "Sujetos sin capacidad operativa"

    # CAPA 3: representante legal SSCO (si no fue SSCO directo)
    riesgo_rep_ssco = (ssco_rep == "SI") & (~ssco_directo)
    base_bi.loc[riesgo_rep_ssco, col_obs] = "Con riesgo de capacidad operativa"

    return base_bi


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
    ruta_ssco = carpeta / "sunat_ssco.xlsx"
    ruta_consolidado_txt = carpeta / "consolidado_txt.xlsx"
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
    base_bi = _consolidar_estado_condicion_contribuyente(base_bi)
    base_bi = _agregar_abreviatura_tipo_contribuyente(base_bi)

    # Left join 3: base_rucs <- sunat_ruc_individual.xlsx (Trabajadores, promedio por RUC)
    df_trabajadores = _leer_hoja_si_existe(ruta_datos_ruc, "Trabajadores")
    df_trabajadores = _mantener_solo_filas_validas(df_trabajadores)
    df_trabajadores_join = _preparar_trabajadores_promedio(df_trabajadores)
    base_bi = base_bi.merge(df_trabajadores_join, on="_join_ruc", how="left")
    base_bi = _agregar_flags_trabajadores(base_bi)
    base_bi = _normalizar_columnas_trabajadores(base_bi)

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

    valores_ssco = _obtener_valores_ssco(ruta_ssco)

    # Columna calculada SSCO empresa: compara valor_ssco in b0_ruc
    base_bi = _agregar_flag_ssco_empresa(base_bi, col_b0_ruc, valores_ssco)

    # Columna calculada SSCO representante legal: compara valor_ssco in nro_documento
    base_bi = _agregar_flag_ssco_representante_legal(
        base_bi,
        df_representantes,
        col_b0_ruc,
        valores_ssco,
    )
    base_bi = _agregar_estado_observacion(base_bi)

    base_bi = base_bi.drop(columns=["_join_ruc"])
    columnas_ordenadas = [col_b0_ruc] + [c for c in base_bi.columns if c != col_b0_ruc]
    base_bi = base_bi[columnas_ordenadas]

    df_consolidado_txt = pd.DataFrame()
    if ruta_consolidado_txt.exists():
        try:
            df_consolidado_txt = pd.read_excel(ruta_consolidado_txt, sheet_name="consolidado_txt")
        except ValueError:
            df_consolidado_txt = pd.read_excel(ruta_consolidado_txt)

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        base_bi.to_excel(writer, sheet_name="base_bi", index=False)
        df_consolidado_txt.to_excel(writer, sheet_name="consolidado_txt", index=False)

    col_data = [c for c in base_bi.columns if c != col_b0_ruc]
    coincidencias = int(base_bi[col_data].notna().any(axis=1).sum()) if col_data else 0

    return {
        "archivo_salida": str(ruta_salida),
        "total_rucs": int(len(base_bi)),
        "coincidencias_correctos": coincidencias,
    }

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

_MAP_TIPO_COMPROBANTE = {
    "0": "Otros",
    "01": "Factura",
    "02": "Recibo por Honorarios",
    "03": "Boleta de Venta",
    "04": "Liquidacion de compra",
    "05": "Boletos de Transporte Aereo",
    "06": "Carta de porte aereo por el servicio de transporte de carga aerea",
    "07": "Nota de credito",
    "08": "Nota de debito",
    "09": "Guia de remision - Remitente",
    "10": "Recibo por Arrendamiento",
    "11": "Recibo por Arrendamiento",
    "12": "Ticket o cinta emitido por maquina registradora",
    "13": "Documentos emitidos por empresas del sistema financiero y de seguros, y cooperativas de ahorro y credito no autorizadas a captar recursos del publico, bajo control de la SBS y AFP",
    "14": "Recibo por servicios publicos",
    "15": "Boletos emitidos por servicio de transporte terrestre regular urbano de pasajeros y ferroviario publico en via ferrea local",
    "16": "Boletos de viaje de empresas de transporte nacional de pasajeros en rutas autorizadas, via terrestre o ferroviario publico no emitido por medios electronicos (BVME)",
    "17": "Documento emitido por la Iglesia Catolica por arrendamiento de bienes inmuebles",
    "18": "Documento emitido por AFP bajo supervision de la SBS y AFP",
    "19": "Boleto o entrada por atracciones y espectaculos publicos",
    "20": "Comprobante de Retencion",
    "21": "Conocimiento de embarque por servicio de transporte de carga maritima",
    "22": "Comprobante por Operaciones No Habituales",
    "23": "Polizas de Adjudicacion por remate o adjudicacion de bienes por venta forzada",
    "24": "Certificado de pago de regalias emitidas por PERUPETRO S.A",
    "25": "Documento de Atribucion (Ley IGV e ISC, Art. 19, ultimo parrafo, R.S. N 022-98-SUNAT)",
    "26": "Recibo por pago de tarifa por uso de agua superficial con fines agrarios y cuota para obra o actividad acordada por Asamblea General de Comision de Regantes",
    "27": "Seguro Complementario de Trabajo de Riesgo",
    "28": "Documentos emitidos por servicios aeroportuarios prestados a pasajeros mediante etiquetas autoadhesivas",
    "29": "Documentos emitidos por COFOPRI como oferta de venta de terrenos, subastas publicas y retribucion de servicios",
    "30": "Documentos emitidos por empresas adquirentes en sistemas de pago con tarjetas de credito y debito",
    "31": "Guia de Remision - Transportista",
    "32": "Documentos emitidos por empresas recaudadoras de la Garantia de Red Principal (Ley N 27133)",
    "33": "Manifiesto de Pasajeros",
    "34": "Documento del Operador",
    "35": "Documento del Participe",
    "36": "Recibo de Distribucion de Gas Natural",
    "37": "Documentos emitidos por concesionarios de revisiones tecnicas vehiculares",
    "40": "Comprobante de Percepcion",
    "41": "Comprobante de Percepcion - Venta interna",
    "42": "Documentos emitidos por empresas adquirentes en sistemas de pago mediante tarjetas de credito emitidas por ellas mismas",
    "43": "Boletos emitidos por companias de aviacion comercial para transporte aereo no regular y especial de pasajeros",
    "44": "Billetes de loteria, rifas y apuestas",
    "45": "Documentos emitidos por centros educativos y culturales, universidades, asociaciones y fundaciones en actividades no gravadas con tributos SUNAT",
    "46": "Formulario de pago",
    "48": "Comprobante de Operaciones - Ley N 29972",
    "49": "Constancia de Deposito - IVAP (Ley 28211)",
    "50": "DUA",
    "51": "Poliza o DUI Fraccionada",
    "52": "Despacho Simplificado - Importacion Simplificada",
    "53": "Declaracion de Mensajeria o Courier",
    "54": "Liquidacion de Cobranza",
    "55": "BVME para transporte ferroviario de pasajeros",
    "56": "Comprobante de pago SEAE",
    "87": "Nota de Credito Especial",
    "88": "Nota de Debito Especial",
    "89": "Nota de Ajuste de Operaciones - Ley N 29972",
    "91": "Comprobante de No Domiciliado",
    "96": "Exceso de credito fiscal por retiro de bienes",
    "97": "Nota de Credito - No Domiciliado",
    "98": "Nota de Debito - No Domiciliado",
}

_MAP_CLASIFICACION_BIENES = {
    "1": (
        "MERCADERIA, MATERIA PRIMA, SUMINISTRO, ENVASES Y EMBALAJES",
        "MERCADERIA",
    ),
    "2": (
        "ACTIVO FIJO",
        "ACTIVO FIJO",
    ),
    "3": (
        "OTROS ACTIVOS NO CONSIDERADOS EN LOS NUMERALES 1 Y 2",
        "OTROS ACTIVOS",
    ),
    "4": (
        "GASTOS DE EDUCACION, RECREACION, SALUD, CULTURALES, REPRESENTACION, CAPACITACION, VIAJE, MANTENIMIENTO DE VEHICULO Y PREMIOS",
        "GASTOS SUJETOS A LIMITE",
    ),
    "5": (
        "OTROS GASTOS NO INCLUIDOS EN EL NUMERAL 4",
        "OTROS GASTOS",
    ),
}


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


def _normalizar_codigo_documento(valor: str) -> str:
    texto = str(valor).strip()
    if not texto:
        return ""

    texto = texto.replace(".0", "")
    if texto.isdigit():
        if texto == "0":
            return "0"
        if len(texto) == 1:
            return f"0{texto}"
    return texto


def _agregar_leyendas(df: pd.DataFrame) -> pd.DataFrame:
    if "tipo_comprobante_pago_documento" in df.columns:
        codigos_doc = df["tipo_comprobante_pago_documento"].astype(str).apply(_normalizar_codigo_documento)
        df["tipo_comprobante_pago_documento_descripcion"] = codigos_doc.map(_MAP_TIPO_COMPROBANTE).fillna("")

    if "clasificacion_bienes_servicios_adquiridos" in df.columns:
        codigos_clase = (
            df["clasificacion_bienes_servicios_adquiridos"]
            .astype(str)
            .str.strip()
            .str.replace(".0", "", regex=False)
        )
        interp = codigos_clase.map(_MAP_CLASIFICACION_BIENES)
        df["clasificacion_bienes_servicios_adquiridos_descripcion_1"] = interp.apply(lambda x: x[0] if isinstance(x, tuple) else "")
        df["clasificacion_bienes_servicios_adquiridos_descripcion_2"] = interp.apply(lambda x: x[1] if isinstance(x, tuple) else "")

    return df


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
        cols_base = [col for col, _ in _COLUMNAS_CONSOLIDADAS] + ["txt_tipo", "txt_archivo_origen"]
        cols_leyenda = [
            "tipo_comprobante_pago_documento_descripcion",
            "clasificacion_bienes_servicios_adquiridos_descripcion_1",
            "clasificacion_bienes_servicios_adquiridos_descripcion_2",
        ]
        return pd.DataFrame(columns=cols_base + cols_leyenda)

    df_final = pd.concat(filas, ignore_index=True)
    return _agregar_leyendas(df_final)


def exportar_consolidado_txt_excel(carpeta_txt: str, ruta_salida: str) -> pd.DataFrame:
    df = consolidar_txts(carpeta_txt)
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="consolidado_txt", index=False)
    return df
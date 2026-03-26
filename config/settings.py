# TXT parsing formats
# Type 801: TABERNERO PLE - no header row - RUC in column 12
# Type 804: CONSORCIO SAN JOSE SIRE - with header row - RUC in column 13
TXT_FILE_FORMATS = {
    "801": {"ruc_column": 12, "has_header": False, "txt_delimiter": "|"},
    "804": {"ruc_column": 13, "has_header": True, "txt_delimiter": "|"},
    "ruc_maestro": {"ruc_column": 1, "has_header": False, "txt_delimiter": "\t"},
}


# SUNAT RUC lookup - REQUEST
SUNAT_RUC_LOOKUP_URL = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias" # Request and Scraping

SUNAT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://e-consultaruc.sunat.gob.pe/"
}

# SUNAT RUC lookup - SCRAPING
SUNAT_FIELD_MAPPING = {
    "Número de RUC": "ruc_sunat",
    "Tipo Contribuyente": "tipo_contribuyente",
    "Nombre Comercial": "nombre_comercial",
    "Fecha de Inscripción": "fecha_inscripcion",
    "Fecha de Inicio de Actividades": "fecha_inicio_actividades",
    "Estado del Contribuyente": "estado_contribuyente",
    "Condición del Contribuyente": "condicion_contribuyente",
    "Domicilio Fiscal":"domicilio_fiscal",
    "Sistema Emisión de Comprobante":"sistema_emision_comprobante",
    "Actividad Comercio Exterior":"actividad_comercio_exterior",
    "Sistema Contabilidad":"sistema_contabilidad",
    "Actividad(es) Económica(s)":"actividades_economicas",
    "Comprobantes de Pago c/aut. de impresión (F. 806 u 816)":"comprobantes_pago",
    "Sistema de Emisión Electrónica":"sistema_emision_electronica",
    "Emisor electrónico desde":"emisor_electronico_desde",
    "Comprobantes Electrónicos":"comprobantes_electronicos",
    "Afiliado al PLE desde":"afiliado_ple_desde",
    "Padrones":"padrones",
    "Fecha consulta":"fecha_consulta_sunat",
}

# SUNAT list of entities without operational capacity (SSCO)
SUNAT_SSCO_URL = "https://www.sunat.gob.pe/padronesnotificaciones/sujeSinCapacidadOperativa.html"

# Lectura de TXTs
# Tipo 801: TABERNERO PLE - Sin cabeceras - RUC en columna 12
# Tipo 804: CONSORCIO SAN JOSE SIRE - Con cabeceras - RUC en columna 13
TXT_FORMATS = {
    "801": {"ruc_column": 12, "has_header": False, "txt_delimiter": "|"},
    "804": {"ruc_column": 13, "has_header": True, "txt_delimiter": "|"},
    "ruc_maestro": {"ruc_column": 1, "has_header": False, "txt_delimiter": "\t"},
}


# Consulta RUC SUNAT - REQUEST
SUNAT_URL_CONSULTA = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias" # Request and Scraping

SUNAT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://e-consultaruc.sunat.gob.pe/"
}

# Consulta RUC SUNAT - SCRAPING
SUNAT_FIELD_MAPEO = {
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

# Consulta Sujetos Sin Capacidad Operativa
SUNAT_CAPACIDAD_OPERATIVA = "https://www.sunat.gob.pe/padronesnotificaciones/sujeSinCapacidadOperativa.html"

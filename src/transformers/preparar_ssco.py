import re
from typing import List, Dict, Any


_SOLO_DIGITOS = re.compile(r"\D+")


def preparar_ssco_tablas(tablas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrega una columna limpia basada en 'RUC o documento de identidad del representante legal (1)'.
    """
    if not tablas:
        return tablas

    # Nombre exacto de la columna según el padrón SUNAT
    origen_col = "RUC o documento de identidad del representante legal (1)"
    destino_col = f"{origen_col}_limpia"

    nuevas_tablas: List[Dict[str, Any]] = []

    for fila in tablas:
        fila_nueva = dict[str, Any](fila)

        valor = fila_nueva.get(origen_col, "")
        if isinstance(valor, str):
            texto = valor.strip()
        else:
            texto = str(valor).strip() if valor is not None else ""

        # Reemplazar todo lo que no sea dígito por nada
        limpio = _SOLO_DIGITOS.sub("", texto)

        fila_nueva[destino_col] = limpio
        nuevas_tablas.append(fila_nueva)

    return nuevas_tablas


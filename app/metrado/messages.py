UNITS = (
    ("m", "metro lineal"),
    ("m2", "metro cuadrado"),
    ("m3", "metro cúbico"),
    ("und", "unidad"),
)

FIELDS = {
    "m": ("longitud",),
    "m2": ("largo", "ancho"),
    "m3": ("largo", "ancho", "alto"),
    "und": ("veces",),
}

ERROR_TEXT = {
    "empty_name": "La partida necesita un nombre.",
    "empty_dimension_name": "La medida necesita un nombre.",
    "non_positive": "La medida debe ser un número mayor que cero.",
    "duplicate_dimension": "Hay una medida repetida.",
    "missing_dimension": "Falta una medida de esta unidad.",
    "unexpected_dimension": "Esta unidad no usa esa medida.",
    "unknown_unit": "La unidad no es válida.",
    "blank_measure": "Falta una medida.",
    "not_a_number": "La medida debe ser un número mayor que cero.",
}

UNAVAILABLE = "No se puede calcular. El cálculo no está disponible."

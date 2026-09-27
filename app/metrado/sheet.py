"""Sheet data and validation. All quantity formulas live in Rust."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from metrado.hierarchy import Outline

UNITS = ("m", "m2", "m3", "kg", "und", "mes", "vje", "glb")
RESULT_COLUMN = {"m": 8, "m2": 9, "m3": 10, "kg": 12,
                 "und": 12, "mes": 12, "vje": 12, "glb": 12}
DIMENSIONS = {"m": ((4, "longitud"),),
              "m2": ((4, "largo"), (5, "ancho")),
              "m3": ((4, "largo"), (5, "ancho"), (6, "alto")),
              "kg": ((4, "largo"), (5, "gancho"), (6, "empalme"), (7, "diametro"), (10, "barras"))}


def new_row(kind, code="", description="", unit="m", level=None):
    cells = [""] * 14
    cells[0:3] = [code, description, unit if kind != "chapter" else ""]
    if kind == "detail":
        cells[3] = "1"
        cells[7 if unit != "kg" else 9] = "1"
    row = {"kind": kind, "cells": cells, "direct": ""}
    if level is not None:
        row['level'] = level
    return row


def example_rows():
    rows = [new_row("chapter", "00.01", "OBRAS PROVISIONALES"),
            new_row("item", "00.01.09", "ENERGÍA ELÉCTRICA PARA LA OBRA", "mes"),
            new_row("detail", description="ENERGÍA ELÉCTRICA PARA LA OBRA", unit="mes"),
            new_row("item", "00.01.10", "CERCO PROVISIONAL DE MALLA CON ARPILLERA H=2.40M"),
            new_row("detail", description="CERCO PROVISIONAL DE MALLA CON ARPILLERA H=2.40M"),
            new_row("chapter", "00.02", "TRABAJOS PRELIMINARES"),
            new_row("item", "00.02.01", "LIMPIEZA DE TERRENO", "m2"),
            new_row("item", "00.02.02", "TRAZO, NIVELES Y REPLANTEO PRELIMINAR", "m2"),
            new_row("item", "00.02.03", "TRAZO Y REPLANTEO DURANTE EL PROCESO DE EJECUCIÓN", "mes"),
            new_row("item", "00.02.04", "MOVILIZACIÓN Y DESMOVILIZACIÓN MAQUINARIA Y/O EQUIPO", "vje"),
            new_row("item", "00.02.05", "DEMOLICIÓN DE ESTRUCTURAS DE CONCRETO ARMADO", "m3"),
            new_row("item", "00.02.06", "DEMOLICIÓN DE PAVIMENTO ASFÁLTICO Y CONCRETO C/EQUIPO PESADO", "m2"),
            new_row("detail", description="PAVIMENTO ASFALTO", unit="m2"),
            new_row("chapter", "01.02", "CONCRETO ARMADO"),
            new_row("item", "01.02.02.03", "ESTRIBOS, ACERO Fy=42000 kg/cm2", "kg")]
    rows[2]["cells"][7] = "6"
    rows[4]["cells"][4] = "80.00"
    rows[12]["direct"] = "837.13"
    rows.extend(_steel_example_details())
    return rows


def steel_detail(description, similar, largo, gancho, empalme, diameter, bars):
    row = new_row("detail", description=description, unit="kg")
    row["cells"][3] = str(similar)
    row["cells"][4:8] = [str(largo), str(gancho), str(empalme), diameter]
    row["cells"][9] = "1"
    row["cells"][10] = str(bars)
    return row


def _steel_example_details():
    return [
        steel_detail("VERTICAL INTERIOR CONTINUO 53 Ø1\"", 2, 10.85, 0.61, 1.15, "1\"", 53),
        steel_detail("VERTICAL INTERIOR CORTADO 53 Ø1\"", 2, 5.35, 0.31, 0, "1\"", 53),
        steel_detail("VERTICAL EXTERIOR 66 Ø1\"", 2, 10.85, 0.61, 1.15, "1\"", 66),
        steel_detail("TRANSVERSAL INTERIOR 44 Ø3/4\"", 2, 13.15, 0.46, 0.85, "3/4\"", 44),
        steel_detail("TRANSVERSAL EXTERIOR 44 Ø3/4\"", 2, 13.15, 0.46, 1.15, "3/4\"", 44),
        steel_detail("TEMPERATURA CARA SUPERIOR 8 Ø1\"", 2, 13.15, 0.61, 1.15, "1\"", 8),
        steel_detail("VERTICAL INTERIOR CAJUELA PRINCIPAL 6 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 6),
        steel_detail("VERTICAL EXTERIOR CAJUELA PRINCIPAL 6 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 6),
        steel_detail("HORIZONTAL INTERIOR CAJUELA PRINCIPAL 5 Ø5/8\"", 2, 13.15, 0.38, 0.73, "5/8\"", 5),
        steel_detail("HORIZONTAL EXTERIOR CAJUELA PRINCIPAL 5 Ø5/8\"", 2, 13.15, 0.38, 0.73, "5/8\"", 5),
        steel_detail("VERTICAL INTERIOR CAJUELA LATERAL IZQ 7 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 7),
        steel_detail("VERTICAL EXTERIOR CAJUELA LATERAL IZQ 7 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 7),
        steel_detail("HORIZONTAL INTERIOR CAJUELA LATERAL IZQ 5 Ø5/8\"", 2, 1.30, 0.38, 0, "5/8\"", 5),
        steel_detail("HORIZONTAL EXTERIOR CAJUELA LATERAL IZQ 5 Ø5/8\"", 2, 1.30, 0.38, 0, "5/8\"", 5),
        steel_detail("VERTICAL INTERIOR CAJUELA LATERAL DER 7 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 7),
        steel_detail("VERTICAL EXTERIOR CAJUELA LATERAL DER 7 Ø3/4\"", 2, 2.15, 0.46, 0, "3/4\"", 7),
        steel_detail("HORIZONTAL INTERIOR CAJUELA LATERAL DER 5 Ø5/8\"", 2, 1.30, 0.38, 0, "5/8\"", 5),
        steel_detail("HORIZONTAL EXTERIOR CAJUELA LATERAL DER 5 Ø5/8\"", 2, 1.30, 0.38, 0, "5/8\"", 5),
    ]


def parent_item(rows, index):
    for i in range(index, -1, -1):
        if rows[i]["kind"] == "chapter":
            return None
        if rows[i]["kind"] == "item":
            return i
    return None


def subtree_end(rows, index):
    return Outline(rows).ends[index]


def calculate(rows, engine):
    """Return values and errors; never store calculated cells in the document."""
    values, errors = {}, {}
    current, quantities, invalid = None, [], False

    def finish():
        if current is not None:
            if invalid:
                errors[current] = "Hay detalles pendientes o inválidos en esta partida."
            else:
                try:
                    values[(current, 13)] = engine.ask_sheet_total(quantities)
                except ValueError:
                    errors[current] = "El total está fuera del rango permitido."

    for index, row in enumerate(rows):
        if row['kind'] == 'detail_group':
            if current is None:
                errors[index] = 'El título de detalle necesita una partida.'
            continue
        if row["kind"] != "detail":
            finish()
            current = index if row["kind"] == "item" else None
            quantities, invalid = [], False
            continue
        if current is None:
            errors[index] = "El detalle necesita una partida."
            continue
        unit = rows[current]["cells"][2]
        cells = row["cells"]
        try:
            number = lambda text: float(text.strip().replace(",", "."))
            if row["direct"].strip():
                if unit == "kg":
                    values[(index, 7)] = number(cells[9])
                quantity = engine.ask_sheet_quantity(
                    unit, [], number(cells[3]),
                    number(cells[9]) if unit == "kg" else number(cells[7]),
                    number(row["direct"]))
            elif unit == "kg":
                times = engine.ask_sheet_quantity(
                    "und", [], number(cells[10]),
                    number(cells[9]) if cells[9].strip() else 1.0, None)
                values[(index, 7)] = times
                if not cells[7].strip():
                    raise ValueError("diameter")
                length, kg_m, quantity = engine.ask_sheet_steel(
                    number(cells[4]),
                    number(cells[5]) if cells[5].strip() else 0.0,
                    number(cells[6]) if cells[6].strip() else 0.0,
                    cells[7].strip(),
                    number(cells[10]),
                    number(cells[3]),
                    number(cells[9]) if cells[9].strip() else 1.0,
                )
                values[(index, 8)] = engine.ask_sheet_quantity(
                    "m", [("longitud", length)], number(cells[3]), times, None)
                values[(index, 11)] = kg_m
            else:
                dimensions = [
                    (name, number(cells[column])) for column, name in DIMENSIONS.get(unit, ())]
                quantity = engine.ask_sheet_quantity(
                    unit, dimensions, number(cells[3]), number(cells[7]), None)
            values[(index, RESULT_COLUMN[unit])] = quantity
            quantities.append(quantity)
        except (ValueError, KeyError, OverflowError):
            errors[index] = "Completa las medidas y factores con números positivos y finitos."
            invalid = True
    finish()
    return values, errors


def read_project(path):
    if Path(path).stat().st_size > 10_000_000:
        raise ValueError("El archivo supera el límite de 10 MB.")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_project(data)


def validate_project(data):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data.get("version") not in (1, 2, 3):
        raise ValueError("Formato de planilla no reconocido.")
    if not isinstance(data.get("title"), str) or not isinstance(data.get("rows"), list):
        raise ValueError("La planilla no contiene un título y filas válidos.")
    if len(data["rows"]) > 10000:
        raise ValueError("La planilla supera el límite de 10 000 filas.")
    current = None
    for row in data["rows"]:
        kinds = ('chapter', 'item', 'detail', 'detail_group') if data['version'] == 3 else ('chapter', 'item', 'detail')
        if not isinstance(row, dict) or row.get("kind") not in kinds:
            raise ValueError("La planilla contiene un tipo de fila inválido.")
        cells = row.get("cells")
        if not isinstance(cells, list) or len(cells) != 14 or not all(isinstance(c, str) for c in cells):
            raise ValueError("Cada fila debe contener 14 columnas de texto.")
        if not isinstance(row.get("direct"), str):
            raise ValueError("Cantidad directa inválida.")
        if data['version'] >= 2 and 'level' not in row:
            raise ValueError('Falta el nivel de una fila.')
        if row["kind"] == "chapter":
            current = None
        elif row["kind"] == "item":
            if cells[2] not in UNITS:
                raise ValueError("Unidad de partida no reconocida.")
            current = cells[2]
        elif current is None:
            raise ValueError("Hay detalles sin una partida asociada.")
        else:
            if data['version'] >= 2 and cells[2] != current:
                raise ValueError('El detalle y su partida deben tener la misma unidad.')
            cells[2] = current
            if row['kind'] == 'detail_group' and (cells[0] or any(cells[3:]) or row['direct']):
                raise ValueError('Un título de detalle solo contiene descripción; no admite código ni cantidades.')
        clear_results(cells, current or cells[2])
    Outline(data['rows'], strict=True)
    return data["title"], data["rows"]


def clear_results(cells, unit=""):
    """Drop calculated cells; keep steel veces (9) and n° de barras (10)."""
    for column in range(8, 14):
        if unit == "kg" and column in (9, 10):
            continue
        cells[column] = ""


def write_project(path, title, rows):
    """Atomic replacement keeps an existing project intact if writing fails."""
    from metrado.hierarchy import materialize
    groups = any(row['kind'] == 'detail_group' for row in rows)
    hierarchical = groups or any('level' in row for row in rows)
    data = {"version": 3 if groups else 2 if hierarchical else 1, "title": title,
            "rows": materialize(rows) if hierarchical else deepcopy(rows)}
    validate_project(data)
    for row in data["rows"]:
        clear_results(row["cells"], row["cells"][2])
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".metrado-", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)

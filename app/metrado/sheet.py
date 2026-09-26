"""Sheet data and validation. All quantity formulas live in Rust."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

UNITS = ("m", "m2", "m3", "kg", "und", "mes", "vje", "glb")
RESULT_COLUMN = {"m": 8, "m2": 9, "m3": 10, "kg": 11,
                 "und": 12, "mes": 12, "vje": 12, "glb": 12}
DIMENSIONS = {"m": ((4, "longitud"),),
              "m2": ((4, "largo"), (5, "ancho")),
              "m3": ((4, "largo"), (5, "ancho"), (6, "alto"))}


def new_row(kind, code="", description="", unit="m"):
    cells = [""] * 14
    cells[0:3] = [code, description, unit if kind != "chapter" else ""]
    if kind == "detail":
        cells[3] = cells[7] = "1"
    return {"kind": kind, "cells": cells, "direct": ""}


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
            new_row("detail", description="PAVIMENTO ASFALTO", unit="m2")]
    rows[2]["cells"][7] = "6"
    rows[4]["cells"][4] = "80.00"
    rows[12]["direct"] = "837.13"
    return rows


def parent_item(rows, index):
    for i in range(index, -1, -1):
        if rows[i]["kind"] == "chapter":
            return None
        if rows[i]["kind"] == "item":
            return i
    return None


def subtree_end(rows, index):
    kind = rows[index]["kind"]
    end = index + 1
    while end < len(rows):
        next_kind = rows[end]["kind"]
        if kind == "detail" or next_kind == "chapter":
            break
        if kind == "item" and next_kind == "item":
            break
        end += 1
    return end


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
            direct = number(row["direct"]) if row["direct"].strip() else None
            dimensions = [] if direct is not None else [
                (name, number(cells[column])) for column, name in DIMENSIONS.get(unit, ())]
            quantity = engine.ask_sheet_quantity(
                unit, dimensions, number(cells[3]), number(cells[7]), direct)
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
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("Formato de planilla no reconocido.")
    if not isinstance(data.get("title"), str) or not isinstance(data.get("rows"), list):
        raise ValueError("La planilla no contiene un título y filas válidos.")
    if len(data["rows"]) > 10000:
        raise ValueError("La planilla supera el límite de 10 000 filas.")
    current = None
    for row in data["rows"]:
        if not isinstance(row, dict) or row.get("kind") not in ("chapter", "item", "detail"):
            raise ValueError("La planilla contiene un tipo de fila inválido.")
        cells = row.get("cells")
        if not isinstance(cells, list) or len(cells) != 14 or not all(isinstance(c, str) for c in cells):
            raise ValueError("Cada fila debe contener 14 columnas de texto.")
        if not isinstance(row.get("direct"), str):
            raise ValueError("Cantidad directa inválida.")
        if row["kind"] == "chapter":
            current = None
        elif row["kind"] == "item":
            if cells[2] not in UNITS:
                raise ValueError("Unidad de partida no reconocida.")
            current = cells[2]
        elif current is None:
            raise ValueError("Hay detalles sin una partida asociada.")
        else:
            cells[2] = current
        cells[8:14] = [""] * 6
    return data["title"], data["rows"]


def write_project(path, title, rows):
    """Atomic replacement keeps an existing project intact if writing fails."""
    data = {"version": 1, "title": title, "rows": deepcopy(rows)}
    for row in data["rows"]:
        row["cells"][8:14] = [""] * 6
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

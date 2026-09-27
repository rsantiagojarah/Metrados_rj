"""Clipboard interchange: lossless row blocks and spreadsheet-compatible TSV."""
from copy import deepcopy
import csv
import io
import json
from uuid import uuid4

from PySide6.QtCore import QMimeData, Qt

from metrado.hierarchy import MAX_ROWS, MEASUREMENT_KINDS, Outline, materialize, renumber
from metrado.sheet import new_row, validate_project

ROW_MIME = 'application/x-metrado-rows+json'
MAX_BYTES = 10_000_000


def selected_roots(rows, selected):
    outline = Outline(rows)
    roots, end = [], -1
    for index in sorted(set(selected)):
        if index >= end:
            roots.append(index)
            end = outline.ends[index]
    return roots


def encode_rows(model, selected):
    rows = materialize(model.rows)
    outline = Outline(rows)
    roots = selected_roots(rows, selected)
    if not roots:
        raise ValueError('Selecciona una fila para copiar.')
    kinds = {rows[i]['kind'] for i in roots}
    if kinds.intersection(MEASUREMENT_KINDS) and kinds.difference(MEASUREMENT_KINDS):
        raise ValueError('Copia el desagregado por separado de los capítulos y partidas.')
    block, text = [], []
    for index in roots:
        for i in range(index, outline.ends[index]):
            row = deepcopy(rows[i])
            row['level'] -= outline.levels[index]
            block.append(row)
            text.append([cell_text(model, i, c) for c in range(14)])
    mime = QMimeData()
    version = 2 if any(row['kind'] == 'detail_group' for row in block) else 1
    mime.setData(ROW_MIME, json.dumps({'version': version, 'rows': block}, ensure_ascii=False).encode('utf-8'))
    mime.setText(tsv(text))
    return mime


def cell_text(model, row, column):
    role = Qt.EditRole if model.editable(row, column) else Qt.DisplayRole
    return str(model.data(model.index(row, column), role) or '')


def tsv(matrix):
    stream = io.StringIO(newline='')
    csv.writer(stream, delimiter='\t', lineterminator='\r\n').writerows(matrix)
    return stream.getvalue()


def parse_tsv(text):
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise ValueError('El portapapeles supera el límite de 10 MB.')
    try:
        matrix = list(csv.reader(io.StringIO(text, newline=''), delimiter='\t', strict=True))
    except csv.Error as error:
        raise ValueError('El texto del portapapeles no es una tabla válida.') from error
    if not matrix:
        return []
    width = len(matrix[0])
    if len(matrix) > MAX_ROWS or width > 14 or not width or any(len(row) != width for row in matrix):
        raise ValueError('Selecciona un bloque rectangular de hasta 14 columnas y 10 000 filas.')
    return matrix


def decode_rows(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('El portapapeles supera el límite de 10 MB.')
    try:
        data = json.loads(bytes(raw).decode('utf-8'))
        if not isinstance(data, dict) or data.get('version') not in (1, 2) or not isinstance(data.get('rows'), list):
            raise ValueError('Formato de filas no reconocido.')
        rows = data['rows']
        if not rows or len(rows) > MAX_ROWS:
            raise ValueError('No hay filas válidas en el portapapeles.')
        if any(not isinstance(row, dict) or type(row.get('level')) is not int for row in rows):
            raise ValueError('Nivel de fila inválido en el portapapeles.')
        if rows[0]['level'] != 0:
            raise ValueError('El bloque copiado debe empezar en el nivel principal.')
        version = 3 if any(row['kind'] == 'detail_group' for row in rows) else 2
        if rows[0]['kind'] in MEASUREMENT_KINDS:
            if any(row['kind'] not in MEASUREMENT_KINDS or
                   row['cells'][2] != rows[0]['cells'][2] for row in rows):
                raise ValueError('Los detalles copiados deben tener la misma unidad.')
            for row in rows:
                row['level'] += 1
            wrapper = [new_row('item', unit=rows[0]['cells'][2], level=0)] + rows
            validate_project({'version': version, 'title': '', 'rows': wrapper})
            for row in rows:
                row['level'] -= 1
        else:
            validate_project({'version': version, 'title': '', 'rows': rows})
        return rows
    except (KeyError, TypeError, IndexError, UnicodeError, RecursionError) as error:
        raise ValueError('El bloque del portapapeles está dañado.') from error


def insert_rows(rows, selected, block):
    if len(rows) + len(block) > MAX_ROWS:
        raise ValueError('La planilla supera el límite de 10 000 filas.')
    result = materialize(rows)
    block = deepcopy(block)
    outline = Outline(result)
    valid = 0 <= selected < len(result)
    if block[0]['kind'] in MEASUREMENT_KINDS:
        parent = selected if valid and result[selected]['kind'] in ('item', 'detail_group') else (
            outline.parents[selected] if valid and result[selected]['kind'] == 'detail' else None)
        if parent is None or result[parent]['cells'][2] != block[0]['cells'][2]:
            raise ValueError('Selecciona una partida de la misma unidad que los detalles copiados.')
        position = outline.ends[selected] if result[selected]['kind'] == 'detail_group' else selected + 1
        level = outline.levels[parent] + 1
    elif valid:
        if result[selected]['kind'] == 'chapter':
            parent = selected
            position = outline.ends[selected]
        else:
            owner = outline.owners[selected]
            parent = outline.parents[owner]
            position = outline.ends[owner]
        level = 0 if parent is None else outline.levels[parent] + 1
    else:
        parent, position, level = None, len(result), 0
    for row in block:
        row['level'] += level
        if 'id' in row:
            row['id'] = uuid4().hex
    result[position:position] = block
    return renumber(result), position

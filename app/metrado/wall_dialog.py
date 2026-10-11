"""Wall forms with labeled fields and selectors."""
from copy import deepcopy
from dataclasses import asdict
import sqlite3
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget, QSizePolicy,
)
from metrado.arithmetic import numeric_text
from metrado.numeric_edit import NumericEdit
from metrado.wall_steel_form import DistributionTable
from metrado.wall_preview import WallPreview
from metrado.wall_rebar import hook_lengths, position_key
from metrado.wall_types import WallType, default_wall_type, generate_wall_rows, nonnegative, positive
from metrado.reference_dialog import ReferencePicker


def _number(text, label, *, zero=False):
    try:
        value = numeric_text(text, nonnegative=zero, positive=not zero)
        return nonnegative(value, label) if zero else positive(value, label)
    except ValueError as error:
        raise ValueError(f'{label}: {error}') from error


class WallTypeDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self._loaded = None
        self._previous_name = None
        self.setWindowTitle('Tipos de muro')
        self.resize(1160, 700)
        self._updating = False
        self._baseline = default_wall_type()
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel('Tipos guardados'))
        self.list = QListWidget()
        self.list.setFixedWidth(150)
        left.addWidget(self.list)
        for text, callback in [('Nuevo', self.new_type), ('Duplicar tipo', self.duplicate_type),
                               ('Eliminar tipo', self.delete_type), ('Exportar…', self.export_type),
                               ('Importar…', self.import_type)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            left.addWidget(button)
        root.addLayout(left)
        panel = QVBoxLayout()
        root.addLayout(panel, 1)
        self.name, self.description = QLineEdit(), QLineEdit()
        self.name.setMaxLength(160)
        form = QFormLayout()
        form.addRow('Nombre del tipo', self.name)
        form.addRow('Descripción', self.description)
        panel.addLayout(form)
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        body = QHBoxLayout()
        self.body = body
        body.addWidget(self.tabs, 3)
        self.section = WallPreview()
        body.addWidget(self.section, 2)
        panel.addLayout(body, 1)
        self.fields, self.labels = {}, {}
        geometry = QWidget()
        geometry_layout = QVBoxLayout(geometry)
        for title, entries in [
            ('Pantalla', [('screen_height', 'Altura de pantalla'), ('top_thickness', 'Espesor superior'),
                          ('bottom_thickness', 'Espesor inferior')]),
            ('Zapata', [('footing_left', 'Vuelo izquierdo (relleno)'), ('footing_right', 'Vuelo derecho'),
                        ('footing_thickness', 'Espesor de zapata')]),
            ('Dentellón', [('dentellon_width', 'Ancho'), ('dentellon_depth', 'Profundidad'), ('dentellon_slope', 'Vuelo inclinado izquierdo')])]:
            group = QGroupBox(title)
            fields = QFormLayout(group)
            fields.setSpacing(6)
            if title == 'Dentellón':
                self.dentellon = QCheckBox('Incluir dentellón')
                fields.addRow(self.dentellon)
            for key, label in entries:
                zero_allowed = key in ('footing_left', 'footing_right', 'dentellon_slope')
                self.fields[key] = NumericEdit(positive=not zero_allowed, nonnegative=zero_allowed)
                self.fields[key].setFixedWidth(100)
                self.fields[key].setFixedHeight(26)
                self.labels[key] = label
                fields.addRow(label + ' (m)', self.fields[key])
            group.setMaximumWidth(390)
            geometry_layout.addWidget(group)
        note = QLabel('Izquierda: lado del relleno.\nTodos los valores se expresan en metros.')
        note.setWordWrap(True)
        geometry_layout.addWidget(note)
        geometry_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(geometry)
        self.tabs.addTab(scroll, 'Geometría')
        steel = QWidget()
        steel_layout = QVBoxLayout(steel)
        hint = QLabel('Completa solo el acero que lleva el muro. Sin diámetro o separación, esa posición no se metra. El cortado requiere también su longitud.')
        hint.setWordWrap(True)
        steel_layout.addWidget(hint)
        self.horizontal_in_footing = QCheckBox('Incluir altura de zapata en el acero horizontal de pantalla')
        self.horizontal_in_footing.setToolTip('Desmarcado: solo altura de pantalla. Marcado: pantalla más zapata, en ambas caras.')
        steel_layout.addWidget(self.horizontal_in_footing)
        self.distributions = DistributionTable()
        steel_layout.addWidget(self.distributions, 1)
        note = QLabel('Sin recubrimientos. Selecciona una fila o barra para editar sus ganchos en el esquema.\n'
                      'Corte: altura sobre zapata en el tipo; su desarrollo se conserva al variar el tramo.')
        note.setWordWrap(True)
        steel_layout.addWidget(note)
        self.tabs.addTab(steel, 'Acero')
        self.error = QLabel()
        self.error.setWordWrap(True)
        panel.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = self.buttons.button(QDialogButtonBox.Save)
        self.save_button.setText('Guardar tipo')
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cancelar')
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        panel.addWidget(self.buttons)
        self.dentellon.toggled.connect(self._toggle_optional)
        self.horizontal_in_footing.toggled.connect(self._update_section)
        self.distributions.changed.connect(self._update_section)
        self.distributions.inputError.connect(self.error.setText)
        self.distributions.positionSelected.connect(self.section.select_position)
        self.section.positionSelected.connect(self.distributions.select_position)
        self.section.hooksChanged.connect(self._change_hooks)
        self.section.inputError.connect(self.error.setText)
        self.tabs.currentChanged.connect(self._update_section)
        for widget in self.fields.values():
            if isinstance(widget, NumericEdit):
                widget.inputError.connect(self.error.setText)
                widget.textChanged.connect(self._update_section)
        self.list.currentRowChanged.connect(self.load_row)
        self.refresh()

    def _toggle_optional(self):
        for key in ('dentellon_width', 'dentellon_depth', 'dentellon_slope'):
            self.fields[key].setEnabled(self.dentellon.isChecked())
        self.distributions.set_dentellon(self.dentellon.isChecked())
        self._update_section()

    def _change_hooks(self, key, start, end):
        self._baseline.hooks[key] = dict(start=start,end=end)
        self.error.clear()
        self._update_section()

    def _update_section(self, *args):
        if self._updating:
            return
        steel = self.tabs.currentIndex() == 1
        self.tabs.setMinimumWidth(540 if steel else 400)
        self.body.setStretch(0, 3 if steel else 2)
        self.body.setStretch(1, 2 if steel else 3)
        try:
            wall = self._geometry()
        except ValueError:
            if self.section.wall:
                self.section.set_wall(self.section.wall, self.tabs.currentIndex() == 1, pending=True)
            return
        wall.distributions = self.distributions.configuration(preview=True)
        wall.cut_left = any(d['component'] == 'refuerzo_cortado' for d in wall.distributions)
        self.section.set_wall(wall, self.tabs.currentIndex() == 1)

    def _geometry(self):
        wall = deepcopy(self._baseline)
        wall.name = self.name.text().strip()
        wall.description = self.description.text().strip()
        wall.dentellon = self.dentellon.isChecked()
        wall.horizontal_in_footing = self.horizontal_in_footing.isChecked()
        for key, edit in self.fields.items():
            if key.startswith('dentellon_') and not wall.dentellon:
                continue
            if key in ('footing_left', 'footing_right', 'dentellon_slope'):
                value = _number(edit.text(), self.labels[key], zero=True)
            else:
                value = _number(edit.text(), self.labels[key])
            setattr(wall, key, value)
        return wall

    def refresh(self, name=None):
        self.values = self.store.read()
        self.list.blockSignals(True)
        self.list.clear()
        self.list.addItems([w.name for w in self.values])
        index = next((i for i, wall in enumerate(self.values) if wall.name == name), 0)
        self.list.setCurrentRow(index)
        self.list.blockSignals(False)
        self._load(self.values[index])

    def _load(self, wall, new=False):
        self._updating = True
        self._baseline = deepcopy(wall)
        self._previous_name = None if new else wall.name
        self.name.setText(wall.name)
        self.description.setText(wall.description)
        for key, edit in self.fields.items():
            edit.setText(format(getattr(wall, key), '.12g'))
            edit._previous = edit.text()
        self.dentellon.setChecked(wall.dentellon)
        self.horizontal_in_footing.setChecked(wall.horizontal_in_footing)
        self.distributions.load(wall)
        self._toggle_optional()
        self.error.clear()
        if self.distributions._extra:
            self.error.setText('El formato anterior contiene posiciones repetidas o ajenas al modelo. '
                               'Se muestra la primera de cada posición; revisa los valores antes de guardar.')
        self._loaded = asdict(self.read_form())
        self._updating = False
        self._update_section()

    def _can_discard(self):
        if self._loaded is None:
            return True
        try:
            if asdict(self.read_form()) == self._loaded:
                return True
        except ValueError:
            pass
        return QMessageBox.question(self, 'Cambios sin guardar',
            'Hay cambios en este tipo. ¿Descartarlos?', QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No) == QMessageBox.Yes

    def load_row(self, index):
        if not 0 <= index < len(self.values):
            return
        if not self._can_discard():
            self.list.blockSignals(True)
            self.list.setCurrentRow(next((i for i, w in enumerate(self.values) if w.name == self._previous_name), -1))
            self.list.blockSignals(False)
            return
        self._load(self.values[index])

    def read_form(self):
        wall = self._geometry()
        wall.distributions = self.distributions.configuration()
        for item in wall.distributions:
            start,end = hook_lengths(wall,item)
            wall.hooks[position_key(item)] = dict(start=start,end=end)
        cut = next((item for item in wall.distributions if item['component'] == 'refuerzo_cortado'), None)
        wall.cut_left = cut is not None
        if cut:
            wall.cut_length, wall.cut_diameter, wall.cut_spacing = cut['fixed_length'], cut['diameter'], cut['spacing']
        wall.validate()
        return wall

    def accept(self):
        try:
            wall = self.read_form()
            if wall.name != self._previous_name and wall.name in {w.name for w in self.store.read()}:
                raise ValueError('Ya existe otro tipo con ese nombre. Elige un nombre diferente.')
            self.store.save(wall, self._previous_name)
        except (OSError, ValueError, sqlite3.Error) as error:
            self.error.setText(str(error))
            return
        super().accept()

    def _unique_name(self, base):
        existing, name, suffix = {w.name for w in self.values}, base, 2
        while name in existing:
            name = f'{base} {suffix}'
            suffix += 1
        return name

    def new_type(self):
        if self._can_discard():
            wall = default_wall_type()
            wall.name = self._unique_name('Nuevo muro')
            self._load(wall, new=True)
            self.name.setFocus()
            self.name.selectAll()

    def duplicate_type(self):
        try:
            wall = self.read_form()
            wall.name = self._unique_name(wall.name + ' (copia)')
            self._load(wall, new=True)
            self.name.setFocus()
            self.name.selectAll()
        except ValueError as error:
            self.error.setText(str(error))

    def delete_type(self):
        if not self._previous_name or len(self.values) <= 1:
            self.error.setText('Conserva al menos un tipo guardado.')
            return
        if QMessageBox.question(self, 'Eliminar tipo', f'¿Eliminar «{self._previous_name}» del catálogo?',
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            self.store.delete(self._previous_name)
            self.refresh()
        except (OSError, ValueError, sqlite3.Error) as error:
            self.error.setText(str(error))

    def export_type(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Exportar catálogo guardado', '', 'Tipos de muro (*.json)')
        if path:
            try:
                self.store.export_json(path)
            except (OSError, ValueError, sqlite3.Error) as error:
                self.error.setText(str(error))

    def import_type(self):
        if not self._can_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Importar tipos de muro', '', 'Tipos de muro (*.json)')
        if path:
            try:
                self.store.import_json(path)
                self.refresh()
            except (OSError, ValueError, sqlite3.Error) as error:
                self.error.setText(str(error))


class WallGeneratorDialog(QDialog):
    DESTINATIONS = (
        ('pantalla:m3', 'Pantalla · concreto', 'm3'), ('zapata:m3', 'Zapata · concreto', 'm3'),
        ('pantalla:m2', 'Pantalla · encofrado', 'm2'), ('zapata:m2', 'Zapata · encofrado', 'm2'),
        ('pantalla:kg', 'Pantalla · acero', 'kg'), ('zapata:kg', 'Zapata · acero', 'kg'),
    )

    def __init__(self, store, rows, parent=None, instance=None, destination=None, item_entries=None):
        super().__init__(parent)
        self.instance = deepcopy(instance)
        self.on_generate = None
        self.setWindowTitle('Editar muro generado' if instance else 'Generar muro tipo')
        self.resize(720, 520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.wall = QComboBox()
        self.values = [WallType.from_dict(deepcopy(instance['wall']))] if instance else store.read()
        self.wall.addItems([wall.name for wall in self.values])
        self.wall.setEnabled(not bool(instance))
        self.wall_picker = QPushButton()
        self.wall_picker.clicked.connect(self.pick_wall)
        self.tramo_name = QLineEdit(instance.get('description', '') if instance else '')
        self.tramo_name.setMaxLength(160)
        self.tramo_name.setPlaceholderText('Ejemplo: lateral eje B')
        self.length = NumericEdit(str(instance['length']) if instance else '1', positive=True)
        self.height = NumericEdit(str(instance['height']) if instance and instance['height'] is not None else '',
                                  positive=True, allow_blank=True)
        self.height.setPlaceholderText('Usar altura del tipo')
        self.length.setToolTip('Haz clic aquí y usa MTRLONGITUD en AutoCAD para traer la longitud seleccionada.')
        self.length.installEventFilter(self)
        form.addRow('Tipo de muro', self.wall_picker)
        form.addRow('Descripción del tramo', self.tramo_name)
        form.addRow('Longitud del tramo (m)', self.length)
        form.addRow('Altura de pantalla (m)', self.height)
        layout.addLayout(form)
        if instance:
            note = QLabel('Se usa la configuración guardada con este tramo. Al actualizar se reemplazan '
                          'sus detalles asociados, incluidos los editados a mano. Puedes deshacer el cambio.')
            note.setWordWrap(True)
            layout.addWidget(note)
        self.item_entries = item_entries or [
            dict(id=row['id'], unit=row['cells'][2], label=f"{row['cells'][0]} · {row['cells'][1]}")
            for row in rows if row['kind'] == 'item']
        self.destination_values, self.destinations = {}, {}
        for key, label, unit in self.DESTINATIONS:
            button = QPushButton('Buscar partida…')
            button.clicked.connect(lambda checked=False, k=key: self.pick_destination(k))
            self.destinations[key] = button
            selected = instance['destinations'].get(key) if instance else None
            if selected is None and instance:
                selected = instance['destinations'].get(unit)
            if selected:
                self.destination_values[key] = selected
                selected_label = next((entry['label'] for entry in self.item_entries if entry['id'] == selected),
                                      'Partida anterior no disponible')
                button.setText(selected_label)
            form.addRow(label, button)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        layout.addWidget(self.preview)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.generate_button = self.buttons.addButton('Actualizar tramo' if instance else 'Generar', QDialogButtonBox.ActionRole)
        self.buttons.button(QDialogButtonBox.Cancel).setText('Cerrar')
        self.generate_button.clicked.connect(self.generate)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.length.textChanged.connect(self.update_preview)
        self.height.textChanged.connect(self.update_preview)
        self.wall.currentIndexChanged.connect(self.update_preview)
        self.length.inputError.connect(self.preview.setText)
        self.height.inputError.connect(self.preview.setText)
        self.tramo_name.textChanged.connect(self.update_preview)
        self.wall.currentIndexChanged.connect(self._update_wall_label)
        self._update_wall_label()
        self.update_preview()

    def eventFilter(self, watched, event):
        if watched is self.length and event.type() == QEvent.FocusIn:
            window = self.parent()
            if hasattr(window, 'set_autocad_length_target'):
                window.set_autocad_length_target(self.length)
        return super().eventFilter(watched, event)

    def done(self, result):
        window = self.parent()
        if hasattr(window, 'clear_autocad_length_target'):
            window.clear_autocad_length_target(self.length)
        super().done(result)

    def configuration(self):
        wall = self.values[self.wall.currentIndex()]
        length = _number(self.length.text(), 'Longitud')
        height = _number(self.height.text(), 'Altura') if self.height.text().strip() else None
        return wall, length, height

    def selected_destinations(self):
        return dict(self.destination_values)

    def tramo_label(self):
        suffix = self.tramo_name.text().strip()
        return self.wall.currentText() + (' · ' + suffix if suffix else '')

    def _update_wall_label(self):
        self.wall_picker.setText(self.wall.currentText() + '  ▾')

    def pick_wall(self):
        entries = [(f'{wall.name} · {wall.description}', '', index, True)
                   for index, wall in enumerate(self.values)]
        picker = ReferencePicker(entries, self)
        picker.setWindowTitle('Elegir tipo de muro — escribe para buscar')
        if picker.exec() == QDialog.Accepted and picker.chosen is not None:
            self.wall.setCurrentIndex(picker.chosen)
        picker.deleteLater()

    def pick_destination(self, key):
        unit = next(unit for code, _, unit in self.DESTINATIONS if code == key)
        entries = [(entry['label'], unit, entry['id'], True) for entry in self.item_entries if entry['unit'] == unit]
        picker = ReferencePicker(entries, self)
        picker.setWindowTitle('Elegir partida — escribe para buscar')
        if picker.exec() == QDialog.Accepted and picker.chosen is not None:
            self.destination_values[key] = picker.chosen
            self.destinations[key].setText(next(entry['label'] for entry in self.item_entries if entry['id'] == picker.chosen))
            self.update_preview()
        picker.deleteLater()

    def update_preview(self):
        try:
            wall, length, height = self.configuration()
            entries = generate_wall_rows(wall, length, height)
            selected = self.selected_destinations()
            count = sum(f'{rest[-1]}:{unit}' in selected for unit, _, *rest in entries)
            self.preview.setText(f'{count} detalles · Pantalla {height or wall.screen_height:g} m · '
                                 f'Tramo {length:g} m. Solo se utilizan las partidas seleccionadas.')
            self.generate_button.setEnabled(count > 0)
        except ValueError as error:
            self.preview.setText(str(error))
            self.generate_button.setEnabled(False)

    def generate(self):
        try:
            self.configuration()
            if not self.tramo_name.text().strip():
                raise ValueError('Escribe la descripción del tramo.')
            if not self.selected_destinations():
                raise ValueError('Selecciona al menos una partida de destino.')
        except ValueError as error:
            self.preview.setText(str(error))
            return
        if self.on_generate:
            self.on_generate()

"""Distributed steel capture from AutoCAD into managed kg details."""
from decimal import Decimal
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication, QDialogButtonBox

import metrado._enlace as engine
from metrado import steel_config as sc
from metrado.autocad_bridge import BridgeProtocol, PROTOCOL_VERSION
from metrado.autocad_integration import (
    AutoCadRequestDispatcher, validate_steel_distribution_request,
)
from metrado.hierarchy import materialize, renumber
from metrado.sheet import new_row
from metrado.steel_dialog import DistributionFormatDialog
from metrado.steel_distribution import (
    DEFAULT_TEMPLATE, distributed_bar_count, parse_distribution, validate_template,
)
from metrado.steel_store import CatalogStore
from metrado.window import PlantillaWindow


APP = QApplication.instance() or QApplication([])


def message(payload):
    return {
        'protocol': PROTOCOL_VERSION,
        'type': 'steel_distribution',
        'request_id': str(uuid.uuid4()),
        'payload': payload,
    }


def rows():
    catalog = sc.initial_catalog()
    item = new_row('item', description='ACERO', unit='kg', level=1)
    sc.adopt(item, catalog)
    return renumber([
        new_row('chapter', description='ESTRUCTURAS', level=0),
        item,
        new_row('item', description='CONCRETO', unit='m3', level=1),
    ])


class SteelDistributionRulesTests(unittest.TestCase):
    def test_default_and_custom_templates_parse_common_autocad_text(self):
        parsed = parse_distribution(' 1%%c1" @ .275 ', DEFAULT_TEMPLATE)
        self.assertEqual(parsed['multiplier'], 1)
        self.assertEqual(parsed['diameter'], '1"')
        self.assertEqual(parsed['spacing_m'], Decimal('.275'))

        custom = 'Ø{diametro} c/{espaciamiento}'
        parsed = parse_distribution('ø 3/4" c/0,20', custom)
        self.assertEqual(parsed['multiplier'], 1)
        self.assertEqual(parsed['diameter'], '3/4"')
        self.assertEqual(parsed['spacing_m'], Decimal('.20'))

    def test_count_rounds_intervals_up_and_includes_both_ends(self):
        self.assertEqual(distributed_bar_count('2', '.275', 1), 9)
        self.assertEqual(distributed_bar_count('.55', '.275', 2), 6)

    def test_invalid_templates_and_unknown_diameter_are_rejected(self):
        for template in ('texto', '{diametro}',
                         '{diametro}@{espaciamiento}{espaciamiento}',
                         '{otro}@{espaciamiento}'):
            with self.subTest(template=template), self.assertRaises(ValueError):
                validate_template(template)
        with self.assertRaisesRegex(ValueError, 'tabla global'):
            parse_distribution('1Ø7/8"@.20')


class SteelDistributionStoreAndDialogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = CatalogStore(Path(self.temp.name) / 'steel.db')

    def tearDown(self):
        self.temp.cleanup()

    def test_global_format_persists_without_changing_catalog(self):
        before = sc.initial_catalog()
        template, revision = self.store.read_distribution_format()
        self.assertEqual(template, DEFAULT_TEMPLATE)
        changed = 'Ø{diametro} c/{espaciamiento}'
        revision = self.store.save_distribution_format(changed, revision)
        self.assertEqual(self.store.read_distribution_format(), (changed, revision))
        self.assertEqual(self.store.read()[0], before)

    def test_dialog_previews_and_rejects_invalid_format(self):
        dialog = DistributionFormatDialog(DEFAULT_TEMPLATE)
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        dialog.template.setText('{diametro}')
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        dialog.template.setText('Ø{diametro} c/{espaciamiento}')
        dialog.sample.setText('Ø1/2" c/.20')
        self.assertEqual(dialog.configuration(), 'Ø{diametro} c/{espaciamiento}')
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.Save).isEnabled())
        dialog.deleteLater()


class AutoCadSteelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = CatalogStore(Path(self.temp.name) / 'steel.db')
        self.window = PlantillaWindow(engine, self.store)
        self.window._load('Prueba', materialize(rows()))
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def test_creates_managed_detail_suffix_lap_weight_and_one_undo(self):
        self.window._select(1)
        result = self.window.insert_autocad_steel(
            'VERTICAL INTERIOR', 10.85, 2.0, '1Ø1"@.275')
        detail = self.window.model.rows[2]
        catalog = self.window.model.rows[1]['steel_catalog']

        self.assertEqual(detail['cells'][1], 'VERTICAL INTERIOR 9 Ø1"')
        self.assertEqual(detail['cells'][3], '1')
        self.assertEqual(detail['cells'][4], '10.85')
        self.assertEqual(detail['cells'][5], '0.00')
        self.assertEqual(detail['cells'][6], catalog['1"']['lap'])
        self.assertEqual(detail['cells'][7], '1"')
        self.assertEqual(detail['cells'][9:11], ['1', '9'])
        self.assertEqual(detail['steel_hooks']['count'], 0)
        self.assertEqual(self.window.model.values[(2, 11)],
                         float(catalog['1"']['weight']))
        self.assertEqual(result['bars'], 9)

        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), 3)

    def test_protocol_dispatches_and_incompatible_item_is_atomic(self):
        self.window._select(1)
        dispatcher = AutoCadRequestDispatcher(self.window)
        protocol = BridgeProtocol('secret', 'session', dispatcher.dispatch)
        _, authenticated = protocol.handle({
            'protocol': PROTOCOL_VERSION, 'type': 'hello',
            'request_id': str(uuid.uuid4()), 'token': 'secret',
            'client': {'name': 'AutoCAD 2021'},
        }, False)
        response, _ = protocol.handle(message({
            'description': 'HORIZONTAL', 'length_m': 8.5,
            'distribution_m': 1.0, 'distribution_text': '2Ø1/2"@.25',
            'drawing': 'obra.dwg', 'drawing_unit': 'm',
        }), authenticated)
        self.assertTrue(response['ok'])
        self.assertEqual(response['type'], 'steel_distribution_ack')
        self.assertEqual(self.window.model.rows[2]['cells'][1], 'HORIZONTAL 10 Ø1/2"')

        self.window._load('Prueba', materialize(rows()))
        self.window._select(2)
        before = materialize(self.window.model.rows)
        with self.assertRaisesRegex(ValueError, 'unidad kg'):
            self.window.insert_autocad_steel('ACERO', 2, 2, '1Ø1/2"@.20')
        self.assertEqual(self.window.model.rows, before)

    def test_invalid_payload_is_rejected(self):
        valid = {
            'description': 'ACERO', 'length_m': 2,
            'distribution_m': 3, 'distribution_text': '1Ø1/2"@.20',
        }
        for change in (
            {'description': ''}, {'length_m': 0},
            {'distribution_m': float('inf')}, {'distribution_text': ''},
        ):
            payload = {**valid, **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_steel_distribution_request({
                    'type': 'steel_distribution', 'payload': payload})


if __name__ == '__main__':
    unittest.main()

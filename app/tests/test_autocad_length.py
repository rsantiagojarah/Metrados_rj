"""Length and perimeter transfer from AutoCAD into the active item."""
import os
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

import metrado._enlace as engine
from metrado.autocad_bridge import BridgeProtocol, PROTOCOL_VERSION
from metrado.autocad_integration import AutoCadRequestDispatcher, validate_length_request
from metrado.hierarchy import renumber
from metrado.sheet import new_row
from metrado.window import PlantillaWindow


APP = QApplication.instance() or QApplication([])


def message(message_type, **values):
    return {
        'protocol': PROTOCOL_VERSION,
        'type': message_type,
        'request_id': str(uuid.uuid4()),
        **values,
    }


def rows():
    return renumber([
        new_row('chapter', description='OBRAS', level=0),
        new_row('item', description='PERÍMETRO', unit='m', level=1),
        new_row('item', description='ENCOFRADO', unit='m2', level=1),
        new_row('item', description='MURO', unit='m3', level=1),
        new_row('item', description='ACERO', unit='kg', level=1),
    ])


class AutoCadLengthTests(unittest.TestCase):
    def setUp(self):
        self.window = PlantillaWindow(engine)
        self.window._load('Prueba', rows())
        self.window.show()
        APP.processEvents()

    def tearDown(self):
        with patch.object(self.window, '_can_discard', return_value=True):
            self.window.close()
        self.window.deleteLater()
        APP.processEvents()

    def test_meter_item_receives_direct_length_and_undoes(self):
        self.window._select(1)
        result = self.window.insert_autocad_length('BORDE EXTERIOR', 18.75, 3)
        detail = self.window.model.rows[2]
        self.assertEqual(detail['direct'], '18.75')
        self.assertEqual(self.window.model.data(self.window.model.index(1, 13)), '18.75')
        self.assertEqual(result['length_m'], 18.75)
        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), 5)

    def test_square_and_cubic_items_receive_length_in_largo(self):
        for owner, dimensions, expected in ((2, ((5, '2'),), 20),
                                             (3, ((5, '2'), (6, '0.5')), 10)):
            with self.subTest(owner=owner):
                self.window._load('Prueba', rows())
                self.window._select(owner)
                self.window.insert_autocad_length('TRAMO', 10.0, 1)
                detail = owner + 1
                self.assertEqual(self.window.model.rows[detail]['cells'][4], '10.00')
                self.assertIn(detail, self.window.model.errors)
                for column, value in dimensions:
                    self.assertTrue(self.window.model.setData(
                        self.window.model.index(detail, column), value))
                self.assertEqual(self.window.model.data(
                    self.window.model.index(owner, 13)), f'{expected:.2f}')

    def test_length_is_stored_with_two_decimals_before_calculating(self):
        self.window._select(2)
        result = self.window.insert_autocad_length('CERCO', 344.789697744, 1)
        detail = self.window.model.rows[3]
        self.assertEqual(detail['cells'][4], '344.79')
        self.assertEqual(result['length_m'], 344.79)

        self.assertTrue(self.window.model.setData(
            self.window.model.index(3, 5), '2'))
        self.assertEqual(self.window.model.data(
            self.window.model.index(2, 13)), '689.58')

    def test_protocol_dispatches_length_and_rejects_incompatible_item(self):
        self.window._select(1)
        dispatcher = AutoCadRequestDispatcher(self.window)
        protocol = BridgeProtocol('secret', 'session', dispatcher.dispatch)
        _, authenticated = protocol.handle(message(
            'hello', token='secret', client={'name': 'AutoCAD 2021'}), False)
        response, _ = protocol.handle(message('length_measurement', payload={
            'name': '  CERCO   TOTAL ', 'length_m': 12.5,
            'entity_count': 2, 'drawing': 'obra.dwg', 'drawing_unit': 'm',
        }), authenticated)
        self.assertTrue(response['ok'])
        self.assertEqual(response['type'], 'length_measurement_ack')
        self.assertEqual(self.window.model.rows[2]['cells'][1], 'CERCO TOTAL')

        self.window._load('Prueba', rows())
        self.window._select(4)
        with self.assertRaisesRegex(ValueError, 'm, m² o m³'):
            self.window.insert_autocad_length('ACERO', 2, 1)

    def test_batch_adds_individual_lengths_by_name_or_layer_with_one_undo(self):
        self.window._select(2)
        dispatcher = AutoCadRequestDispatcher(self.window)
        response = dispatcher.dispatch({
            'type': 'length_measurement',
            'payload': {
                'measurements': [
                    {'name': 'CERCO', 'length_m': 10.126, 'entity_count': 1},
                    {'name': 'A-MUROS', 'length_m': 4.444, 'entity_count': 1},
                ],
                'drawing': 'obra.dwg', 'drawing_unit': 'm',
            },
        })

        self.assertEqual([row['cells'][1] for row in self.window.model.rows[3:5]],
                         ['CERCO', 'A-MUROS'])
        self.assertEqual([row['cells'][4] for row in self.window.model.rows[3:5]],
                         ['10.13', '4.44'])
        self.assertEqual(response['inserted_count'], 2)
        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), 5)

    def test_invalid_length_payload_is_rejected(self):
        for payload in (
            {},
            {'name': '', 'length_m': 2, 'entity_count': 1},
            {'name': 'TRAMO', 'length_m': float('inf'), 'entity_count': 1},
            {'name': 'TRAMO', 'length_m': -1, 'entity_count': 1},
            {'measurements': []},
            {'measurements': [
                {'name': 'TRAMO', 'length_m': float('nan'), 'entity_count': 1},
            ]},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_length_request({'type': 'length_measurement', 'payload': payload})


if __name__ == '__main__':
    unittest.main()

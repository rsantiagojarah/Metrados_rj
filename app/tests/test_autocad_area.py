"""Area transfer from AutoCAD into the active m² item."""
import os
import threading
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication

import metrado._enlace as engine
from metrado.autocad_bridge import BridgeProtocol, PROTOCOL_VERSION
from metrado.autocad_integration import AutoCadRequestDispatcher, validate_area_request
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
        new_row('item', description='PISO', unit='m2', level=1),
        new_row('item', description='CONCRETO', unit='m3', level=1),
    ])


class AutoCadAreaTests(unittest.TestCase):
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

    def test_adds_one_direct_detail_to_active_square_meter_item_and_undoes(self):
        self.window._select(1)
        result = self.window.insert_autocad_area(
            'LOSA PRINCIPAL', 24.75, 3, 2, 'plano.dwg', 'm')

        self.assertEqual(len(self.window.model.rows), 4)
        detail = self.window.model.rows[2]
        self.assertEqual(detail['kind'], 'detail')
        self.assertEqual(detail['cells'][1], 'LOSA PRINCIPAL')
        self.assertEqual(detail['cells'][2], 'm2')
        self.assertEqual(detail['direct'], '24.75')
        self.assertEqual(self.window.model.data(self.window.model.index(1, 13)), '24.75')
        self.assertEqual(result['detail_id'], detail['id'])

        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), 3)
        self.assertEqual(self.window.model.rows[1]['cells'][1], 'PISO')

    def test_cubic_item_receives_pending_area_then_user_adds_dimension(self):
        self.window._select(2)
        self.window.insert_autocad_area('EXCAVACIÓN IRREGULAR', 10.0, 1)
        detail = self.window.model.rows[3]
        self.assertEqual(detail['cells'][2], 'm3')
        self.assertEqual(detail['cells'][9], '10')
        self.assertEqual(detail['direct'], '')
        self.assertIn(3, self.window.model.errors)
        self.assertTrue(self.window.model.setData(self.window.model.index(3, 6), '0.10'))
        self.assertEqual(self.window.model.data(self.window.model.index(2, 13)), '1.00')

    def test_rejects_when_active_item_cannot_receive_an_area(self):
        incompatible = rows()
        incompatible[2]['cells'][2] = 'kg'
        self.window._load('Prueba', incompatible)
        self.window._select(2)
        with self.assertRaisesRegex(ValueError, 'm² o m³'):
            self.window.insert_autocad_area('PESO', 10.0, 1)

    def test_protocol_validates_and_inserts_authenticated_measurement(self):
        self.window._select(1)
        dispatcher = AutoCadRequestDispatcher(self.window)
        protocol = BridgeProtocol('secret', 'session', dispatcher.dispatch)
        _, authenticated = protocol.handle(message(
            'hello', token='secret', client={'name': 'AutoCAD 2021'}), False)
        response, _ = protocol.handle(message('area_measurement', payload={
            'name': '  VEREDA   NORTE ', 'area_m2': 12.5,
            'entity_count': 2, 'region_count': 1,
            'drawing': 'obra.dwg', 'drawing_unit': 'm',
        }), authenticated)

        self.assertTrue(response['ok'])
        self.assertEqual(response['type'], 'area_measurement_ack')
        self.assertEqual(self.window.model.rows[2]['cells'][1], 'VEREDA NORTE')

    def test_background_request_is_dispatched_to_qt_thread(self):
        self.window._select(1)
        dispatcher = AutoCadRequestDispatcher(self.window)
        result = []

        worker = threading.Thread(target=lambda: result.append(dispatcher.dispatch({
            'type': 'area_measurement',
            'payload': {'name': 'PATIO', 'area_m2': 8.25, 'entity_count': 1},
        })))
        worker.start()
        while worker.is_alive():
            APP.processEvents()
            worker.join(0.01)
        worker.join()

        self.assertEqual(result[0]['area_m2'], 8.25)
        self.assertEqual(self.window.model.rows[2]['cells'][1], 'PATIO')

    def test_batch_adds_individual_areas_by_name_or_layer_with_one_undo(self):
        self.window._select(1)
        dispatcher = AutoCadRequestDispatcher(self.window)
        response = dispatcher.dispatch({
            'type': 'area_measurement',
            'payload': {
                'measurements': [
                    {'name': 'PISOS', 'area_m2': 12.5,
                     'entity_count': 1, 'region_count': 1},
                    {'name': 'A-VEREDA', 'area_m2': 7.25,
                     'entity_count': 1, 'region_count': 1},
                ],
                'drawing': 'obra.dwg', 'drawing_unit': 'm',
            },
        })

        self.assertEqual([row['cells'][1] for row in self.window.model.rows[2:4]],
                         ['PISOS', 'A-VEREDA'])
        self.assertEqual([row['direct'] for row in self.window.model.rows[2:4]],
                         ['12.5', '7.25'])
        self.assertEqual(response['inserted_count'], 2)
        self.window.model.undo_stack.undo()
        self.assertEqual(len(self.window.model.rows), 3)

    def test_invalid_payload_is_rejected_as_a_complete_operation(self):
        for payload in (
            {},
            {'name': '', 'area_m2': 2, 'entity_count': 1},
            {'name': 'ZONA', 'area_m2': float('inf'), 'entity_count': 1},
            {'name': 'ZONA', 'area_m2': 2, 'entity_count': 0},
            {'measurements': []},
            {'measurements': [
                {'name': 'ZONA', 'area_m2': -1, 'entity_count': 1,
                 'region_count': 1},
            ]},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_area_request({'type': 'area_measurement', 'payload': payload})


if __name__ == '__main__':
    unittest.main()

"""Checks for the reusable AutoCAD 2021 connection."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid

from metrado.autocad_bridge import (
    AutoCadBridgeServer, BridgeProtocol, PROTOCOL_VERSION,
)


def request(message_type, **values):
    return {
        "protocol": PROTOCOL_VERSION,
        "type": message_type,
        "request_id": str(uuid.uuid4()),
        **values,
    }


class BridgeProtocolTests(unittest.TestCase):
    def setUp(self):
        self.token = "secret-session-token"
        self.protocol = BridgeProtocol(self.token, "session-1")

    def authenticate(self):
        message = request("hello", token=self.token, client={
            "name": "test-client", "version": "1", "process_id": 10,
            "autocad_release": "AutoCAD 2021",
        })
        response, authenticated = self.protocol.handle(message, False)
        self.assertTrue(response["ok"])
        self.assertEqual(response["type"], "hello_ack")
        self.assertTrue(authenticated)
        return authenticated

    def test_rejects_requests_before_authentication(self):
        response, authenticated = self.protocol.handle(request("ping"), False)
        self.assertFalse(authenticated)
        self.assertEqual(response["error"]["code"], "authentication_required")

    def test_rejects_wrong_token_without_echoing_it(self):
        response, authenticated = self.protocol.handle(request(
            "hello", token="wrong", client={"name": "AutoCAD"}), False)
        self.assertFalse(authenticated)
        self.assertEqual(response["error"]["code"], "authentication_failed")
        self.assertNotIn("wrong", json.dumps(response))

    def test_rejects_wrong_protocol_and_invalid_identifier(self):
        message = request("hello", token=self.token, client={"name": "AutoCAD"})
        message["protocol"] = 99
        response, _ = self.protocol.handle(message, False)
        self.assertEqual(response["error"]["code"], "unsupported_protocol")
        message["protocol"] = PROTOCOL_VERSION
        message["request_id"] = "not-a-uuid"
        response, _ = self.protocol.handle(message, False)
        self.assertEqual(response["error"]["code"], "invalid_request_id")

    def test_ping_is_idempotent(self):
        authenticated = self.authenticate()
        message = request("ping")
        first, authenticated = self.protocol.handle(message, authenticated)
        second, _ = self.protocol.handle(message, authenticated)
        self.assertEqual(first, second)
        self.assertEqual(first["type"], "pong")

    def test_handler_extends_same_connection(self):
        handled = []
        protocol = BridgeProtocol(self.token, "session-1",
                                  lambda message: handled.append(message["type"]) or {"value": 12})
        hello = request("hello", token=self.token, client={"name": "AutoCAD"})
        _, authenticated = protocol.handle(hello, False)
        response, _ = protocol.handle(request("future_measurement"), authenticated)
        self.assertEqual(handled, ["future_measurement"])
        self.assertEqual(response["result"]["value"], 12)


@unittest.skipUnless(os.name == "nt", "La tubería local se prueba en Windows.")
class BridgeServerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.mutex_name = "Local\\Metrados.Test." + uuid.uuid4().hex
        self.server = AutoCadBridgeServer(Path(self.folder.name), mutex_name=self.mutex_name)

    def tearDown(self):
        self.server.stop()
        self.folder.cleanup()

    def test_lifecycle_publishes_and_removes_session(self):
        self.assertTrue(self.server.start())
        descriptor = json.loads(self.server.session_path.read_text(encoding="utf-8"))
        self.assertEqual(descriptor["protocol"], PROTOCOL_VERSION)
        self.assertEqual(descriptor["session_id"], self.server.session_id)
        self.assertGreaterEqual(len(descriptor["token"]), 32)
        self.assertTrue(self.server.running)
        self.server.stop()
        self.assertFalse(self.server.running)
        self.assertFalse(self.server.session_path.exists())

    def test_single_server_owns_the_published_session(self):
        self.assertTrue(self.server.start())
        second = AutoCadBridgeServer(Path(self.folder.name), mutex_name=self.mutex_name)
        try:
            self.assertFalse(second.start())
            self.assertIn("Otra instancia", second.last_error)
        finally:
            second.stop()

    def test_compiled_autocad_client_uses_the_real_protocol(self):
        probe = self.compiled_probe()
        if not probe.exists():
            self.skipTest("Compila primero el complemento de AutoCAD 2021.")
        self.assertTrue(self.server.start())
        environment = os.environ.copy()
        environment["METRADOS_BRIDGE_SESSION"] = str(self.server.session_path)
        completed = subprocess.run(
            [str(probe)], capture_output=True, text=True, timeout=10,
            env=environment, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("conectado correctamente", completed.stdout)

    def test_compiled_client_reconnects_to_a_new_server_session(self):
        probe = self.compiled_probe()
        if not probe.exists():
            self.skipTest("Compila primero el complemento de AutoCAD 2021.")
        self.assertTrue(self.server.start())
        environment = os.environ.copy()
        environment["METRADOS_BRIDGE_SESSION"] = str(self.server.session_path)
        process = subprocess.Popen(
            [str(probe), "--reconnect"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=environment,
        )
        try:
            first = process.stdout.readline()
            self.assertIn("conectado correctamente", first)
            old_session = self.server.session_id
            self.server.stop()
            self.server = AutoCadBridgeServer(Path(self.folder.name), mutex_name=self.mutex_name)
            self.assertTrue(self.server.start())
            self.assertNotEqual(self.server.session_id, old_session)
            remaining, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, first + remaining + errors)
            self.assertIn("conectado correctamente", remaining)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(5)

    def test_compiled_client_sends_area_payload(self):
        probe = self.compiled_probe()
        if not probe.exists():
            self.skipTest("Compila primero el complemento de AutoCAD 2021.")
        received = []
        self.server.request_handler = lambda value: received.append(value) or {'accepted': True}
        self.assertTrue(self.server.start())
        environment = os.environ.copy()
        environment["METRADOS_BRIDGE_SESSION"] = str(self.server.session_path)
        completed = subprocess.run(
            [str(probe), "--area"], capture_output=True, timeout=10,
            env=environment, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['type'], 'area_measurement')
        self.assertEqual(received[0]['payload']['name'], 'ÁREA DE PRUEBA')
        self.assertEqual(received[0]['payload']['area_m2'], 12.5)

    def test_compiled_client_sends_length_payload(self):
        probe = self.compiled_probe()
        if not probe.exists():
            self.skipTest("Compila primero el complemento de AutoCAD 2021.")
        received = []
        self.server.request_handler = lambda value: received.append(value) or {'accepted': True}
        self.assertTrue(self.server.start())
        environment = os.environ.copy()
        environment["METRADOS_BRIDGE_SESSION"] = str(self.server.session_path)
        completed = subprocess.run(
            [str(probe), "--length"], capture_output=True, timeout=10,
            env=environment, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['type'], 'length_measurement')
        self.assertEqual(received[0]['payload']['name'], 'LONGITUD DE PRUEBA')
        self.assertEqual(received[0]['payload']['length_m'], 8.75)

    def test_compiled_client_serializes_area_batch(self):
        received = self.run_probe_and_capture('--area-batch')
        measurements = received['payload']['measurements']
        self.assertEqual([value['name'] for value in measurements],
                         ['A-PISOS', 'A-VEREDA'])
        self.assertEqual([value['area_m2'] for value in measurements],
                         [12.5, 7.25])

    def test_compiled_client_serializes_length_batch(self):
        received = self.run_probe_and_capture('--length-batch')
        measurements = received['payload']['measurements']
        self.assertEqual([value['name'] for value in measurements],
                         ['CERCO', 'A-MUROS'])
        self.assertEqual([value['length_m'] for value in measurements],
                         [10.125, 4.445])

    def test_compiled_client_serializes_distributed_steel(self):
        received = self.run_probe_and_capture('--steel')
        self.assertEqual(received['type'], 'steel_distribution')
        self.assertEqual(received['payload']['description'], 'ACERO DE PRUEBA')
        self.assertEqual(received['payload']['length_m'], 8.5)
        self.assertEqual(received['payload']['distribution_m'], 2.0)
        self.assertEqual(received['payload']['distribution_text'], '1Ø1/2"@.20')

    def run_probe_and_capture(self, argument):
        probe = self.compiled_probe()
        if not probe.exists():
            self.skipTest("Compila primero el complemento de AutoCAD 2021.")
        received = []
        self.server.request_handler = lambda value: received.append(value) or {'accepted': True}
        self.assertTrue(self.server.start())
        environment = os.environ.copy()
        environment["METRADOS_BRIDGE_SESSION"] = str(self.server.session_path)
        completed = subprocess.run(
            [str(probe), argument], capture_output=True, timeout=10,
            env=environment, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(len(received), 1)
        return received[0]

    @staticmethod
    def compiled_probe():
        root = Path(__file__).resolve().parents[2]
        return root / "target" / "autocad" / "Metrados.AutoCAD2021.Probe.exe"


if __name__ == "__main__":
    unittest.main()

"""Local, authenticated bridge used by the AutoCAD plug-in.

The transport is deliberately independent from Qt and from the metrado model.  Future
commands can register a request handler without creating another connection.
"""
from __future__ import annotations

from collections import OrderedDict
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
from typing import Callable
import uuid


PROTOCOL_VERSION = 1
SERVER_NAME = "Metrados"
MAX_MESSAGE_BYTES = 1_048_576
MAX_CACHED_RESPONSES = 512
SESSION_FILE_NAME = "session.json"
DEFAULT_MUTEX_NAME = r"Local\Metrados.AutoCADBridge"


class BridgeError(RuntimeError):
    """Raised when the local bridge cannot start or exchange a valid message."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def default_state_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "Metrados" / "bridge"
    return Path(tempfile.gettempdir()) / "Metrados" / "bridge"


def _strict_json(text: str):
    def reject_constant(value):
        raise ValueError(f"Constante JSON no permitida: {value}")

    return json.loads(text, parse_constant=reject_constant)


def _json_line(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                       allow_nan=False) + "\n").encode("utf-8")


def _valid_request_id(value) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return True


class BridgeProtocol:
    """Versioned message dispatcher with authentication and idempotent replies."""

    def __init__(self, token: str, session_id: str,
                 request_handler: Callable[[dict], dict | None] | None = None):
        self._token = token
        self.session_id = session_id
        self.request_handler = request_handler
        self.client = None
        self._responses: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def handle(self, message, authenticated: bool) -> tuple[dict, bool]:
        request_id = message.get("request_id", "") if isinstance(message, dict) else ""
        if not isinstance(message, dict):
            return self._error(request_id, "invalid_message", "El mensaje debe ser un objeto JSON."), authenticated
        if message.get("protocol") != PROTOCOL_VERSION:
            return self._error(request_id, "unsupported_protocol",
                               f"Se requiere el protocolo {PROTOCOL_VERSION}."), authenticated
        if not _valid_request_id(request_id):
            return self._error("", "invalid_request_id", "La solicitud no tiene un identificador válido."), authenticated

        message_type = message.get("type")
        if not isinstance(message_type, str) or not message_type or len(message_type) > 64:
            return self._error(request_id, "invalid_type", "El tipo de solicitud no es válido."), authenticated

        if not authenticated:
            if message_type != "hello":
                return self._error(request_id, "authentication_required",
                                   "La conexión debe autenticarse primero."), False
            supplied = message.get("token")
            if not isinstance(supplied, str) or not hmac.compare_digest(supplied, self._token):
                return self._error(request_id, "authentication_failed",
                                   "La sesión no es válida."), False
            client = message.get("client")
            if not isinstance(client, dict):
                return self._error(request_id, "invalid_client", "Falta la identificación del cliente."), False
            safe_client = {
                "name": str(client.get("name", ""))[:80],
                "version": str(client.get("version", ""))[:32],
                "process_id": client.get("process_id"),
                "autocad_release": str(client.get("autocad_release", ""))[:32],
            }
            with self._lock:
                self.client = safe_client
            response = self._ok(request_id, "hello_ack", {
                "session_id": self.session_id,
                "server": SERVER_NAME,
                "server_time": _utc_now(),
            })
            self._remember(request_id, response)
            return response, True

        with self._lock:
            previous = self._responses.get(request_id)
            if previous is not None:
                self._responses.move_to_end(request_id)
                return previous, True

        if message_type == "ping":
            response = self._ok(request_id, "pong", {
                "session_id": self.session_id,
                "server_time": _utc_now(),
            })
        elif message_type == "status":
            response = self._ok(request_id, "status_ack", {
                "session_id": self.session_id,
                "ready": True,
                "server_time": _utc_now(),
            })
        elif self.request_handler is not None:
            try:
                result = self.request_handler(message)
                if result is None:
                    result = {}
                if not isinstance(result, dict):
                    raise TypeError("El controlador debe devolver un objeto.")
                response = self._ok(request_id, message_type + "_ack", result)
            except (TypeError, ValueError) as error:
                response = self._error(request_id, "invalid_operation", str(error))
            except Exception:
                response = self._error(request_id, "operation_failed",
                                       "La operación no pudo completarse.")
        else:
            response = self._error(request_id, "unsupported_operation",
                                   "La operación todavía no está disponible.")
        self._remember(request_id, response)
        return response, True

    def disconnect(self):
        with self._lock:
            self.client = None

    def _remember(self, request_id: str, response: dict):
        with self._lock:
            self._responses[request_id] = response
            self._responses.move_to_end(request_id)
            while len(self._responses) > MAX_CACHED_RESPONSES:
                self._responses.popitem(last=False)

    @staticmethod
    def _ok(request_id: str, message_type: str, result: dict) -> dict:
        return {
            "protocol": PROTOCOL_VERSION,
            "type": message_type,
            "request_id": request_id,
            "ok": True,
            "result": result,
        }

    @staticmethod
    def _error(request_id: str, code: str, message: str) -> dict:
        return {
            "protocol": PROTOCOL_VERSION,
            "type": "error",
            "request_id": request_id,
            "ok": False,
            "error": {"code": code, "message": message},
        }


if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateNamedPipeW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
    ]
    _kernel32.CreateNamedPipeW.restype = wintypes.HANDLE
    _kernel32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    _kernel32.ConnectNamedPipe.restype = wintypes.BOOL
    _kernel32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    _kernel32.DisconnectNamedPipe.restype = wintypes.BOOL
    _kernel32.ReadFile.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    _kernel32.ReadFile.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = [
        wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    _kernel32.WriteFile.restype = wintypes.BOOL
    _kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.CancelIoEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    _kernel32.CancelIoEx.restype = wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    _kernel32.CreateMutexW.restype = wintypes.HANDLE


class AutoCadBridgeServer:
    """Single-instance Windows named-pipe server for all AutoCAD operations."""

    PIPE_ACCESS_DUPLEX = 0x00000003
    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000
    PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
    ERROR_ALREADY_EXISTS = 183
    ERROR_PIPE_CONNECTED = 535
    ERROR_OPERATION_ABORTED = 995
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    def __init__(self, state_dir: Path | None = None,
                 request_handler: Callable[[dict], dict | None] | None = None,
                 state_callback: Callable[[str, dict], None] | None = None,
                 mutex_name: str = DEFAULT_MUTEX_NAME):
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.session_path = self.state_dir / SESSION_FILE_NAME
        self.request_handler = request_handler
        self.state_callback = state_callback
        self.mutex_name = mutex_name
        self.session_id = ""
        self.pipe_name = ""
        self.last_error = ""
        self._token = ""
        self._protocol = None
        self._thread = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._handle = None
        self._handle_lock = threading.Lock()
        self._mutex = None
        self._startup_error = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    @property
    def connected_client(self):
        return None if self._protocol is None else self._protocol.client

    def start(self) -> bool:
        if self.running:
            return True
        if os.name != "nt":
            self.last_error = "La conexión con AutoCAD solo está disponible en Windows."
            return False
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self._acquire_mutex():
            self.last_error = "Otra instancia de Metrados administra la conexión con AutoCAD."
            self._diagnostic("server_skipped", reason="already_running")
            return False

        self.session_id = str(uuid.uuid4())
        self.pipe_name = "Metrados.AutoCAD." + uuid.uuid4().hex
        self._token = secrets.token_urlsafe(32)
        self._protocol = BridgeProtocol(self._token, self.session_id, self.request_handler)
        self._stop.clear()
        self._ready.clear()
        self._startup_error = None
        self._thread = threading.Thread(target=self._run, name="MetradosAutoCADBridge", daemon=True)
        self._thread.start()
        if not self._ready.wait(3):
            self.stop()
            raise BridgeError("La conexión local no respondió al iniciar.")
        if self._startup_error is not None:
            error = self._startup_error
            self.stop()
            raise BridgeError(str(error))
        try:
            self._write_session()
        except OSError as error:
            self.stop()
            raise BridgeError("No se pudo publicar la sesión local de AutoCAD.") from error
        self._diagnostic("server_started", pipe=self.pipe_name, session_id=self.session_id)
        self._notify("listening", {"session_id": self.session_id})
        return True

    def stop(self):
        self._stop.set()
        with self._handle_lock:
            handle = self._handle
        if handle not in (None, self.INVALID_HANDLE_VALUE):
            _kernel32.CancelIoEx(handle, None)
            _kernel32.DisconnectNamedPipe(handle)
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(3)
        self._thread = None
        self._remove_own_session()
        if self._mutex is not None:
            _kernel32.CloseHandle(self._mutex)
            self._mutex = None
        if self.session_id:
            self._diagnostic("server_stopped", session_id=self.session_id)
        self._notify("stopped", {})

    def _acquire_mutex(self) -> bool:
        handle = _kernel32.CreateMutexW(None, False, self.mutex_name)
        if not handle:
            raise BridgeError(f"No se pudo crear el control de instancia ({ctypes.get_last_error()}).")
        error = ctypes.get_last_error()
        if error == self.ERROR_ALREADY_EXISTS:
            _kernel32.CloseHandle(handle)
            return False
        self._mutex = handle
        return True

    def _run(self):
        first = True
        while not self._stop.is_set():
            try:
                handle = self._create_pipe()
            except OSError as error:
                self._startup_error = error
                self.last_error = str(error)
                self._ready.set()
                self._diagnostic("pipe_error", error=str(error))
                return
            with self._handle_lock:
                self._handle = handle
            if first:
                first = False
                self._ready.set()
            try:
                connected = bool(_kernel32.ConnectNamedPipe(handle, None))
                if not connected:
                    error = ctypes.get_last_error()
                    connected = error == self.ERROR_PIPE_CONNECTED
                    if not connected and error != self.ERROR_OPERATION_ABORTED and not self._stop.is_set():
                        raise OSError(error, "No se pudo aceptar la conexión de AutoCAD.")
                if connected and not self._stop.is_set():
                    self._diagnostic("client_transport_connected")
                    self._serve_client(handle)
            except OSError as error:
                if not self._stop.is_set():
                    self.last_error = str(error)
                    self._diagnostic("client_error", error=str(error))
            finally:
                if self._protocol is not None:
                    self._protocol.disconnect()
                _kernel32.DisconnectNamedPipe(handle)
                _kernel32.CloseHandle(handle)
                with self._handle_lock:
                    if self._handle == handle:
                        self._handle = None
                self._notify("disconnected", {})

    def _create_pipe(self):
        path = "\\\\.\\pipe\\" + self.pipe_name
        handle = _kernel32.CreateNamedPipeW(
            path,
            self.PIPE_ACCESS_DUPLEX | self.FILE_FLAG_FIRST_PIPE_INSTANCE,
            self.PIPE_TYPE_BYTE | self.PIPE_READMODE_BYTE | self.PIPE_WAIT |
            self.PIPE_REJECT_REMOTE_CLIENTS,
            1,
            65_536,
            65_536,
            5_000,
            None,
        )
        if handle == self.INVALID_HANDLE_VALUE:
            error = ctypes.get_last_error()
            raise OSError(error, "No se pudo crear la tubería local de AutoCAD.")
        return handle

    def _serve_client(self, handle):
        authenticated = False
        pending = bytearray()
        while not self._stop.is_set():
            chunk = ctypes.create_string_buffer(4096)
            read = wintypes.DWORD()
            if not _kernel32.ReadFile(handle, chunk, len(chunk), ctypes.byref(read), None):
                error = ctypes.get_last_error()
                if error in (109, 232, self.ERROR_OPERATION_ABORTED):
                    return
                raise OSError(error, "No se pudo leer la conexión de AutoCAD.")
            if read.value == 0:
                return
            pending.extend(chunk.raw[:read.value])
            if len(pending) > MAX_MESSAGE_BYTES and b"\n" not in pending:
                self._write(handle, BridgeProtocol._error("", "message_too_large",
                                                          "El mensaje excede el límite permitido."))
                return
            while b"\n" in pending:
                raw, _, remainder = pending.partition(b"\n")
                pending = bytearray(remainder)
                if not raw.strip():
                    continue
                if len(raw) > MAX_MESSAGE_BYTES:
                    self._write(handle, BridgeProtocol._error("", "message_too_large",
                                                              "El mensaje excede el límite permitido."))
                    return
                try:
                    message = _strict_json(raw.decode("utf-8"))
                    response, authenticated = self._protocol.handle(message, authenticated)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    response = BridgeProtocol._error("", "invalid_json", "El mensaje JSON no es válido.")
                self._write(handle, response)
                if authenticated and response["type"] == "hello_ack":
                    self._diagnostic("client_authenticated", client=self.connected_client)
                    self._notify("connected", dict(self.connected_client or {}))
                if response.get("error", {}).get("code") == "authentication_failed":
                    self._diagnostic("authentication_failed")
                    return

    @staticmethod
    def _write(handle, response: dict):
        payload = _json_line(response)
        if len(payload) > MAX_MESSAGE_BYTES:
            raise OSError("La respuesta excede el límite permitido.")
        offset = 0
        while offset < len(payload):
            buffer = ctypes.create_string_buffer(payload[offset:])
            written = wintypes.DWORD()
            if not _kernel32.WriteFile(handle, buffer, len(payload) - offset,
                                       ctypes.byref(written), None):
                error = ctypes.get_last_error()
                raise OSError(error, "No se pudo responder a AutoCAD.")
            if written.value == 0:
                raise OSError("La conexión con AutoCAD no aceptó la respuesta.")
            offset += written.value

    def _write_session(self):
        descriptor = {
            "protocol": PROTOCOL_VERSION,
            "pipe": self.pipe_name,
            "token": self._token,
            "server_pid": os.getpid(),
            "session_id": self.session_id,
            "started_at": _utc_now(),
        }
        temporary = self.state_dir / f".{SESSION_FILE_NAME}.{os.getpid()}.tmp"
        temporary.write_text(json.dumps(descriptor, ensure_ascii=False, separators=(",", ":")),
                             encoding="utf-8")
        os.replace(temporary, self.session_path)

    def _remove_own_session(self):
        try:
            descriptor = _strict_json(self.session_path.read_text(encoding="utf-8"))
            if descriptor.get("session_id") == self.session_id:
                self.session_path.unlink(missing_ok=True)
        except (OSError, ValueError, json.JSONDecodeError, AttributeError):
            pass

    def _diagnostic(self, event: str, **details):
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            path = self.state_dir / "bridge.log"
            backup = self.state_dir / "bridge.log.1"
            if path.exists() and path.stat().st_size > 1_048_576:
                backup.unlink(missing_ok=True)
                path.replace(backup)
            entry = {"time": _utc_now(), "event": event, **details}
            with path.open("a", encoding="utf-8") as output:
                output.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError:
            pass

    def _notify(self, state: str, details: dict):
        if self.state_callback is None:
            return
        try:
            self.state_callback(state, details)
        except Exception:
            self._diagnostic("state_callback_failed", state=state)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

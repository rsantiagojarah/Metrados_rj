"""Qt-safe dispatch of measurements received from the AutoCAD bridge."""
from __future__ import annotations

import math
from queue import Empty, Queue
from threading import Event

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot


REQUEST_TIMEOUT_SECONDS = 4
MAX_MEASUREMENTS = 10_000


def _measurement_payload(message: dict, message_type: str) -> tuple[dict, dict]:
    if not isinstance(message, dict) or message.get("type") != message_type:
        raise ValueError("La operación solicitada por AutoCAD no está disponible.")
    payload = message.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("AutoCAD no envió los datos de la medición.")
    return payload, {
        "drawing": str(payload.get("drawing", ""))[:500],
        "drawing_unit": str(payload.get("drawing_unit", ""))[:32],
    }


def _measurement_identity(payload: dict, noun: str) -> tuple[str, int]:
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Escribe un nombre para la medición de {noun}.")
    name = " ".join(name.split())
    if len(name) > 200:
        raise ValueError("El nombre de la medición admite hasta 200 caracteres.")

    entity_count = payload.get("entity_count")
    if type(entity_count) is not int or entity_count <= 0 or entity_count > 100_000:
        raise ValueError("La cantidad de objetos seleccionados no es válida.")
    return name, entity_count


def _measurement_entries(payload: dict, noun: str, value_key: str,
                         value_error: str, include_region=False):
    entries = payload.get("measurements")
    if entries is None:
        return None
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_MEASUREMENTS:
        raise ValueError("El lote de mediciones recibido no es válido.")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Una medición del lote no es válida.")
        name, entity_count = _measurement_identity(entry, noun)
        value = entry.get(value_key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(value_error)
        clean = {"name": name, "entity_count": entity_count,
                 value_key: float(value)}
        if include_region:
            region_count = entry.get("region_count", 1)
            if type(region_count) is not int or region_count <= 0 or region_count > 100_000:
                raise ValueError("La cantidad de regiones recibida no es válida.")
            clean["region_count"] = region_count
        result.append(clean)
    return result


def validate_area_request(message: dict) -> dict:
    """Return a small, trusted area payload or reject the complete operation."""
    payload, result = _measurement_payload(message, "area_measurement")
    measurements = _measurement_entries(
        payload, "área", "area_m2",
        "El área recibida debe ser un número positivo y finito.", True)
    if measurements is not None:
        result["measurements"] = measurements
        return result

    name, entity_count = _measurement_identity(payload, "área")
    area = payload.get("area_m2")
    if type(area) not in (int, float) or not math.isfinite(area) or area <= 0:
        raise ValueError("El área recibida debe ser un número positivo y finito.")
    result.update(name=name, entity_count=entity_count, area_m2=float(area),
                  region_count=payload.get("region_count"))
    return result


def validate_length_request(message: dict) -> dict:
    """Return a small, trusted length payload or reject the complete operation."""
    payload, result = _measurement_payload(message, "length_measurement")
    measurements = _measurement_entries(
        payload, "longitud", "length_m",
        "La longitud recibida debe ser un número positivo y finito.")
    if measurements is not None:
        result["measurements"] = measurements
        return result

    name, entity_count = _measurement_identity(payload, "longitud")
    length = payload.get("length_m")
    if type(length) not in (int, float) or not math.isfinite(length) or length <= 0:
        raise ValueError("La longitud recibida debe ser un número positivo y finito.")
    result.update(name=name, entity_count=entity_count, length_m=float(length))
    return result


def validate_steel_distribution_request(message: dict) -> dict:
    """Validate only captured CAD inputs; steel calculations stay in Metrados."""
    payload, result = _measurement_payload(message, "steel_distribution")
    description = payload.get('description')
    if not isinstance(description, str) or not description.strip():
        raise ValueError('Escribe una descripción para el detalle de acero.')
    description = ' '.join(description.split())
    if len(description) > 200:
        raise ValueError('La descripción del acero admite hasta 200 caracteres.')
    distribution_text = payload.get('distribution_text')
    if (not isinstance(distribution_text, str) or not distribution_text.strip() or
            len(distribution_text) > 500):
        raise ValueError('Selecciona un texto de distribución válido en AutoCAD.')
    for key, label in (('length_m', 'El largo'),
                       ('distribution_m', 'La distancia de distribución')):
        value = payload.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'{label} debe ser un número positivo y finito.')
        result[key] = float(value)
    result.update(description=description,
                  distribution_text=distribution_text.strip())
    return result


class AutoCadRequestDispatcher(QObject):
    """Move pipe-server requests onto Qt's main thread before touching widgets."""

    requested = Signal(object, object, object)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.requested.connect(self._receive, Qt.QueuedConnection)

    def dispatch(self, message: dict) -> dict:
        if QThread.currentThread() == self.thread():
            return self._execute(message)
        reply = Queue(maxsize=1)
        cancelled = Event()
        self.requested.emit(message, reply, cancelled)
        try:
            ok, value = reply.get(timeout=REQUEST_TIMEOUT_SECONDS)
        except Empty as error:
            cancelled.set()
            raise ValueError("Metrados no pudo atender la medición en la interfaz.") from error
        if not ok:
            raise ValueError(value)
        return value

    @Slot(object, object, object)
    def _receive(self, message, reply, cancelled):
        if cancelled.is_set():
            return
        try:
            reply.put((True, self._execute(message)))
        except (TypeError, ValueError) as error:
            reply.put((False, str(error)))
        except Exception:
            reply.put((False, "La medición no pudo agregarse a la planilla."))

    def _execute(self, message: dict) -> dict:
        if isinstance(message, dict) and message.get('type') == 'area_measurement':
            values = validate_area_request(message)
            if 'measurements' in values:
                result = self.window.insert_autocad_areas(**values)
                return {
                    'item_code': result['item_code'],
                    'item_description': result['item_description'],
                    'inserted_count': len(result['detail_ids']),
                }
            return self.window.insert_autocad_area(**values)
        if isinstance(message, dict) and message.get('type') == 'length_measurement':
            values = validate_length_request(message)
            if 'measurements' in values:
                result = self.window.insert_autocad_lengths(**values)
                return {
                    'item_code': result['item_code'],
                    'item_description': result['item_description'],
                    'inserted_count': len(result['detail_ids']),
                }
            return self.window.insert_autocad_length(**values)
        if isinstance(message, dict) and message.get('type') == 'steel_distribution':
            return self.window.insert_autocad_steel(
                **validate_steel_distribution_request(message))
        raise ValueError("La operación solicitada por AutoCAD no está disponible.")

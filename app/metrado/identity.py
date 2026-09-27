"""Persistent identities are independent of visible, renumberable item codes."""
from uuid import uuid4


def ensure_ids(rows):
    seen = set()
    for row in rows:
        if 'id' not in row:
            row['id'] = uuid4().hex
        identity = row['id']
        if not isinstance(identity, str) or not identity or len(identity) > 128 or identity in seen:
            raise ValueError('Identificador de fila inválido o duplicado.')
        seen.add(identity)

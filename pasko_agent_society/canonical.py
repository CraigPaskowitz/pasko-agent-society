"""Canonical serialization and hashing for deterministic experiment identity."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from enum import Enum
from typing import Any


def to_primitive(value: Any) -> Any:
    """Convert supported values to a stable JSON-compatible representation."""

    if dataclasses.is_dataclass(value):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {
            str(key): to_primitive(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [to_primitive(item) for item in value]
    if isinstance(value, set):
        return sorted((to_primitive(item) for item in value), key=repr)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize without platform- or insertion-order-dependent whitespace."""

    return json.dumps(
        to_primitive(value),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_hash(value: Any) -> str:
    """Return a namespaced SHA-256 digest of a canonical representation."""

    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"

"""Stateless, namespaced deterministic draws for matched experiments."""

from __future__ import annotations

import hashlib


def deterministic_u64(seed: int, *namespace: object) -> int:
    material = "\x1f".join([str(seed), *(str(part) for part in namespace)])
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def uniform(seed: int, *namespace: object) -> float:
    """Return a reproducible value in [0, 1), independent of call order."""

    return deterministic_u64(seed, *namespace) / 2**64


def stable_order(values: list[str], seed: int, *namespace: object) -> tuple[str, ...]:
    """Order identifiers reproducibly without consuming mutable RNG state."""

    return tuple(
        sorted(values, key=lambda value: (deterministic_u64(seed, *namespace, value), value))
    )

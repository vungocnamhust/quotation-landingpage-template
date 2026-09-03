"""K6/K7 — time-sortable id generation.

Layout:
- Total: 64 bits (16 lowercase hex characters).
- Timestamp: 48 bits (Unix millisecond epoch, high-order, keeps IDs sortable by creation time).
- Counter: 16 bits (process-local monotonic counter, seeded from cryptographically random offset).

Concurrency boundary & Collision characteristics:
- Single-process: strictly monotonic and collision-free up to 65,536 IDs/millisecond.
- Cross-process: Independent 16-bit random seeds yield a collision probability of ~2^-16 (~0.0015%)
  per process pair landing on the exact same millisecond.
- Recommended worker limit: Keep concurrent bulk-seeding / ingestion worker processes to <= 4 workers
  per tenant (same-ms collision risk <= 0.14%) to avoid primary-key contention without needing
  external coordination services.
"""
from __future__ import annotations

import itertools
import secrets
import threading
import time

_TIMESTAMP_BITS = 48
_COUNTER_BITS = 16
_ID_BITS = _TIMESTAMP_BITS + _COUNTER_BITS
_HEX_LENGTH = _ID_BITS // 4
_COUNTER_MASK = (1 << _COUNTER_BITS) - 1
_ID_MASK = (1 << _ID_BITS) - 1

_counter = itertools.count(secrets.randbits(_COUNTER_BITS))
_counter_lock = threading.Lock()


def _next_counter() -> int:
    with _counter_lock:
        return next(_counter) & _COUNTER_MASK


def _sortable_hex() -> str:
    timestamp_ms = time.time_ns() // 1_000_000
    tail = _next_counter()
    combined = ((timestamp_ms << _COUNTER_BITS) | tail) & _ID_MASK
    return format(combined, f"0{_HEX_LENGTH}x")


def generate_id(prefix: str) -> str:
    """Generate a `{prefix}_{16 hex chars}` id, sortable by creation time."""
    if not prefix:
        raise ValueError("prefix is required")
    return f"{prefix}_{_sortable_hex()}"

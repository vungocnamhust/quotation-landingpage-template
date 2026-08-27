"""K6/K7 — time-sortable id generation.

No external uuid7 dependency is available in this repo, so ids are built from
a millisecond timestamp (high-order bits, keeps ids sortable by creation
time) plus a process-local monotonic counter (low-order bits). The counter —
rather than randomness — guarantees strictly increasing ids for successive
calls even when several land in the same millisecond.
"""
from __future__ import annotations

import itertools
import threading
import time

_TIMESTAMP_BITS = 48
_COUNTER_BITS = 16
_ID_BITS = _TIMESTAMP_BITS + _COUNTER_BITS
_HEX_LENGTH = _ID_BITS // 4
_COUNTER_MASK = (1 << _COUNTER_BITS) - 1
_ID_MASK = (1 << _ID_BITS) - 1

_counter = itertools.count()
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

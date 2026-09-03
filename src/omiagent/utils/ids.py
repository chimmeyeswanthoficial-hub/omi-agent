from __future__ import annotations

import secrets
import time


def new_id() -> str:
    """Sortable-ish short id: base36 ms-timestamp + entropy."""
    ts = int(time.time() * 1000)
    return f"{ts:x}{secrets.token_hex(3)}"

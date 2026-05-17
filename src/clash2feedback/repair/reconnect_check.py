from __future__ import annotations

from typing import Any


def local_reconnect_pass(diagnostics_row: dict[str, Any]) -> bool:
    return bool(diagnostics_row.get("local_reconnect_pass", False))


def reconnect_failure_reason(diagnostics_row: dict[str, Any]) -> str:
    if local_reconnect_pass(diagnostics_row):
        return ""
    return str(diagnostics_row.get("local_reconnect_failure_reason") or "unknown")

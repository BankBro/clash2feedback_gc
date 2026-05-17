from __future__ import annotations

from typing import Any


def anchor_aware_filter_row(diagnostics_row: dict[str, Any]) -> dict[str, Any]:
    candidate_single_fragment = bool(diagnostics_row.get("candidate_single_fragment", False))
    anchor_match_success = bool(diagnostics_row.get("anchor_match_success", False))
    connected_to_anchor = bool(diagnostics_row.get("generated_fragment_connected_to_anchor", False))
    local_reconnect_pass = bool(diagnostics_row.get("local_reconnect_pass", False))
    size_status = str(diagnostics_row.get("generated_size_status") or "unknown")
    pass_filter = (
        candidate_single_fragment
        and anchor_match_success
        and connected_to_anchor
        and local_reconnect_pass
        and size_status == "matched"
    )
    return {
        "candidate_id": diagnostics_row.get("candidate_id", ""),
        "candidate_budget_k": int(diagnostics_row.get("candidate_budget_k") or 0),
        "anchor_aware_filter_pass": pass_filter,
        "anchor_aware_filter_reason": "" if pass_filter else _filter_reason(diagnostics_row),
    }


def _filter_reason(diagnostics_row: dict[str, Any]) -> str:
    if not bool(diagnostics_row.get("candidate_single_fragment", False)):
        return "candidate_not_single_fragment"
    if not bool(diagnostics_row.get("anchor_match_success", False)):
        return "anchor_not_mapped"
    if not bool(diagnostics_row.get("generated_fragment_connected_to_anchor", False)):
        return "generated_fragment_not_connected_to_anchor"
    if not bool(diagnostics_row.get("local_reconnect_pass", False)):
        return str(diagnostics_row.get("local_reconnect_failure_reason") or "local_reconnect_failed")
    if str(diagnostics_row.get("generated_size_status") or "unknown") != "matched":
        return f"generated_size_status={diagnostics_row.get('generated_size_status')}"
    return "unknown"

from __future__ import annotations

from typing import Any

import numpy as np


def mark_duplicate_cases(rows: list[dict[str, Any]], *, coords_rmsd_threshold: float = 0.1) -> list[dict[str, Any]]:
    representatives: list[dict[str, Any]] = []
    for row in rows:
        if row.get("oracle_split") in {"invalid_conformer", "unsupported"}:
            row["duplicate_of"] = ""
            representatives.append(row)
            continue
        duplicate_of = ""
        for previous in representatives:
            if _is_duplicate(row, previous, coords_rmsd_threshold=float(coords_rmsd_threshold)):
                duplicate_of = str(previous.get("case_id", ""))
                break
        row["duplicate_of"] = duplicate_of
        if duplicate_of:
            row["original_oracle_split"] = row.get("oracle_split", "")
            row["oracle_split"] = "duplicate_removed"
            row["acceptance_status"] = "duplicate_removed"
            row["reject_reason"] = row.get("reject_reason") or "duplicate_of_existing_case"
        else:
            representatives.append(row)
    return rows


def coords_rmsd(coords_a: np.ndarray, coords_b: np.ndarray) -> float:
    a = np.asarray(coords_a, dtype=np.float32)
    b = np.asarray(coords_b, dtype=np.float32)
    if a.shape != b.shape:
        return float("inf")
    diff = a - b
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))


def _is_duplicate(row: dict[str, Any], previous: dict[str, Any], *, coords_rmsd_threshold: float) -> bool:
    if row.get("base_sample_id") != previous.get("base_sample_id"):
        return False
    if row.get("target_rgroup") != previous.get("target_rgroup"):
        return False
    if row.get("oracle_split") != previous.get("oracle_split"):
        return False
    if row.get("failure_type") != previous.get("failure_type"):
        return False
    if row.get("top_clash_residue") and previous.get("top_clash_residue") and row.get("top_clash_residue") != previous.get("top_clash_residue"):
        return False
    return coords_rmsd(row.get("_failed_coords"), previous.get("_failed_coords")) <= float(coords_rmsd_threshold)

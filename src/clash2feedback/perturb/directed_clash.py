from __future__ import annotations

from typing import Any

import numpy as np

from clash2feedback.perturb.rotation import rotate_target_rgroup


def directed_rotation_attempts(
    sample: dict[str, Any],
    rgroup: dict[str, Any],
    angles_deg: list[float],
) -> list[dict[str, Any]]:
    """Return anchor-preserving rotations ordered by proximity to protein atoms."""
    attempts: list[dict[str, Any]] = []
    protein_coords = np.asarray(sample.get("protein", {}).get("coords"), dtype=np.float32)
    target_atoms = [int(idx) for idx in rgroup.get("heavy_atom_indices") or rgroup.get("atom_indices", [])]
    for angle in angles_deg:
        result = rotate_target_rgroup(sample, rgroup, float(angle))
        failed = np.asarray(result["failed_coords"], dtype=np.float32)
        min_distance = _min_distance_to_protein(failed[target_atoms], protein_coords)
        result["hotspot_min_distance"] = min_distance
        attempts.append(result)
    return sorted(attempts, key=lambda item: float(item["hotspot_min_distance"]))


def _min_distance_to_protein(ligand_coords: np.ndarray, protein_coords: np.ndarray) -> float:
    if ligand_coords.size == 0 or protein_coords.size == 0:
        return float("inf")
    diff = ligand_coords[:, None, :] - protein_coords[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    return float(np.min(distances))

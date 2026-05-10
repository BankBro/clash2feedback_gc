from __future__ import annotations

from typing import Any

import numpy as np


def rotation_matrix(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    vector = np.asarray(axis, dtype=np.float64)
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12:
        raise ValueError("Rotation axis has near-zero length.")
    unit = vector / norm
    theta = np.deg2rad(float(angle_deg))
    ux, uy, uz = unit.tolist()
    skew = np.asarray(
        [
            [0.0, -uz, uy],
            [uz, 0.0, -ux],
            [-uy, ux, 0.0],
        ],
        dtype=np.float64,
    )
    return (
        np.eye(3, dtype=np.float64) * np.cos(theta)
        + (1.0 - np.cos(theta)) * np.outer(unit, unit)
        + np.sin(theta) * skew
    )


def rotate_atoms_around_axis(
    coords: np.ndarray,
    *,
    axis_start_atom_idx: int,
    axis_end_atom_idx: int,
    atom_indices: list[int] | np.ndarray,
    angle_deg: float,
) -> tuple[np.ndarray, np.ndarray]:
    original = np.asarray(coords, dtype=np.float32)
    if original.ndim != 2 or original.shape[1] != 3:
        raise ValueError("coords must have shape (num_atoms, 3).")
    start_idx = int(axis_start_atom_idx)
    end_idx = int(axis_end_atom_idx)
    if not (0 <= start_idx < original.shape[0] and 0 <= end_idx < original.shape[0]):
        raise ValueError("Rotation axis atom index is out of bounds.")

    moved = np.asarray(sorted({int(idx) for idx in atom_indices}), dtype=np.int64)
    if moved.size == 0:
        raise ValueError("atom_indices must not be empty.")
    if (moved < 0).any() or (moved >= original.shape[0]).any():
        raise ValueError("Moved atom index is out of bounds.")

    anchor = original[start_idx].astype(np.float64)
    axis = original[end_idx].astype(np.float64) - anchor
    matrix = rotation_matrix(axis, angle_deg)
    failed = original.astype(np.float64, copy=True)
    failed[moved] = (failed[moved] - anchor) @ matrix.T + anchor
    return failed.astype(np.float32), matrix.astype(np.float32)


def rotate_target_rgroup(
    sample: dict[str, Any],
    rgroup: dict[str, Any],
    angle_deg: float,
    *,
    atom_indices: list[int] | None = None,
) -> dict[str, Any]:
    coords = np.asarray(sample.get("ligand", {}).get("coords"), dtype=np.float32)
    scaffold_anchor = rgroup.get("anchor_scaffold_atom_idx")
    rgroup_anchor = rgroup.get("anchor_rgroup_atom_idx")
    if scaffold_anchor is None or rgroup_anchor is None:
        raise ValueError(f"R-group {rgroup.get('rgroup_id', '')} has no single anchor.")
    moved_atoms = list(atom_indices if atom_indices is not None else rgroup.get("atom_indices", []))
    failed_coords, matrix = rotate_atoms_around_axis(
        coords,
        axis_start_atom_idx=int(scaffold_anchor),
        axis_end_atom_idx=int(rgroup_anchor),
        atom_indices=moved_atoms,
        angle_deg=float(angle_deg),
    )
    transform = np.eye(4, dtype=np.float32)
    transform[:3, :3] = matrix
    return {
        "failed_coords": failed_coords,
        "rotation_matrix": matrix,
        "transform_matrix": transform,
        "rotation_axis_atom_pair": [int(scaffold_anchor), int(rgroup_anchor)],
        "moved_atom_indices": sorted(int(idx) for idx in moved_atoms),
        "angle_deg": float(angle_deg),
    }

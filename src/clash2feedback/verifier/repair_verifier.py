from __future__ import annotations

from typing import Any

import numpy as np

from clash2feedback.geometry.clash import detect_clashes
from clash2feedback.geometry.rgroup_attribution import ligand_atom_regions


def verify_repair(
    sample: dict[str, Any],
    failed_ligand_coords: np.ndarray,
    repaired_ligand_coords: np.ndarray,
    edit_region: str | list[str] | None = None,
    config: dict[str, Any] | None = None,
    old_clash_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or {}
    detector_cfg = cfg.get("detector", {}) if "detector" in cfg else {}
    verifier_cfg = cfg.get("verifier", cfg)
    old_scope = str(detector_cfg.get("default_old_scope", "phase0_pocket8"))
    new_scope = str(detector_cfg.get("default_new_scope", "pocket10_all_atoms"))
    delta = float(detector_cfg.get("delta_angstrom", 0.4))
    severe_threshold = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    resolved_ratio = float(verifier_cfg.get("old_clash_resolved_ratio", 0.1))
    scaffold_threshold = float(verifier_cfg.get("scaffold_rmsd_threshold", 0.5))
    non_edit_threshold = float(verifier_cfg.get("non_edit_rmsd_threshold", 0.8))
    outside_fraction_threshold = float(verifier_cfg.get("edit_region_outside_change_fraction", 0.2))

    failed_coords = np.asarray(failed_ligand_coords, dtype=np.float32)
    repaired_coords = np.asarray(repaired_ligand_coords, dtype=np.float32)
    geometry_valid = _geometry_valid(sample, failed_coords, repaired_coords)

    if old_clash_report is None:
        old_clash_report = detect_clashes(
            sample,
            ligand_coords=failed_coords,
            receptor_scope=old_scope,
            delta_angstrom=delta,
            severe_depth_threshold_angstrom=severe_threshold,
        )
    old_after_report = detect_clashes(
        sample,
        ligand_coords=repaired_coords,
        receptor_scope=old_scope,
        delta_angstrom=delta,
        severe_depth_threshold_angstrom=severe_threshold,
    )
    new_report = detect_clashes(
        sample,
        ligand_coords=repaired_coords,
        receptor_scope=new_scope,
        delta_angstrom=delta,
        severe_depth_threshold_angstrom=severe_threshold,
    )

    old_before = float(old_clash_report.get("total_clash_score") or 0.0)
    old_after = float(old_after_report.get("total_clash_score") or 0.0)
    old_before_severe = int(old_clash_report.get("num_severe_clash_pairs") or 0)
    old_after_severe = int(old_after_report.get("num_severe_clash_pairs") or 0)
    if old_before_severe == 0 and old_after_severe == 0:
        old_clash_resolved = True
    else:
        old_clash_resolved = old_after <= max(old_before * resolved_ratio, 1e-12)
    new_severe_count = int(new_report.get("num_severe_clash_pairs") or 0)
    no_new_severe_clash = new_severe_count == 0

    scaffold_mask = _scaffold_mask(sample)
    scaffold_rmsd = _masked_rmsd(failed_coords, repaired_coords, scaffold_mask)
    scaffold_stable = _passes_rmsd(scaffold_rmsd, scaffold_threshold)

    edit_mask = _edit_region_mask(sample, edit_region)
    non_edit_mask = _heavy_atom_mask(sample) & ~edit_mask
    non_edit_rmsd = _masked_rmsd(failed_coords, repaired_coords, non_edit_mask)
    non_edit_stable = _passes_rmsd(non_edit_rmsd, non_edit_threshold)
    edit_compliance = _edit_compliance(
        failed_coords,
        repaired_coords,
        non_edit_mask,
        outside_fraction_threshold=outside_fraction_threshold,
    )
    pocket_retention = _pocket_retention(sample, repaired_coords, verifier_cfg)

    unsupported_reasons = sorted(
        set(
            list(old_clash_report.get("unsupported_reasons", []))
            + list(old_after_report.get("unsupported_reasons", []))
            + list(new_report.get("unsupported_reasons", []))
        )
    )
    failure_reasons: list[str] = []
    if unsupported_reasons:
        failure_reasons.append("unsupported_case")
    if not old_clash_resolved:
        failure_reasons.append("old_clash_not_resolved")
    if not no_new_severe_clash:
        failure_reasons.append("new_severe_clash")
    if not scaffold_stable:
        failure_reasons.append("scaffold_drift")
    if not non_edit_stable:
        failure_reasons.append("non_edit_drift")
    if not geometry_valid:
        failure_reasons.append("geometry_invalid")
    if not edit_compliance:
        failure_reasons.append("edit_noncompliance")
    if not pocket_retention:
        failure_reasons.append("pocket_not_retained")

    repair_pass = not failure_reasons
    return {
        "sample_id": sample.get("sample_id", ""),
        "old_clash_score_before": old_before,
        "old_clash_score_after": old_after,
        "old_clash_resolved": bool(old_clash_resolved),
        "new_severe_clash_count": new_severe_count,
        "no_new_severe_clash": bool(no_new_severe_clash),
        "scaffold_rmsd": float(scaffold_rmsd),
        "scaffold_stable": bool(scaffold_stable),
        "non_edit_rmsd": float(non_edit_rmsd),
        "non_edit_stable": bool(non_edit_stable),
        "geometry_valid": bool(geometry_valid),
        "edit_compliance": bool(edit_compliance),
        "pocket_retention": bool(pocket_retention),
        "repair_pass": bool(repair_pass),
        "failure_reasons": failure_reasons,
        "unsupported_reasons": unsupported_reasons,
        "receptor_scope_old": old_scope,
        "receptor_scope_new": new_scope,
    }


def _geometry_valid(sample: dict[str, Any], failed_coords: np.ndarray, repaired_coords: np.ndarray) -> bool:
    expected_shape = np.asarray(sample.get("ligand", {}).get("coords"), dtype=np.float32).shape
    return (
        failed_coords.shape == expected_shape
        and repaired_coords.shape == expected_shape
        and failed_coords.shape == repaired_coords.shape
        and failed_coords.ndim == 2
        and failed_coords.shape[1] == 3
        and bool(np.isfinite(failed_coords).all())
        and bool(np.isfinite(repaired_coords).all())
    )


def _scaffold_mask(sample: dict[str, Any]) -> np.ndarray:
    ligand = sample.get("ligand", {})
    num_atoms = int(ligand.get("num_atoms") or np.asarray(ligand.get("coords")).shape[0])
    mask = np.zeros(num_atoms, dtype=bool)
    for atom_idx in sample.get("scaffold", {}).get("atom_indices", []):
        if 0 <= int(atom_idx) < num_atoms:
            mask[int(atom_idx)] = True
    if not mask.any():
        mask = np.asarray(sample.get("masks", {}).get("ligand_scaffold_mask", mask), dtype=bool)
    return mask


def _heavy_atom_mask(sample: dict[str, Any]) -> np.ndarray:
    ligand = sample.get("ligand", {})
    num_atoms = int(ligand.get("num_atoms") or np.asarray(ligand.get("coords")).shape[0])
    if "heavy_atom_mask" in sample.get("masks", {}):
        mask = np.asarray(sample["masks"]["heavy_atom_mask"], dtype=bool)
        if mask.shape[0] == num_atoms:
            return mask
    atomic_numbers = list(ligand.get("atomic_numbers", []))
    return np.asarray([int(atomic_numbers[idx]) > 1 if idx < len(atomic_numbers) else True for idx in range(num_atoms)])


def _edit_region_mask(sample: dict[str, Any], edit_region: str | list[str] | None) -> np.ndarray:
    ligand = sample.get("ligand", {})
    num_atoms = int(ligand.get("num_atoms") or np.asarray(ligand.get("coords")).shape[0])
    mask = np.zeros(num_atoms, dtype=bool)
    if edit_region is None:
        return mask
    wanted = {edit_region} if isinstance(edit_region, str) else set(edit_region)
    regions = ligand_atom_regions(sample)
    for atom_idx, region in enumerate(regions):
        if region in wanted:
            mask[atom_idx] = True
    return mask


def _masked_rmsd(failed_coords: np.ndarray, repaired_coords: np.ndarray, mask: np.ndarray) -> float:
    if mask.shape[0] != failed_coords.shape[0] or not bool(mask.any()):
        return float("nan")
    diff = failed_coords[mask] - repaired_coords[mask]
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))


def _passes_rmsd(value: float, threshold: float) -> bool:
    return bool(np.isnan(value) or value < float(threshold))


def _edit_compliance(
    failed_coords: np.ndarray,
    repaired_coords: np.ndarray,
    non_edit_mask: np.ndarray,
    *,
    outside_fraction_threshold: float,
) -> bool:
    if non_edit_mask.shape[0] != failed_coords.shape[0] or not bool(non_edit_mask.any()):
        return True
    displacement = np.sqrt(np.sum((failed_coords[non_edit_mask] - repaired_coords[non_edit_mask]) ** 2, axis=1))
    changed_fraction = float(np.mean(displacement > 0.1))
    return changed_fraction <= float(outside_fraction_threshold)


def _pocket_retention(sample: dict[str, Any], repaired_coords: np.ndarray, verifier_cfg: dict[str, Any]) -> bool:
    min_contacts = verifier_cfg.get("pocket_retention_min_contacts")
    if min_contacts is None:
        return bool(np.isfinite(repaired_coords).all())
    protein_coords = np.asarray(sample.get("protein", {}).get("coords"), dtype=np.float32)
    if protein_coords.ndim != 2 or protein_coords.shape[1] != 3 or protein_coords.size == 0:
        return False
    heavy_mask = _heavy_atom_mask(sample)
    ligand_coords = repaired_coords[heavy_mask]
    if ligand_coords.size == 0:
        return False
    diff = ligand_coords[:, None, :] - protein_coords[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    return int(np.sum(distances <= 8.0)) >= int(min_contacts)

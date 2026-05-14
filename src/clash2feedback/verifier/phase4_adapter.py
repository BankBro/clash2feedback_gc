from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from clash2feedback.repair.phase4_inputs import Phase4CaseInput, read_first_mol
from clash2feedback.verifier.repair_verifier import verify_repair


RELIABLE_REPAIR_FIELDS = [
    "candidate_readable",
    "ligand_valid",
    "fixed_structure_match_success",
    "old_clash_resolved",
    "no_new_severe_clash",
    "scaffold_stable",
    "keep_region_stable",
    "anchor_integrity",
    "edit_compliance",
    "pocket_retention",
]


def evaluate_candidate_for_phase4(
    candidate_row: dict[str, Any],
    case_input: Phase4CaseInput,
    *,
    verifier_config: dict[str, Any],
    phase4_verifier_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    phase4_cfg = phase4_verifier_cfg or {}
    base = _base_outcome(candidate_row, case_input)
    candidate_path = str(candidate_row.get("candidate_path") or "")
    if not candidate_path:
        base["failure_stage"] = candidate_row.get("failure_stage") or "candidate_missing"
        base["failure_reason"] = candidate_row.get("failure_reason") or "candidate_path_empty"
        return _finalize(base)

    try:
        mol = read_first_mol(candidate_path, sanitize=False)
        coords = np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32)
        base["candidate_readable"] = True
        base["candidate_atom_count"] = int(mol.GetNumAtoms())
        base["ligand_valid"] = _ligand_valid(mol)
    except Exception as exc:
        base["failure_stage"] = "candidate_read"
        base["failure_reason"] = f"{type(exc).__name__}:{exc}"
        return _finalize(base)

    try:
        same_topology = _as_bool(candidate_row.get("same_topology"))
        if same_topology:
            repaired_coords = coords
            base["fixed_structure_match_success"] = _same_topology_match(case_input, mol)
            base["anchor_integrity"] = _same_topology_anchor_integrity(case_input, mol)
            base["keep_region_rmsd"] = _rmsd(case_input.failed_ligand_coords, repaired_coords, case_input.keep_atom_indices)
            base["keep_region_stable"] = bool(base["keep_region_rmsd"] <= float(phase4_cfg.get("keep_region_rmsd_threshold", 0.8)))
            base["topology_mappable_to_original_atom_order"] = True
        else:
            mapped = _map_variable_topology_candidate(case_input, mol, coords, phase4_cfg)
            base.update(mapped["metrics"])
            if not mapped["success"]:
                base["failure_stage"] = "adapter"
                base["failure_reason"] = mapped["failure_reason"]
                return _finalize(base)
            repaired_coords = mapped["repaired_coords"]

        verify = verify_repair(
            case_input.failed_sample,
            case_input.failed_ligand_coords,
            repaired_coords,
            edit_region=case_input.target_rgroup,
            config=verifier_config,
            old_clash_report=case_input.phase2_sample.get("clash_report"),
        )
        base.update(
            {
                "old_clash_score_before": verify.get("old_clash_score_before", 0.0),
                "old_clash_score_after": verify.get("old_clash_score_after", 0.0),
                "old_clash_resolved": bool(verify.get("old_clash_resolved", False)),
                "no_new_severe_clash": bool(verify.get("no_new_severe_clash", False)),
                "new_severe_clash_count": int(verify.get("new_severe_clash_count", 0)),
                "scaffold_rmsd": float(verify.get("scaffold_rmsd", np.nan)),
                "scaffold_stable": bool(verify.get("scaffold_stable", False)),
                "non_edit_rmsd": float(verify.get("non_edit_rmsd", np.nan)),
                "non_edit_stable": bool(verify.get("non_edit_stable", False)),
                "coordinate_valid": bool(verify.get("coordinate_valid", False)),
                "geometry_valid": bool(verify.get("geometry_valid", False)),
                "edit_compliance": bool(verify.get("edit_compliance", False)),
                "pocket_retention": bool(verify.get("pocket_retention", False)),
                "repair_pass": bool(verify.get("repair_pass", False)),
                "verifier_failure_reasons": verify.get("failure_reasons", []),
                "old_pair_remaining_count": int(verify.get("old_pair_remaining_count", 0)),
                "old_severe_pair_remaining_count": int(verify.get("old_severe_pair_remaining_count", 0)),
                "new_severe_pair_created_count": int(verify.get("new_severe_pair_created_count", 0)),
                "receptor_scope_old": str(verify.get("receptor_scope_old", "")),
                "receptor_scope_new": str(verify.get("receptor_scope_new", "")),
                "old_report_scope_input": str(case_input.phase2_sample.get("clash_report", {}).get("receptor_scope", "")),
            }
        )
        if not bool(base["repair_pass"]) and not base["failure_reason"]:
            base["failure_stage"] = "verifier"
            base["failure_reason"] = ";".join(str(item) for item in verify.get("failure_reasons", []))
    except Exception as exc:
        base["failure_stage"] = "verifier_adapter"
        base["failure_reason"] = f"{type(exc).__name__}:{exc}"
    return _finalize(base)


def _base_outcome(candidate_row: dict[str, Any], case_input: Phase4CaseInput) -> dict[str, Any]:
    return {
        "backend_name": candidate_row.get("backend_name", ""),
        "backend_unit": candidate_row.get("backend_unit", ""),
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "attempt_id": candidate_row.get("attempt_id", ""),
        "candidate_id": candidate_row.get("candidate_id", ""),
        "candidate_index": int(candidate_row.get("candidate_index") or 0),
        "candidate_path": candidate_row.get("candidate_path", ""),
        "candidate_readable": False,
        "ligand_valid": False,
        "fixed_structure_match_success": False,
        "topology_mappable_to_original_atom_order": False,
        "anchor_integrity": False,
        "keep_region_rmsd": float("nan"),
        "keep_region_stable": False,
        "old_clash_score_before": float("nan"),
        "old_clash_score_after": float("nan"),
        "old_clash_resolved": False,
        "no_new_severe_clash": False,
        "new_severe_clash_count": -1,
        "scaffold_rmsd": float("nan"),
        "scaffold_stable": False,
        "non_edit_rmsd": float("nan"),
        "non_edit_stable": False,
        "coordinate_valid": False,
        "geometry_valid": False,
        "edit_compliance": False,
        "pocket_retention": False,
        "repair_pass": False,
        "reliable_repair_success": False,
        "reliable_repair_criteria_json": "",
        "failure_stage": candidate_row.get("failure_stage", ""),
        "failure_reason": candidate_row.get("failure_reason", ""),
        "verifier_failure_reasons": [],
        "old_pair_remaining_count": -1,
        "old_severe_pair_remaining_count": -1,
        "new_severe_pair_created_count": -1,
        "receptor_scope_old": "",
        "receptor_scope_new": "",
        "old_report_scope_input": str(case_input.phase2_sample.get("clash_report", {}).get("receptor_scope", "")),
    }


def _finalize(row: dict[str, Any]) -> dict[str, Any]:
    criteria = {field: bool(row.get(field, False)) for field in RELIABLE_REPAIR_FIELDS}
    row["reliable_repair_criteria_json"] = json.dumps(criteria, ensure_ascii=False, sort_keys=True)
    row["reliable_repair_success"] = all(criteria.values())
    if not row["reliable_repair_success"] and not row.get("failure_stage"):
        row["failure_stage"] = "reliable_criteria"
        failed = [key for key, value in criteria.items() if not value]
        row["failure_reason"] = ";".join(failed)
    if isinstance(row.get("verifier_failure_reasons"), list):
        row["verifier_failure_reasons"] = ";".join(str(item) for item in row["verifier_failure_reasons"])
    return row


def _same_topology_match(case_input: Phase4CaseInput, mol: Any) -> bool:
    return int(mol.GetNumAtoms()) == int(case_input.failed_ligand_coords.shape[0])


def _same_topology_anchor_integrity(case_input: Phase4CaseInput, mol: Any) -> bool:
    if not _same_topology_match(case_input, mol):
        return False
    bond = mol.GetBondBetweenAtoms(case_input.anchor_scaffold_atom_idx, case_input.anchor_rgroup_atom_idx)
    return bond is not None and int(bond.GetIdx()) == int(case_input.anchor_bond_idx)


def _map_variable_topology_candidate(
    case_input: Phase4CaseInput,
    mol: Any,
    coords: np.ndarray,
    phase4_cfg: dict[str, Any],
) -> dict[str, Any]:
    tolerance = float(phase4_cfg.get("fixed_structure_match_tolerance_angstrom", 0.35))
    failed_mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
    mapping = _coordinate_match_keep_atoms(case_input, failed_mol, mol, coords, tolerance=tolerance)
    metrics = {
        "fixed_structure_match_success": bool(mapping["success"]),
        "keep_region_rmsd": float(mapping["rmsd"]),
        "keep_region_stable": bool(mapping["success"] and mapping["rmsd"] <= float(phase4_cfg.get("keep_region_rmsd_threshold", 0.8))),
        "anchor_integrity": False,
        "topology_mappable_to_original_atom_order": False,
    }
    if not mapping["success"]:
        return {"success": False, "failure_reason": mapping["failure_reason"], "metrics": metrics}
    anchor_candidate = mapping["old_to_candidate"].get(case_input.anchor_scaffold_atom_idx)
    generated_atoms = set(range(mol.GetNumAtoms())) - set(mapping["old_to_candidate"].values())
    metrics["anchor_integrity"] = _generated_fragment_connected_to_anchor(mol, anchor_candidate, generated_atoms)
    repaired_coords_result = _adapt_candidate_coords_to_original_order(case_input, failed_mol, mol, coords, mapping["old_to_candidate"], generated_atoms)
    metrics["topology_mappable_to_original_atom_order"] = bool(repaired_coords_result["success"])
    if not repaired_coords_result["success"]:
        return {"success": False, "failure_reason": repaired_coords_result["failure_reason"], "metrics": metrics}
    return {
        "success": True,
        "failure_reason": "",
        "metrics": metrics,
        "repaired_coords": repaired_coords_result["repaired_coords"],
    }


def _coordinate_match_keep_atoms(
    case_input: Phase4CaseInput,
    failed_mol: Any,
    candidate_mol: Any,
    candidate_coords: np.ndarray,
    *,
    tolerance: float,
) -> dict[str, Any]:
    old_coords = np.asarray(case_input.failed_ligand_coords, dtype=np.float32)
    used: set[int] = set()
    old_to_candidate: dict[int, int] = {}
    distances: list[float] = []
    for old_idx in case_input.keep_atom_indices:
        old_atom = failed_mol.GetAtomWithIdx(int(old_idx))
        candidates = []
        for cand_idx in range(candidate_mol.GetNumAtoms()):
            if cand_idx in used:
                continue
            cand_atom = candidate_mol.GetAtomWithIdx(cand_idx)
            if cand_atom.GetAtomicNum() != old_atom.GetAtomicNum():
                continue
            dist = float(np.linalg.norm(old_coords[int(old_idx)] - candidate_coords[cand_idx]))
            candidates.append((dist, cand_idx))
        if not candidates:
            return {"success": False, "failure_reason": f"keep_atom_no_element_match:{old_idx}", "old_to_candidate": old_to_candidate, "rmsd": float("nan")}
        dist, cand_idx = min(candidates, key=lambda item: item[0])
        if dist > tolerance:
            return {
                "success": False,
                "failure_reason": f"keep_atom_coordinate_mismatch:{old_idx}:distance={dist:.3f}",
                "old_to_candidate": old_to_candidate,
                "rmsd": float("nan"),
            }
        used.add(cand_idx)
        old_to_candidate[int(old_idx)] = int(cand_idx)
        distances.append(dist * dist)
    rmsd = float(np.sqrt(np.mean(distances))) if distances else 0.0
    return {"success": True, "failure_reason": "", "old_to_candidate": old_to_candidate, "rmsd": rmsd}


def _generated_fragment_connected_to_anchor(mol: Any, anchor_candidate_idx: int | None, generated_atoms: set[int]) -> bool:
    if anchor_candidate_idx is None or not generated_atoms:
        return False
    atom = mol.GetAtomWithIdx(int(anchor_candidate_idx))
    return any(int(neighbor.GetIdx()) in generated_atoms for neighbor in atom.GetNeighbors())


def _adapt_candidate_coords_to_original_order(
    case_input: Phase4CaseInput,
    failed_mol: Any,
    candidate_mol: Any,
    candidate_coords: np.ndarray,
    old_to_candidate: dict[int, int],
    generated_atoms: set[int],
) -> dict[str, Any]:
    if len(generated_atoms) != len(case_input.mask_atom_indices):
        return {
            "success": False,
            "failure_reason": f"generated_atom_count_mismatch:{len(generated_atoms)}!={len(case_input.mask_atom_indices)}",
        }
    remaining_by_atomic_number: dict[int, list[int]] = {}
    for cand_idx in sorted(generated_atoms):
        atomic_number = int(candidate_mol.GetAtomWithIdx(cand_idx).GetAtomicNum())
        remaining_by_atomic_number.setdefault(atomic_number, []).append(cand_idx)
    repaired = np.asarray(case_input.failed_ligand_coords, dtype=np.float32).copy()
    for old_idx in case_input.keep_atom_indices:
        repaired[int(old_idx)] = candidate_coords[old_to_candidate[int(old_idx)]]
    for old_idx in case_input.mask_atom_indices:
        atomic_number = int(failed_mol.GetAtomWithIdx(int(old_idx)).GetAtomicNum())
        candidates = remaining_by_atomic_number.get(atomic_number) or []
        if not candidates:
            return {"success": False, "failure_reason": f"generated_atom_element_mismatch:old_atom={old_idx}:Z={atomic_number}"}
        cand_idx = candidates.pop(0)
        repaired[int(old_idx)] = candidate_coords[cand_idx]
    return {"success": True, "failure_reason": "", "repaired_coords": repaired}


def _ligand_valid(mol: Any) -> bool:
    from rdkit import Chem

    try:
        copy = Chem.Mol(mol)
        result = Chem.SanitizeMol(copy, catchErrors=True)
        return result == Chem.SanitizeFlags.SANITIZE_NONE
    except Exception:
        return False


def _rmsd(coords_a: np.ndarray, coords_b: np.ndarray, atom_indices: list[int]) -> float:
    if not atom_indices:
        return float("nan")
    idx = np.asarray(atom_indices, dtype=np.int64)
    diff = coords_a[idx] - coords_b[idx]
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

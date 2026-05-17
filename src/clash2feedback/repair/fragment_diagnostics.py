from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from clash2feedback.repair.phase4_inputs import Phase4CaseInput, read_first_mol


@dataclass(frozen=True)
class CandidateMapping:
    success: bool
    failure_reason: str
    old_to_candidate: dict[int, int]
    generated_atoms: set[int]
    rmsd: float


def analyze_candidate_fragment(
    candidate_row: dict[str, Any],
    case_input: Phase4CaseInput,
    *,
    tolerance: float = 0.35,
) -> dict[str, Any]:
    row = _empty_row(candidate_row, case_input)
    candidate_path = str(candidate_row.get("candidate_path") or "")
    if not candidate_path or not Path(candidate_path).exists():
        row["fragment_diagnostics_status"] = "candidate_missing"
        row["fragment_diagnostics_reason"] = candidate_row.get("failure_reason") or "candidate_path_empty"
        return row

    try:
        failed_mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
        candidate_mol = read_first_mol(candidate_path, sanitize=False)
        coords = np.asarray(candidate_mol.GetConformer().GetPositions(), dtype=np.float32)
    except Exception as exc:
        row["fragment_diagnostics_status"] = "read_failed"
        row["fragment_diagnostics_reason"] = f"{type(exc).__name__}:{exc}"
        return row

    row["candidate_total_fragment_count"] = int(_mol_fragment_count(candidate_mol))
    row["candidate_single_fragment"] = row["candidate_total_fragment_count"] == 1
    row["candidate_extra_fragment_count"] = max(int(row["candidate_total_fragment_count"]) - 1, 0)

    mapping = map_keep_atoms(case_input, failed_mol, candidate_mol, coords, tolerance=tolerance)
    row["fixed_structure_mapping_success_for_diagnostics"] = mapping.success
    row["fixed_structure_mapping_reason"] = mapping.failure_reason
    row["fixed_structure_mapping_rmsd"] = mapping.rmsd
    row["generated_atom_indices_json"] = json.dumps(sorted(mapping.generated_atoms), ensure_ascii=False)
    row["generated_fragment_heavy_atom_count"] = len(mapping.generated_atoms)
    row["target_mask_heavy_atom_count"] = len(case_input.mask_atom_indices)
    row["generated_fragment_size_diff"] = len(mapping.generated_atoms) - len(case_input.mask_atom_indices)
    row["generated_size_status"] = _size_status(len(mapping.generated_atoms), len(case_input.mask_atom_indices))

    target_elements = [_atom_symbol(failed_mol, atom_idx) for atom_idx in case_input.mask_atom_indices]
    generated_elements = [_atom_symbol(candidate_mol, atom_idx) for atom_idx in sorted(mapping.generated_atoms)]
    row["target_mask_elements"] = json.dumps(target_elements, ensure_ascii=False)
    row["generated_fragment_elements"] = json.dumps(generated_elements, ensure_ascii=False)
    row["generated_element_mismatch_count"] = _multiset_mismatch_count(target_elements, generated_elements)

    if not mapping.success:
        row["fragment_diagnostics_status"] = "mapping_failed"
        row["fragment_diagnostics_reason"] = mapping.failure_reason
        return row

    row["fragment_diagnostics_status"] = "ok"
    row["fragment_diagnostics_reason"] = ""
    row.update(_graph_diagnostics(case_input, candidate_mol, coords, mapping))
    return row


def map_keep_atoms(
    case_input: Phase4CaseInput,
    failed_mol: Any,
    candidate_mol: Any,
    candidate_coords: np.ndarray,
    *,
    tolerance: float,
) -> CandidateMapping:
    old_coords = np.asarray(case_input.failed_ligand_coords, dtype=np.float32)
    used: set[int] = set()
    old_to_candidate: dict[int, int] = {}
    distances: list[float] = []
    for old_idx in case_input.keep_atom_indices:
        old_atom = failed_mol.GetAtomWithIdx(int(old_idx))
        candidates: list[tuple[float, int]] = []
        for cand_idx in range(candidate_mol.GetNumAtoms()):
            if cand_idx in used:
                continue
            cand_atom = candidate_mol.GetAtomWithIdx(cand_idx)
            if cand_atom.GetAtomicNum() != old_atom.GetAtomicNum():
                continue
            dist = float(np.linalg.norm(old_coords[int(old_idx)] - candidate_coords[cand_idx]))
            candidates.append((dist, cand_idx))
        if not candidates:
            return CandidateMapping(False, f"keep_atom_no_element_match:{old_idx}", old_to_candidate, set(), float("nan"))
        dist, cand_idx = min(candidates, key=lambda item: item[0])
        if dist > tolerance:
            return CandidateMapping(
                False,
                f"keep_atom_coordinate_mismatch:{old_idx}:distance={dist:.3f}",
                old_to_candidate,
                set(),
                float("nan"),
            )
        used.add(cand_idx)
        old_to_candidate[int(old_idx)] = int(cand_idx)
        distances.append(dist * dist)

    generated_atoms = set(range(candidate_mol.GetNumAtoms())) - set(old_to_candidate.values())
    rmsd = float(np.sqrt(np.mean(distances))) if distances else 0.0
    return CandidateMapping(True, "", old_to_candidate, generated_atoms, rmsd)


def _graph_diagnostics(
    case_input: Phase4CaseInput,
    mol: Any,
    coords: np.ndarray,
    mapping: CandidateMapping,
) -> dict[str, Any]:
    anchor_candidate_idx = mapping.old_to_candidate.get(int(case_input.anchor_scaffold_atom_idx))
    generated_atoms = set(mapping.generated_atoms)
    keep_candidate_atoms = set(mapping.old_to_candidate.values())
    generated_components = _generated_component_count(mol, generated_atoms)
    attachment_keep_atoms: set[int] = set()
    anchor_neighbors: set[int] = set()
    for gen_idx in generated_atoms:
        atom = mol.GetAtomWithIdx(int(gen_idx))
        for neighbor in atom.GetNeighbors():
            n_idx = int(neighbor.GetIdx())
            if n_idx in keep_candidate_atoms:
                attachment_keep_atoms.add(n_idx)
                if anchor_candidate_idx is not None and n_idx == int(anchor_candidate_idx):
                    anchor_neighbors.add(int(gen_idx))
    floating = _floating_fragment_detected(mol, generated_atoms, keep_candidate_atoms)
    anchor_distance = _anchor_bond_like_distance(coords, anchor_candidate_idx, generated_atoms)
    num_extra_attachments = max(len(attachment_keep_atoms) - 1, 0)
    connected_to_anchor = bool(anchor_neighbors)
    local_pass = (
        anchor_candidate_idx is not None
        and len(generated_atoms) > 0
        and connected_to_anchor
        and len(anchor_neighbors) == 1
        and num_extra_attachments == 0
        and not floating
    )
    reason = _reconnect_reason(
        anchor_candidate_idx=anchor_candidate_idx,
        generated_atoms=generated_atoms,
        connected_to_anchor=connected_to_anchor,
        anchor_neighbor_count=len(anchor_neighbors),
        num_extra_attachments=num_extra_attachments,
        floating=floating,
    )
    return {
        "anchor_candidate_idx": -1 if anchor_candidate_idx is None else int(anchor_candidate_idx),
        "anchor_match_success": anchor_candidate_idx is not None,
        "generated_fragment_connected_to_anchor": connected_to_anchor,
        "generated_fragment_attachment_count": len(attachment_keep_atoms),
        "anchor_bond_like_distance": anchor_distance,
        "anchor_reconnect_status": "pass" if local_pass else "fail",
        "anchor_reconnect_reason": "" if local_pass else reason,
        "local_reconnect_pass": local_pass,
        "local_reconnect_failure_reason": "" if local_pass else reason,
        "num_generated_components": generated_components,
        "num_anchor_neighbors": len(anchor_neighbors),
        "num_extra_attachments": num_extra_attachments,
        "floating_fragment_detected": floating,
    }


def _empty_row(candidate_row: dict[str, Any], case_input: Phase4CaseInput) -> dict[str, Any]:
    return {
        "backend_name": candidate_row.get("backend_name", ""),
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "attempt_id": candidate_row.get("attempt_id", ""),
        "candidate_id": candidate_row.get("candidate_id", ""),
        "candidate_index": int(candidate_row.get("candidate_index") or 0),
        "candidate_path": candidate_row.get("candidate_path", ""),
        "candidate_budget_k": int(candidate_row.get("candidate_budget_k") or 0),
        "fragment_diagnostics_status": "",
        "fragment_diagnostics_reason": "",
        "fixed_structure_mapping_success_for_diagnostics": False,
        "fixed_structure_mapping_reason": "",
        "fixed_structure_mapping_rmsd": float("nan"),
        "target_mask_heavy_atom_count": len(case_input.mask_atom_indices),
        "generated_fragment_heavy_atom_count": 0,
        "generated_fragment_size_diff": -len(case_input.mask_atom_indices),
        "generated_atom_indices_json": "[]",
        "target_mask_elements": "[]",
        "generated_fragment_elements": "[]",
        "generated_element_mismatch_count": len(case_input.mask_atom_indices),
        "generated_size_status": "unknown",
        "candidate_total_fragment_count": 0,
        "candidate_single_fragment": False,
        "candidate_extra_fragment_count": 0,
        "anchor_candidate_idx": -1,
        "anchor_match_success": False,
        "generated_fragment_connected_to_anchor": False,
        "generated_fragment_attachment_count": 0,
        "anchor_bond_like_distance": float("nan"),
        "anchor_reconnect_status": "fail",
        "anchor_reconnect_reason": "not_evaluated",
        "local_reconnect_pass": False,
        "local_reconnect_failure_reason": "not_evaluated",
        "num_generated_components": 0,
        "num_anchor_neighbors": 0,
        "num_extra_attachments": 0,
        "floating_fragment_detected": False,
    }


def _mol_fragment_count(mol: Any) -> int:
    from rdkit import Chem

    return len(Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False))


def _generated_component_count(mol: Any, generated_atoms: set[int]) -> int:
    from rdkit import Chem

    if not generated_atoms:
        return 0
    count = 0
    for fragment in Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False):
        if generated_atoms & set(int(idx) for idx in fragment):
            count += 1
    return count


def _floating_fragment_detected(mol: Any, generated_atoms: set[int], keep_candidate_atoms: set[int]) -> bool:
    from rdkit import Chem

    if not generated_atoms:
        return False
    for fragment in Chem.GetMolFrags(mol, asMols=False, sanitizeFrags=False):
        fragment_atoms = set(int(idx) for idx in fragment)
        if fragment_atoms & generated_atoms and not fragment_atoms & keep_candidate_atoms:
            return True
    return False


def _anchor_bond_like_distance(coords: np.ndarray, anchor_candidate_idx: int | None, generated_atoms: set[int]) -> float:
    if anchor_candidate_idx is None or not generated_atoms:
        return float("nan")
    anchor = coords[int(anchor_candidate_idx)]
    return float(min(np.linalg.norm(anchor - coords[int(idx)]) for idx in generated_atoms))


def _reconnect_reason(
    *,
    anchor_candidate_idx: int | None,
    generated_atoms: set[int],
    connected_to_anchor: bool,
    anchor_neighbor_count: int,
    num_extra_attachments: int,
    floating: bool,
) -> str:
    if anchor_candidate_idx is None:
        return "anchor_not_mapped"
    if not generated_atoms:
        return "generated_fragment_empty"
    if floating:
        return "floating_fragment"
    if not connected_to_anchor:
        return "not_connected_to_anchor"
    if anchor_neighbor_count != 1:
        return f"anchor_neighbor_count={anchor_neighbor_count}"
    if num_extra_attachments:
        return f"extra_attachments={num_extra_attachments}"
    return "unknown"


def _atom_symbol(mol: Any, atom_idx: int) -> str:
    return str(mol.GetAtomWithIdx(int(atom_idx)).GetSymbol())


def _multiset_mismatch_count(expected: list[str], observed: list[str]) -> int:
    from collections import Counter

    expected_counter = Counter(expected)
    observed_counter = Counter(observed)
    keys = set(expected_counter) | set(observed_counter)
    return int(sum(abs(expected_counter[key] - observed_counter[key]) for key in keys))


def _size_status(generated_count: int, target_count: int) -> str:
    if generated_count == 0:
        return "empty"
    if generated_count == target_count:
        return "matched"
    if generated_count < target_count:
        return "smaller"
    return "larger"

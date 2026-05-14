from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from clash2feedback.geometry.clash import detect_clashes
from clash2feedback.perturb.quality import copy_mol_with_coords
from clash2feedback.perturb.rotation import rotate_atoms_around_axis
from clash2feedback.repair.phase4_inputs import Phase4CaseInput, adapter_input_row, read_first_mol


def run_rule_backend(
    case_input: Phase4CaseInput,
    *,
    backend_cfg: dict[str, Any],
    verifier_config: dict[str, Any],
    run_root: str | Path,
    k: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start = time.perf_counter()
    backend_name = str(backend_cfg.get("backend_name", "rule_fixed_topology"))
    backend_unit = str(backend_cfg.get("backend_unit", "fixed_topology_local_conformer_repair"))
    run_dir = Path(run_root) / "rule_only" / case_input.case_id
    run_dir.mkdir(parents=True, exist_ok=True)
    input_row = adapter_input_row(
        case_input,
        backend_name=backend_name,
        backend_unit=backend_unit,
        status="prepared",
        uses_h_clash_in_generation=False,
    )

    try:
        mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
        proposals = _build_proposals(case_input, mol, backend_cfg, verifier_config)
        deduped = _deduplicate_proposals(proposals, case_input.mask_atom_indices, float(backend_cfg.get("dedup_rmsd_angstrom", 0.1)))
        selected = sorted(deduped, key=lambda row: row["sort_key"])[: max(int(k), 0)]
        runtime_sec = time.perf_counter() - start
        rows: list[dict[str, Any]] = []
        for index, proposal in enumerate(selected, start=1):
            candidate_path = run_dir / f"rule_candidate_{index:03d}.sdf"
            _write_candidate_sdf(mol, proposal["coords"], candidate_path)
            rows.append(
                _candidate_row(
                    case_input,
                    backend_name=backend_name,
                    backend_unit=backend_unit,
                    candidate_index=index,
                    candidate_path=candidate_path,
                    proposal_count=len(proposals),
                    candidate_count=len(selected),
                    runtime_sec=runtime_sec,
                    failure_stage="",
                    failure_reason="",
                    candidate_source=str(proposal["candidate_source"]),
                    generation_metadata=proposal["metadata"],
                )
            )
        if not rows:
            rows.append(
                _candidate_row(
                    case_input,
                    backend_name=backend_name,
                    backend_unit=backend_unit,
                    candidate_index=0,
                    candidate_path=None,
                    proposal_count=len(proposals),
                    candidate_count=0,
                    runtime_sec=runtime_sec,
                    failure_stage="generation",
                    failure_reason="no_rule_proposals_selected",
                    candidate_source="rule_fixed_topology",
                    generation_metadata={},
                )
            )
        return input_row, rows
    except Exception as exc:
        runtime_sec = time.perf_counter() - start
        return input_row, [
            _candidate_row(
                case_input,
                backend_name=backend_name,
                backend_unit=backend_unit,
                candidate_index=0,
                candidate_path=None,
                proposal_count=0,
                candidate_count=0,
                runtime_sec=runtime_sec,
                failure_stage="generation",
                failure_reason=f"{type(exc).__name__}:{exc}",
                candidate_source="rule_fixed_topology",
                generation_metadata={},
            )
        ]


def _build_proposals(
    case_input: Phase4CaseInput,
    mol: Any,
    backend_cfg: dict[str, Any],
    verifier_config: dict[str, Any],
) -> list[dict[str, Any]]:
    coords = np.asarray(case_input.failed_ligand_coords, dtype=np.float32)
    proposals: list[dict[str, Any]] = []
    for angle in backend_cfg.get("single_axis_angles_deg", []):
        repaired, _ = rotate_atoms_around_axis(
            coords,
            axis_start_atom_idx=case_input.anchor_scaffold_atom_idx,
            axis_end_atom_idx=case_input.anchor_rgroup_atom_idx,
            atom_indices=case_input.mask_atom_indices,
            angle_deg=float(angle),
        )
        proposals.append(_scored_proposal(case_input, repaired, verifier_config, "single_anchor_axis_rotation", {"angle_deg": float(angle)}))

    for bond in _rotatable_bonds_in_mask(mol, set(case_input.mask_atom_indices)):
        moving = _side_away_from_anchor(mol, bond[0], bond[1], case_input.anchor_rgroup_atom_idx)
        if not moving or not moving.issubset(set(case_input.mask_atom_indices)):
            continue
        axis_start, axis_end = (bond[0], bond[1]) if bond[1] in moving else (bond[1], bond[0])
        for angle in backend_cfg.get("torsion_angles_deg", []):
            repaired, _ = rotate_atoms_around_axis(
                coords,
                axis_start_atom_idx=axis_start,
                axis_end_atom_idx=axis_end,
                atom_indices=sorted(moving),
                angle_deg=float(angle),
            )
            proposals.append(
                _scored_proposal(
                    case_input,
                    repaired,
                    verifier_config,
                    "internal_target_torsion",
                    {"angle_deg": float(angle), "torsion_bond": [int(bond[0]), int(bond[1])], "moved_atom_indices": sorted(moving)},
                )
            )
    return proposals


def _scored_proposal(
    case_input: Phase4CaseInput,
    coords: np.ndarray,
    verifier_config: dict[str, Any],
    source: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    detector_cfg = verifier_config.get("detector", {})
    old_scope = str(detector_cfg.get("default_old_scope", "phase0_pocket8"))
    new_scope = str(detector_cfg.get("default_new_scope", "pocket10_all_atoms"))
    delta = float(detector_cfg.get("delta_angstrom", 0.4))
    severe = float(detector_cfg.get("severe_depth_threshold_angstrom", 0.4))
    old_after = detect_clashes(
        case_input.failed_sample,
        ligand_coords=coords,
        receptor_scope=old_scope,
        delta_angstrom=delta,
        severe_depth_threshold_angstrom=severe,
    )
    new_after = detect_clashes(
        case_input.failed_sample,
        ligand_coords=coords,
        receptor_scope=new_scope,
        delta_angstrom=delta,
        severe_depth_threshold_angstrom=severe,
    )
    sort_key = (
        int(old_after.get("num_severe_clash_pairs") or 0),
        float(old_after.get("total_clash_score") or 0.0),
        int(new_after.get("num_severe_clash_pairs") or 0),
        float(new_after.get("total_clash_score") or 0.0),
    )
    return {
        "coords": np.asarray(coords, dtype=np.float32),
        "candidate_source": source,
        "metadata": {
            **metadata,
            "old_after_severe_pairs": int(old_after.get("num_severe_clash_pairs") or 0),
            "old_after_total_clash_score": float(old_after.get("total_clash_score") or 0.0),
            "new_after_severe_pairs": int(new_after.get("num_severe_clash_pairs") or 0),
            "new_after_total_clash_score": float(new_after.get("total_clash_score") or 0.0),
        },
        "sort_key": sort_key,
    }


def _deduplicate_proposals(proposals: list[dict[str, Any]], moved_atoms: list[int], threshold: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    moved = np.asarray(moved_atoms, dtype=np.int64)
    for proposal in sorted(proposals, key=lambda row: row["sort_key"]):
        coords = proposal["coords"]
        duplicate = False
        for previous in selected:
            rmsd = _masked_rmsd(coords, previous["coords"], moved)
            if rmsd <= threshold:
                duplicate = True
                break
        if not duplicate:
            selected.append(proposal)
    return selected


def _rotatable_bonds_in_mask(mol: Any, mask: set[int]) -> list[tuple[int, int]]:
    bonds: list[tuple[int, int]] = []
    for bond in mol.GetBonds():
        if bond.IsInRing() or str(bond.GetBondType()) != "SINGLE":
            continue
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        if begin in mask and end in mask and mol.GetAtomWithIdx(begin).GetAtomicNum() > 1 and mol.GetAtomWithIdx(end).GetAtomicNum() > 1:
            bonds.append((begin, end))
    return bonds


def _side_away_from_anchor(mol: Any, begin: int, end: int, anchor_idx: int) -> set[int]:
    left = _component_without_bond(mol, begin, forbidden_neighbor=end)
    right = _component_without_bond(mol, end, forbidden_neighbor=begin)
    if anchor_idx in left and anchor_idx not in right:
        return right
    if anchor_idx in right and anchor_idx not in left:
        return left
    return set()


def _component_without_bond(mol: Any, start: int, *, forbidden_neighbor: int) -> set[int]:
    seen = {int(start)}
    queue: deque[int] = deque([int(start)])
    while queue:
        current = queue.popleft()
        atom = mol.GetAtomWithIdx(current)
        for neighbor in atom.GetNeighbors():
            next_idx = int(neighbor.GetIdx())
            if current == int(start) and next_idx == int(forbidden_neighbor):
                continue
            if next_idx in seen:
                continue
            seen.add(next_idx)
            queue.append(next_idx)
    return seen


def _write_candidate_sdf(mol: Any, coords: np.ndarray, path: Path) -> None:
    from rdkit import Chem

    writer_mol = copy_mol_with_coords(mol, np.asarray(coords, dtype=np.float32))
    writer = Chem.SDWriter(str(path))
    writer.write(writer_mol)
    writer.close()


def _candidate_row(
    case_input: Phase4CaseInput,
    *,
    backend_name: str,
    backend_unit: str,
    candidate_index: int,
    candidate_path: Path | None,
    proposal_count: int,
    candidate_count: int,
    runtime_sec: float,
    failure_stage: str,
    failure_reason: str,
    candidate_source: str,
    generation_metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "backend_name": backend_name,
        "backend_unit": backend_unit,
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "attempt_id": f"{backend_name}:{case_input.case_id}",
        "candidate_id": f"{backend_name}:{case_input.case_id}:{candidate_index:03d}" if candidate_index else "",
        "candidate_index": int(candidate_index),
        "candidate_path": str(candidate_path) if candidate_path is not None else "",
        "candidate_source": candidate_source,
        "proposal_count": int(proposal_count),
        "candidate_count": int(candidate_count),
        "runtime_sec": float(runtime_sec),
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "same_topology": True,
        "requires_fixed_structure_match": False,
        "uses_h_clash_in_generation": False,
        "generation_metadata": generation_metadata,
    }


def _masked_rmsd(coords_a: np.ndarray, coords_b: np.ndarray, atom_indices: np.ndarray) -> float:
    if atom_indices.size == 0:
        return 0.0
    diff = coords_a[atom_indices] - coords_b[atom_indices]
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))

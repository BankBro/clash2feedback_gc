from __future__ import annotations

import copy
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from clash2feedback.repair.case_selection import parse_json_list


@dataclass(frozen=True)
class Phase4CaseInput:
    case_id: str
    base_sample_id: str
    selected_row: dict[str, Any]
    manifest_row: dict[str, Any]
    base_sample: dict[str, Any]
    failed_sample: dict[str, Any]
    phase2_sample: dict[str, Any]
    failed_ligand_coords: np.ndarray
    mask_atom_indices: list[int]
    keep_atom_indices: list[int]
    anchor_scaffold_atom_idx: int
    anchor_rgroup_atom_idx: int
    anchor_bond_idx: int
    target_rgroup: str
    raw_protein_path: Path
    failed_ligand_sdf: Path
    original_ligand_sdf: Path
    phase2_sample_path: Path
    processed_sample_path: Path


def load_phase4_case_inputs(
    selected_cases: pd.DataFrame,
    *,
    phase2_manifest_path: str | Path,
    phase2_benchmark_root: str | Path,
    processed_root: str | Path,
) -> list[Phase4CaseInput]:
    phase2_manifest = pd.read_parquet(phase2_manifest_path)
    manifest_by_case = {str(row["case_id"]): row for _, row in phase2_manifest.iterrows()}
    benchmark_root = Path(phase2_benchmark_root)
    processed = Path(processed_root)

    result: list[Phase4CaseInput] = []
    for _, selected in selected_cases.iterrows():
        case_id = str(selected["case_id"])
        if case_id not in manifest_by_case:
            raise ValueError(f"Selected case missing from phase2 manifest: {case_id}")
        manifest_row = manifest_by_case[case_id]
        base_sample_id = str(selected["base_sample_id"])
        phase2_sample_path = benchmark_root / str(manifest_row.get("sample_path") or f"samples/{case_id}.pkl")
        failed_ligand_sdf = benchmark_root / str(manifest_row.get("failed_ligand_sdf") or f"ligands/{case_id}_failed.sdf")
        original_ligand_sdf = benchmark_root / str(manifest_row.get("original_ligand_sdf") or f"ligands/{case_id}_original.sdf")
        processed_sample_path = processed / "complexes" / f"{base_sample_id}.pkl"
        phase2_sample = _load_pickle(phase2_sample_path)
        base_sample = _load_pickle(processed_sample_path)
        failed_coords = np.asarray(phase2_sample["failed_ligand_coords"], dtype=np.float32)
        failed_sample = copy.deepcopy(base_sample)
        failed_sample.setdefault("ligand", {})["coords"] = failed_coords.copy()

        raw_protein_path = Path(str(base_sample.get("paths", {}).get("raw_protein_path") or ""))
        if not raw_protein_path.exists():
            raise FileNotFoundError(f"Missing raw protein PDB for {case_id}: {raw_protein_path}")
        if not failed_ligand_sdf.exists():
            raise FileNotFoundError(f"Missing failed ligand SDF for {case_id}: {failed_ligand_sdf}")
        if not original_ligand_sdf.exists():
            raise FileNotFoundError(f"Missing original ligand SDF for {case_id}: {original_ligand_sdf}")

        result.append(
            Phase4CaseInput(
                case_id=case_id,
                base_sample_id=base_sample_id,
                selected_row=selected.to_dict(),
                manifest_row=manifest_row.to_dict(),
                base_sample=base_sample,
                failed_sample=failed_sample,
                phase2_sample=phase2_sample,
                failed_ligand_coords=failed_coords,
                mask_atom_indices=parse_json_list(selected["oracle_mask_atom_indices"]),
                keep_atom_indices=parse_json_list(selected["oracle_keep_atom_indices"]),
                anchor_scaffold_atom_idx=int(selected["oracle_anchor_scaffold_atom_idx"]),
                anchor_rgroup_atom_idx=int(selected["oracle_anchor_rgroup_atom_idx"]),
                anchor_bond_idx=int(selected["oracle_anchor_bond_idx"]),
                target_rgroup=str(manifest_row.get("target_rgroup") or phase2_sample.get("target_rgroup") or ""),
                raw_protein_path=raw_protein_path,
                failed_ligand_sdf=failed_ligand_sdf,
                original_ligand_sdf=original_ligand_sdf,
                phase2_sample_path=phase2_sample_path,
                processed_sample_path=processed_sample_path,
            )
        )
    return result


def adapter_input_row(case_input: Phase4CaseInput, *, backend_name: str, backend_unit: str, status: str, **extra: Any) -> dict[str, Any]:
    row = {
        "backend_name": backend_name,
        "backend_unit": backend_unit,
        "case_id": case_input.case_id,
        "base_sample_id": case_input.base_sample_id,
        "adapter_status": status,
        "phase2_sample_path": str(case_input.phase2_sample_path),
        "processed_sample_path": str(case_input.processed_sample_path),
        "failed_ligand_sdf": str(case_input.failed_ligand_sdf),
        "raw_protein_path": str(case_input.raw_protein_path),
        "oracle_mask_atom_indices": case_input.mask_atom_indices,
        "oracle_keep_atom_indices": case_input.keep_atom_indices,
        "oracle_anchor_scaffold_atom_idx": case_input.anchor_scaffold_atom_idx,
        "oracle_anchor_rgroup_atom_idx": case_input.anchor_rgroup_atom_idx,
        "oracle_anchor_bond_idx": case_input.anchor_bond_idx,
        "target_rgroup": case_input.target_rgroup,
    }
    row.update(extra)
    return row


def write_keep_submol_sdf(case_input: Phase4CaseInput, output_path: str | Path) -> dict[str, Any]:
    from rdkit import Chem

    mol = read_first_mol(case_input.failed_ligand_sdf, sanitize=False)
    keep = set(case_input.keep_atom_indices)
    editable = set(case_input.mask_atom_indices)
    if keep & editable:
        raise ValueError(f"Mask/keep overlap for {case_input.case_id}")
    if len(keep) + len(editable) != mol.GetNumAtoms():
        raise ValueError(f"Mask/keep does not cover all ligand atoms for {case_input.case_id}")

    rw_mol = Chem.RWMol(mol)
    for atom_idx in sorted(editable, reverse=True):
        rw_mol.RemoveAtom(int(atom_idx))
    fixed = rw_mol.GetMol()
    fixed.UpdatePropertyCache(strict=False)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(path))
    writer.write(fixed)
    writer.close()
    return {
        "fix_atoms_sdf": str(path),
        "fixed_atom_count": int(fixed.GetNumAtoms()),
        "add_n_nodes": int(len(case_input.mask_atom_indices)),
    }


def read_first_mol(path: str | Path, *, sanitize: bool = False) -> Any:
    from rdkit import Chem

    supplier = Chem.SDMolSupplier(str(path), sanitize=sanitize, removeHs=False)
    mol = supplier[0] if supplier and len(supplier) else None
    if mol is None:
        raise ValueError(f"Unable to read SDF molecule: {path}")
    return mol


def _load_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return pickle.load(f)

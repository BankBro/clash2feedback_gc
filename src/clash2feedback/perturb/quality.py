from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from clash2feedback.geometry.vdw import get_vdw_radius


def mol_from_sample(sample: dict[str, Any]) -> Any:
    Chem = _import_chem()
    molblock = sample.get("ligand", {}).get("molblock")
    if not molblock:
        raise ValueError(f"Sample {sample.get('sample_id', '')} has no ligand molblock.")
    mol = Chem.MolFromMolBlock(str(molblock), sanitize=False, removeHs=False)
    if mol is None:
        raise ValueError(f"Sample {sample.get('sample_id', '')} ligand molblock is unreadable.")
    return mol


def copy_mol_with_coords(mol: Any, coords: np.ndarray) -> Any:
    Chem = _import_chem()
    Geometry = _import_geometry()
    copy = Chem.Mol(mol)
    positions = np.asarray(coords, dtype=float)
    if copy.GetNumConformers() == 0:
        conf = Chem.Conformer(copy.GetNumAtoms())
        copy.AddConformer(conf, assignId=True)
    conf = copy.GetConformer()
    for atom_idx, xyz in enumerate(positions):
        conf.SetAtomPosition(int(atom_idx), Geometry.Point3D(float(xyz[0]), float(xyz[1]), float(xyz[2])))
    return copy


def check_rotatable_anchor_bond(mol: Any, rgroup: dict[str, Any], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    Chem = _import_chem()
    config = cfg or {}
    bond_idx = rgroup.get("anchor_bond_idx")
    if bond_idx is None or int(bond_idx) < 0 or int(bond_idx) >= mol.GetNumBonds():
        return _anchor_result(False, "anchor_bond_missing")
    bond = mol.GetBondWithIdx(int(bond_idx))
    begin = bond.GetBeginAtom()
    end = bond.GetEndAtom()
    if config.get("reject_double_bond", True) and bond.GetBondType() != Chem.BondType.SINGLE:
        return _anchor_result(False, "anchor_bond_not_single")
    if config.get("reject_ring_bond", True) and bond.IsInRing():
        return _anchor_result(False, "anchor_bond_in_ring")
    if config.get("reject_aromatic_bond", True) and (bond.GetIsAromatic() or begin.GetIsAromatic() or end.GetIsAromatic()):
        return _anchor_result(False, "anchor_bond_aromatic")
    if begin.GetAtomicNum() <= 1 or end.GetAtomicNum() <= 1:
        return _anchor_result(False, "anchor_bond_has_hydrogen")
    if config.get("reject_amide_like_bond", True) and _is_amide_like_bond(bond):
        return _anchor_result(False, "anchor_bond_amide_like")
    if config.get("reject_conjugated_bond", True) and bond.GetIsConjugated():
        return _anchor_result(False, "anchor_bond_conjugated")
    return _anchor_result(True, "")


def evaluate_ligand_only_quality(
    sample: dict[str, Any],
    mol: Any,
    rgroup: dict[str, Any],
    original_coords: np.ndarray,
    failed_coords: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    chemistry_cfg = config.get("chemistry", {})
    geometry_cfg = config.get("geometry", {})
    original = np.asarray(original_coords, dtype=np.float32)
    failed = np.asarray(failed_coords, dtype=np.float32)

    anchor_result = check_rotatable_anchor_bond(mol, rgroup, chemistry_cfg)
    failed_mol = copy_mol_with_coords(mol, failed)
    sanitize_ok, sanitize_error = _sanitize_ok(failed_mol)
    coords_finite = bool(np.isfinite(failed).all())
    anchor_integrity = _anchor_integrity_pass(
        original,
        failed,
        rgroup,
        threshold=float(geometry_cfg.get("anchor_bond_length_delta_threshold", 0.05)),
    )
    bond_length_valid, max_bond_delta = _bond_length_sanity(
        mol,
        original,
        failed,
        threshold=float(geometry_cfg.get("bond_length_delta_threshold", 0.05)),
    )
    internal_count, internal_max_depth = ligand_internal_severe_clash_count(
        mol,
        failed,
        delta_angstrom=float(geometry_cfg.get("ligand_internal_delta_angstrom", 0.4)),
        severe_depth_threshold_angstrom=float(geometry_cfg.get("ligand_internal_severe_depth_threshold_angstrom", 0.4)),
    )
    chirality_preserved = _chirality_preserved(mol, original, failed)
    energy = ligand_energy_delta(
        mol,
        original,
        failed,
        forcefield_preference=list(chemistry_cfg.get("forcefield_preference", ["MMFF", "UFF"])),
        threshold_mode=chemistry_cfg.get("energy_delta_threshold_mode", "record_only"),
    )

    fatal_errors: list[str] = []
    if chemistry_cfg.get("require_rdkit_sanitize", True) and not sanitize_ok:
        fatal_errors.append("rdkit_sanitize_failed")
    if chemistry_cfg.get("require_rotatable_anchor_bond", True) and not bool(anchor_result["rotatable_bond_valid"]):
        fatal_errors.append(str(anchor_result["rotatable_bond_reason"]))
    if not coords_finite:
        fatal_errors.append("coords_not_finite")
    if not anchor_integrity:
        fatal_errors.append("anchor_integrity_failed")
    if not bond_length_valid:
        fatal_errors.append("bond_length_invalid")
    if internal_count > int(geometry_cfg.get("ligand_internal_severe_clash_allowed", 0)):
        fatal_errors.append("ligand_internal_severe_clash")
    if chemistry_cfg.get("require_chirality_preserved", True) and not chirality_preserved:
        fatal_errors.append("chirality_changed")
    if chemistry_cfg.get("use_energy_delta_filter", True) and not bool(energy["energy_delta_pass"]):
        fatal_errors.append("energy_delta_failed")

    return {
        "ligand_valid": len(fatal_errors) == 0,
        "rdkit_sanitize_ok": bool(sanitize_ok),
        "sanitize_error": sanitize_error,
        "rotatable_bond_valid": bool(anchor_result["rotatable_bond_valid"]),
        "rotatable_bond_reason": str(anchor_result["rotatable_bond_reason"]),
        "anchor_integrity_pass": bool(anchor_integrity),
        "bond_length_valid": bool(bond_length_valid),
        "max_bond_length_delta": float(max_bond_delta),
        "coords_finite": bool(coords_finite),
        "chirality_preserved": bool(chirality_preserved),
        "ligand_internal_severe_clash_count": int(internal_count),
        "ligand_internal_max_depth": float(internal_max_depth),
        "fatal_errors": fatal_errors,
        **energy,
    }


def ligand_internal_severe_clash_count(
    mol: Any,
    coords: np.ndarray,
    *,
    delta_angstrom: float = 0.4,
    severe_depth_threshold_angstrom: float = 0.4,
) -> tuple[int, float]:
    positions = np.asarray(coords, dtype=np.float32)
    graph_distances = _bond_graph_distances(mol)
    count = 0
    max_depth = 0.0
    for i in range(mol.GetNumAtoms()):
        atom_i = mol.GetAtomWithIdx(i)
        if atom_i.GetAtomicNum() <= 1:
            continue
        for j in range(i + 1, mol.GetNumAtoms()):
            atom_j = mol.GetAtomWithIdx(j)
            if atom_j.GetAtomicNum() <= 1:
                continue
            if graph_distances.get((i, j), 99) <= 2:
                continue
            distance = float(np.linalg.norm(positions[i] - positions[j]))
            vdw_sum = get_vdw_radius(atom_i.GetSymbol()) + get_vdw_radius(atom_j.GetSymbol())
            depth = max(0.0, float(vdw_sum) - float(delta_angstrom) - distance)
            max_depth = max(max_depth, depth)
            if depth >= float(severe_depth_threshold_angstrom):
                count += 1
    return count, max_depth


def ligand_energy_delta(
    mol: Any,
    original_coords: np.ndarray,
    failed_coords: np.ndarray,
    *,
    forcefield_preference: list[str],
    threshold_mode: Any,
) -> dict[str, Any]:
    try:
        original_energy = _single_point_energy(mol, original_coords, forcefield_preference)
        failed_energy = _single_point_energy(mol, failed_coords, forcefield_preference)
    except Exception as exc:
        return {
            "forcefield_type": "unavailable",
            "energy_original": float("nan"),
            "energy_failed": float("nan"),
            "energy_delta": float("nan"),
            "energy_delta_pass": True,
            "energy_check_status": f"unavailable:{exc}",
        }
    forcefield_type = original_energy["forcefield_type"] if original_energy["forcefield_type"] == failed_energy["forcefield_type"] else "mixed"
    delta = float(failed_energy["energy"] - original_energy["energy"])
    if isinstance(threshold_mode, int | float):
        passed = delta <= float(threshold_mode)
        status = "threshold_applied"
    else:
        passed = True
        status = "record_only"
    return {
        "forcefield_type": forcefield_type,
        "energy_original": float(original_energy["energy"]),
        "energy_failed": float(failed_energy["energy"]),
        "energy_delta": delta,
        "energy_delta_pass": bool(passed),
        "energy_check_status": status,
    }


def scaffold_and_non_target_rmsd(
    sample: dict[str, Any],
    original_coords: np.ndarray,
    failed_coords: np.ndarray,
    target_rgroup: str,
) -> tuple[float, float, float]:
    original = np.asarray(original_coords, dtype=np.float32)
    failed = np.asarray(failed_coords, dtype=np.float32)
    scaffold_mask = np.asarray(sample.get("masks", {}).get("ligand_scaffold_mask", []), dtype=bool)
    rgroup_ids = list(sample.get("masks", {}).get("ligand_rgroup_id", []))
    heavy_mask = np.asarray(sample.get("masks", {}).get("heavy_atom_mask", np.ones(original.shape[0], dtype=bool)), dtype=bool)
    if scaffold_mask.shape[0] != original.shape[0]:
        scaffold_mask = np.zeros(original.shape[0], dtype=bool)
        for idx in sample.get("scaffold", {}).get("atom_indices", []):
            if 0 <= int(idx) < original.shape[0]:
                scaffold_mask[int(idx)] = True
    non_target_mask = np.asarray(
        [
            bool(heavy_mask[idx])
            and (idx >= len(rgroup_ids) or rgroup_ids[idx] != target_rgroup)
            and not bool(scaffold_mask[idx])
            for idx in range(original.shape[0])
        ],
        dtype=bool,
    )
    target_mask = np.asarray(
        [idx < len(rgroup_ids) and rgroup_ids[idx] == target_rgroup and bool(heavy_mask[idx]) for idx in range(original.shape[0])],
        dtype=bool,
    )
    return _masked_rmsd(original, failed, scaffold_mask), _masked_rmsd(original, failed, non_target_mask), _masked_rmsd(original, failed, target_mask)


def _anchor_result(valid: bool, reason: str) -> dict[str, Any]:
    return {"rotatable_bond_valid": bool(valid), "rotatable_bond_reason": str(reason)}


def _is_amide_like_bond(bond: Any) -> bool:
    atoms = [bond.GetBeginAtom(), bond.GetEndAtom()]
    atomic_numbers = {atom.GetAtomicNum() for atom in atoms}
    if atomic_numbers != {6, 7}:
        return False
    carbon = atoms[0] if atoms[0].GetAtomicNum() == 6 else atoms[1]
    for neighbor_bond in carbon.GetBonds():
        if neighbor_bond.GetIdx() == bond.GetIdx():
            continue
        other = neighbor_bond.GetOtherAtom(carbon)
        if other.GetAtomicNum() in {7, 8, 16} and abs(float(neighbor_bond.GetBondTypeAsDouble()) - 2.0) < 1e-6:
            return True
    return False


def _sanitize_ok(mol: Any) -> tuple[bool, str]:
    Chem = _import_chem()
    try:
        copy = Chem.Mol(mol)
        Chem.SanitizeMol(copy)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _anchor_integrity_pass(original: np.ndarray, failed: np.ndarray, rgroup: dict[str, Any], *, threshold: float) -> bool:
    scaffold = rgroup.get("anchor_scaffold_atom_idx")
    anchor = rgroup.get("anchor_rgroup_atom_idx")
    if scaffold is None or anchor is None:
        return False
    before = float(np.linalg.norm(original[int(scaffold)] - original[int(anchor)]))
    after = float(np.linalg.norm(failed[int(scaffold)] - failed[int(anchor)]))
    return abs(after - before) <= float(threshold)


def _bond_length_sanity(mol: Any, original: np.ndarray, failed: np.ndarray, *, threshold: float) -> tuple[bool, float]:
    max_delta = 0.0
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        before = float(np.linalg.norm(original[begin] - original[end]))
        after = float(np.linalg.norm(failed[begin] - failed[end]))
        max_delta = max(max_delta, abs(after - before))
    return max_delta <= float(threshold), max_delta


def _chirality_preserved(mol: Any, original: np.ndarray, failed: np.ndarray) -> bool:
    Chem = _import_chem()
    try:
        original_mol = copy_mol_with_coords(mol, original)
        failed_mol = copy_mol_with_coords(mol, failed)
        Chem.AssignAtomChiralTagsFromStructure(original_mol)
        Chem.AssignAtomChiralTagsFromStructure(failed_mol)
        original_tags = [str(atom.GetChiralTag()) for atom in original_mol.GetAtoms()]
        failed_tags = [str(atom.GetChiralTag()) for atom in failed_mol.GetAtoms()]
        return original_tags == failed_tags
    except Exception:
        return True


def _single_point_energy(mol: Any, coords: np.ndarray, preference: list[str]) -> dict[str, Any]:
    Chem = _import_chem()
    AllChem = _import_all_chem()
    base = copy_mol_with_coords(mol, coords)
    with_h = Chem.AddHs(base, addCoords=True)
    for forcefield in preference:
        name = str(forcefield).upper()
        if name == "MMFF":
            props = AllChem.MMFFGetMoleculeProperties(with_h, mmffVariant="MMFF94s")
            if props is None:
                continue
            ff = AllChem.MMFFGetMoleculeForceField(with_h, props)
        elif name == "UFF":
            ff = AllChem.UFFGetMoleculeForceField(with_h)
        else:
            continue
        if ff is None:
            continue
        return {"forcefield_type": name, "energy": float(ff.CalcEnergy())}
    raise ValueError("no_supported_forcefield")


def _bond_graph_distances(mol: Any) -> dict[tuple[int, int], int]:
    distances: dict[tuple[int, int], int] = {}
    adjacency: dict[int, list[int]] = {idx: [] for idx in range(mol.GetNumAtoms())}
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        adjacency[begin].append(end)
        adjacency[end].append(begin)
    for start in range(mol.GetNumAtoms()):
        seen = {start: 0}
        queue: deque[int] = deque([start])
        while queue:
            current = queue.popleft()
            if seen[current] >= 2:
                continue
            for neighbor in adjacency[current]:
                if neighbor in seen:
                    continue
                seen[neighbor] = seen[current] + 1
                queue.append(neighbor)
        for end, distance in seen.items():
            if start < end:
                distances[(start, end)] = int(distance)
    return distances


def _masked_rmsd(original: np.ndarray, failed: np.ndarray, mask: np.ndarray) -> float:
    if mask.shape[0] != original.shape[0] or not bool(mask.any()):
        return float("nan")
    diff = original[mask] - failed[mask]
    return float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))))


def _import_chem() -> Any:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise ImportError("RDKit is required for phase2 ligand quality gates.") from exc
    return Chem


def _import_all_chem() -> Any:
    try:
        from rdkit.Chem import AllChem
    except ImportError as exc:
        raise ImportError("RDKit AllChem is required for phase2 energy checks.") from exc
    return AllChem


def _import_geometry() -> Any:
    try:
        from rdkit import Geometry
    except ImportError as exc:
        raise ImportError("RDKit Geometry is required for coordinate updates.") from exc
    return Geometry

from __future__ import annotations

from typing import Any

import numpy as np

from clash2feedback.geometry.vdw import get_vdw_radius
from clash2feedback.perturb.quality import ligand_internal_severe_clash_count


LIGAND_VALIDITY_COLUMNS = [
    "candidate_id",
    "postprocess_stage",
    "rdkit_readable",
    "rdkit_sanitize_ok",
    "sanitize_error",
    "num_fragments",
    "largest_fragment_selected",
    "allowed_elements_ok",
    "heavy_atom_count",
    "heavy_atom_count_in_range",
    "coords_finite",
    "has_3d_conformer",
    "ligand_internal_severe_clash_count",
    "ligand_internal_max_depth",
    "forcefield_type",
    "energy",
    "energy_check_status",
    "ligand_validity_status",
    "ligand_validity_reason",
]


def evaluate_generated_ligand(
    candidate_id: str,
    mol: Any | None,
    *,
    postprocess_stage: str,
    config: dict[str, Any] | None = None,
    largest_fragment_selected: bool = False,
    readable: bool = True,
) -> dict[str, Any]:
    cfg = config or {}
    if mol is None or not readable:
        return _row(
            candidate_id,
            postprocess_stage,
            rdkit_readable=False,
            ligand_validity_status="invalid",
            ligand_validity_reason="rdkit_unreadable",
        )

    Chem = _import_rdkit()
    sanitize_ok, sanitize_error = _sanitize_ok(Chem, mol)
    fragments = Chem.GetMolFrags(mol, sanitizeFrags=False)
    heavy_atom_count = int(sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() > 1))
    min_heavy = int(cfg.get("min_heavy_atoms", 5))
    max_heavy = int(cfg.get("max_heavy_atoms", 80))
    heavy_in_range = min_heavy <= heavy_atom_count <= max_heavy
    allowed = set(cfg.get("allowed_elements", ["C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H"]))
    elements = {atom.GetSymbol() for atom in mol.GetAtoms()}
    allowed_ok = elements.issubset(allowed)
    has_3d = mol.GetNumConformers() > 0 and bool(mol.GetConformer().Is3D())
    coords_finite = _coords_finite(mol)
    internal_count, internal_max = _internal_clashes(mol, cfg)
    energy = _single_point_energy(mol, list(cfg.get("forcefield_preference", ["MMFF", "UFF"])))

    fatal: list[str] = []
    if not sanitize_ok:
        fatal.append("rdkit_sanitize_failed")
    if bool(cfg.get("require_single_fragment", True)) and len(fragments) != 1:
        fatal.append("multiple_fragments")
    if not allowed_ok:
        fatal.append("disallowed_elements")
    if not heavy_in_range:
        fatal.append("heavy_atom_count_out_of_range")
    if bool(cfg.get("require_3d", True)) and not has_3d:
        fatal.append("no_3d_conformer")
    if not coords_finite:
        fatal.append("coords_not_finite")
    if internal_count > int(cfg.get("ligand_internal_severe_clash_allowed", 0)):
        fatal.append("ligand_internal_severe_clash")

    return _row(
        candidate_id,
        postprocess_stage,
        rdkit_readable=True,
        rdkit_sanitize_ok=sanitize_ok,
        sanitize_error=sanitize_error,
        num_fragments=len(fragments),
        largest_fragment_selected=largest_fragment_selected,
        allowed_elements_ok=allowed_ok,
        heavy_atom_count=heavy_atom_count,
        heavy_atom_count_in_range=heavy_in_range,
        coords_finite=coords_finite,
        has_3d_conformer=has_3d,
        ligand_internal_severe_clash_count=internal_count,
        ligand_internal_max_depth=internal_max,
        forcefield_type=energy["forcefield_type"],
        energy=energy["energy"],
        energy_check_status=energy["energy_check_status"],
        ligand_validity_status="valid" if not fatal else "invalid",
        ligand_validity_reason=";".join(fatal),
    )


def _row(candidate_id: str, postprocess_stage: str, **updates: Any) -> dict[str, Any]:
    row = {
        "candidate_id": candidate_id,
        "postprocess_stage": postprocess_stage,
        "rdkit_readable": False,
        "rdkit_sanitize_ok": False,
        "sanitize_error": "",
        "num_fragments": 0,
        "largest_fragment_selected": False,
        "allowed_elements_ok": False,
        "heavy_atom_count": 0,
        "heavy_atom_count_in_range": False,
        "coords_finite": False,
        "has_3d_conformer": False,
        "ligand_internal_severe_clash_count": 0,
        "ligand_internal_max_depth": 0.0,
        "forcefield_type": "unavailable",
        "energy": float("nan"),
        "energy_check_status": "unavailable",
        "ligand_validity_status": "invalid",
        "ligand_validity_reason": "",
    }
    row.update(updates)
    return row


def _sanitize_ok(Chem: Any, mol: Any) -> tuple[bool, str]:
    try:
        copy = Chem.Mol(mol)
        Chem.SanitizeMol(copy)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _coords_finite(mol: Any) -> bool:
    if mol.GetNumConformers() == 0:
        return False
    coords = np.asarray(mol.GetConformer().GetPositions(), dtype=float)
    return bool(np.isfinite(coords).all())


def _internal_clashes(mol: Any, cfg: dict[str, Any]) -> tuple[int, float]:
    if mol.GetNumConformers() == 0:
        return 0, 0.0
    try:
        coords = np.asarray(mol.GetConformer().GetPositions(), dtype=np.float32)
        return ligand_internal_severe_clash_count(
            mol,
            coords,
            delta_angstrom=float(cfg.get("ligand_internal_delta_angstrom", 0.4)),
            severe_depth_threshold_angstrom=float(cfg.get("ligand_internal_severe_depth_threshold_angstrom", 0.4)),
        )
    except Exception:
        return 0, 0.0


def _single_point_energy(mol: Any, forcefield_preference: list[str]) -> dict[str, Any]:
    Chem, AllChem = _import_allchem()
    if mol.GetNumConformers() == 0:
        return {"forcefield_type": "unavailable", "energy": float("nan"), "energy_check_status": "no_conformer"}
    work = Chem.Mol(mol)
    for forcefield in forcefield_preference:
        try:
            if forcefield.upper() == "MMFF":
                props = AllChem.MMFFGetMoleculeProperties(work, mmffVariant="MMFF94s")
                if props is None:
                    continue
                ff = AllChem.MMFFGetMoleculeForceField(work, props)
            elif forcefield.upper() == "UFF":
                ff = AllChem.UFFGetMoleculeForceField(work)
            else:
                continue
            if ff is None:
                continue
            return {
                "forcefield_type": forcefield.upper(),
                "energy": float(ff.CalcEnergy()),
                "energy_check_status": "ok",
            }
        except Exception:
            continue
    return {"forcefield_type": "unavailable", "energy": float("nan"), "energy_check_status": "unavailable"}


def ligand_internal_severe_clash_count_from_coords(mol: Any, coords: np.ndarray, *, delta: float = 0.4, severe: float = 0.4) -> tuple[int, float]:
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
            distance = float(np.linalg.norm(coords[i] - coords[j]))
            depth = max(0.0, get_vdw_radius(atom_i.GetSymbol()) + get_vdw_radius(atom_j.GetSymbol()) - float(delta) - distance)
            max_depth = max(max_depth, depth)
            if depth >= float(severe):
                count += 1
    return count, max_depth


def _import_rdkit() -> Any:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise ImportError("RDKit is required for generated ligand validity checks.") from exc
    return Chem


def _import_allchem() -> tuple[Any, Any]:
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError as exc:
        raise ImportError("RDKit is required for generated ligand energy checks.") from exc
    return Chem, AllChem

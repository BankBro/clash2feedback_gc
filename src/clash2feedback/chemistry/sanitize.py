from __future__ import annotations

from typing import Any

import numpy as np


DEFAULT_ALLOWED_ELEMENTS = {"C", "N", "O", "S", "P", "F", "Cl", "Br", "I", "H"}
METAL_ATOMIC_NUMBERS = {
    3,
    4,
    11,
    12,
    13,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28,
    29,
    30,
    31,
    37,
    38,
    39,
    40,
    41,
    42,
    43,
    44,
    45,
    46,
    47,
    48,
    49,
    50,
    55,
    56,
    57,
    72,
    73,
    74,
    75,
    76,
    77,
    78,
    79,
    80,
    81,
    82,
}


def check_ligand_validity(
    mol: Any,
    *,
    min_heavy_atoms: int = 15,
    max_heavy_atoms: int = 60,
    allowed_elements: set[str] | None = None,
    require_single_fragment: bool = True,
    require_3d: bool = True,
    reject_metals: bool = True,
    reject_macrocycles: bool = True,
    macrocycle_min_ring_size: int = 12,
) -> dict[str, Any]:
    Chem = _import_rdkit()
    allowed = set(allowed_elements or DEFAULT_ALLOWED_ELEMENTS)
    allowed.add("H")
    fatal_errors: list[str] = []
    warnings: list[str] = []

    try:
        copy = Chem.Mol(mol)
        Chem.SanitizeMol(copy)
        sanitize_ok = True
    except Exception as exc:
        sanitize_ok = False
        fatal_errors.append("ligand_sanitize_failed")
        warnings.append(f"sanitize_error:{exc}")

    has_3d = mol.GetNumConformers() > 0 and bool(mol.GetConformer().Is3D())
    if require_3d and not has_3d:
        fatal_errors.append("ligand_no_3d_conformer")

    coords_finite = True
    if mol.GetNumConformers() > 0:
        coords = np.asarray(mol.GetConformer().GetPositions(), dtype=float)
        coords_finite = bool(np.isfinite(coords).all())
        if not coords_finite:
            fatal_errors.append("ligand_coords_not_finite")

    fragments = Chem.GetMolFrags(mol, sanitizeFrags=False)
    if require_single_fragment and len(fragments) != 1:
        fatal_errors.append("ligand_multiple_fragments")

    heavy_atoms = [atom for atom in mol.GetAtoms() if atom.GetAtomicNum() > 1]
    num_heavy_atoms = len(heavy_atoms)
    if num_heavy_atoms < min_heavy_atoms or num_heavy_atoms > max_heavy_atoms:
        fatal_errors.append("ligand_heavy_atoms_out_of_range")

    elements = {atom.GetSymbol() for atom in mol.GetAtoms()}
    disallowed = sorted(element for element in elements if element not in allowed)
    if disallowed:
        fatal_errors.append("ligand_disallowed_elements")
        warnings.append("disallowed_elements:" + ",".join(disallowed))

    has_metal = any(atom.GetAtomicNum() in METAL_ATOMIC_NUMBERS for atom in mol.GetAtoms())
    if reject_metals and has_metal:
        fatal_errors.append("ligand_has_metal")

    max_ring_size = _max_ring_size(mol)
    if reject_macrocycles and max_ring_size >= macrocycle_min_ring_size:
        fatal_errors.append("ligand_macrocycle")

    fatal_errors = _dedupe(fatal_errors)
    return {
        "ok": len(fatal_errors) == 0,
        "rdkit_sanitize_ok": sanitize_ok,
        "has_3d_conformer": has_3d,
        "coords_finite": coords_finite,
        "num_fragments": len(fragments),
        "num_heavy_atoms": num_heavy_atoms,
        "heavy_atoms_in_range": min_heavy_atoms <= num_heavy_atoms <= max_heavy_atoms,
        "elements": sorted(elements),
        "disallowed_elements": disallowed,
        "has_metal": has_metal,
        "max_ring_size": max_ring_size,
        "fatal_errors": fatal_errors,
        "warnings": warnings,
    }


def _max_ring_size(mol: Any) -> int:
    ring_info = mol.GetRingInfo()
    atom_rings = ring_info.AtomRings()
    if not atom_rings:
        return 0
    return max(len(ring) for ring in atom_rings)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _import_rdkit() -> Any:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise ImportError(
            "RDKit is required for ligand validity checks. Create the conda env with environment.yml."
        ) from exc
    return Chem

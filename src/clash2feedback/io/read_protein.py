from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from clash2feedback.data.schema import ATOMIC_NUMBERS, ProteinAtoms

BACKBONE_ATOMS = {"N", "CA", "C", "O", "OXT"}
WATER_NAMES = {"HOH", "WAT", "H2O"}


def read_protein_structure(
    protein_path: str | Path,
    *,
    keep_waters: bool = False,
    keep_hetero: bool = False,
    prefer_mmcif: bool = True,
) -> ProteinAtoms:
    PDBParser, MMCIFParser, is_aa = _import_biopython()
    path = Path(protein_path)
    if not path.exists():
        raise FileNotFoundError(f"Protein file does not exist: {path}")

    suffix = path.suffix.lower()
    if suffix in {".cif", ".mmcif"}:
        parser = MMCIFParser(QUIET=True)
    elif suffix == ".pdb":
        parser = PDBParser(QUIET=True)
    elif prefer_mmcif:
        parser = MMCIFParser(QUIET=True)
    else:
        parser = PDBParser(QUIET=True)

    structure = parser.get_structure(path.stem, str(path))
    atom_names: list[str] = []
    elements: list[str] = []
    atomic_numbers: list[int] = []
    coords: list[np.ndarray] = []
    chain_ids: list[str] = []
    residue_ids: list[int] = []
    insertion_codes: list[str] = []
    residue_names: list[str] = []
    is_backbone: list[bool] = []
    is_hetero: list[bool] = []
    occupancies: list[float] = []
    b_factors: list[float] = []
    warnings: list[str] = []

    for model in structure:
        for chain in model:
            for residue in chain:
                residue_name = residue.get_resname().strip()
                hetero_flag, residue_number, insertion_code = residue.id
                is_water = residue_name in WATER_NAMES or hetero_flag == "W"
                residue_is_hetero = hetero_flag != " "
                if is_water and not keep_waters:
                    continue
                if residue_is_hetero and not keep_hetero and not is_aa(residue, standard=False):
                    continue

                for atom in residue.get_atoms():
                    if atom.is_disordered():
                        warnings.append(f"altloc_handled:{chain.id}:{residue_number}:{atom.get_name().strip()}")
                    selected_atom = _select_altloc(atom)
                    atom_name = selected_atom.get_name().strip()
                    raw_element = getattr(selected_atom, "element", "")
                    element = _normalize_element(raw_element, atom_name)
                    if not str(raw_element or "").strip() and element:
                        warnings.append(f"element_inferred:{chain.id}:{residue_number}:{atom_name}:{element}")
                    if not element:
                        warnings.append(f"element_missing:{chain.id}:{residue_number}:{atom_name}")
                        element = _infer_element(atom_name)
                    atomic_number = ATOMIC_NUMBERS.get(element, 0)
                    if atomic_number == 0:
                        warnings.append(f"unknown_element:{element}:{chain.id}:{residue_number}:{atom_name}")

                    atom_names.append(atom_name)
                    elements.append(element)
                    atomic_numbers.append(atomic_number)
                    coords.append(np.asarray(selected_atom.get_coord(), dtype=np.float32))
                    chain_ids.append(str(chain.id))
                    residue_ids.append(int(residue_number))
                    insertion_codes.append(str(insertion_code).strip())
                    residue_names.append(residue_name)
                    is_backbone.append(atom_name in BACKBONE_ATOMS)
                    is_hetero.append(residue_is_hetero)
                    occupancies.append(float(selected_atom.get_occupancy() or 0.0))
                    b_factors.append(float(selected_atom.get_bfactor()))
        break

    if not coords:
        raise ValueError(f"No protein atoms found after filtering: {path}")

    coord_array = np.asarray(coords, dtype=np.float32)
    if not np.isfinite(coord_array).all():
        raise ValueError(f"Protein coordinates contain NaN or inf: {path}")

    return ProteinAtoms(
        atom_names=atom_names,
        elements=elements,
        atomic_numbers=atomic_numbers,
        coords=coord_array,
        chain_ids=chain_ids,
        residue_ids=residue_ids,
        insertion_codes=insertion_codes,
        residue_names=residue_names,
        is_backbone=np.asarray(is_backbone, dtype=bool),
        is_hetero=np.asarray(is_hetero, dtype=bool),
        occupancy=np.asarray(occupancies, dtype=np.float32),
        b_factor=np.asarray(b_factors, dtype=np.float32),
        warnings=warnings,
    )


def _select_altloc(atom: Any) -> Any:
    if not atom.is_disordered():
        return atom
    children = list(getattr(atom, "child_dict", {}).values())
    if not children:
        return atom
    return max(children, key=lambda child: float(child.get_occupancy() or 0.0))


def _normalize_element(raw_element: str, atom_name: str) -> str:
    element = (raw_element or "").strip()
    if len(element) == 1:
        return element.upper()
    if len(element) >= 2:
        return element[0].upper() + element[1:].lower()
    return _infer_element(atom_name)


def _infer_element(atom_name: str) -> str:
    stripped = "".join(ch for ch in atom_name.strip() if ch.isalpha())
    if not stripped:
        return ""
    if len(stripped) >= 2:
        candidate = stripped[:2][0].upper() + stripped[:2][1].lower()
        if candidate in ATOMIC_NUMBERS:
            return candidate
    return stripped[0].upper()


def _import_biopython() -> tuple[Any, Any, Any]:
    try:
        from Bio.PDB import MMCIFParser, PDBParser, is_aa
    except ImportError as exc:
        raise ImportError(
            "Biopython is required for protein reading. Create the conda env with environment.yml."
        ) from exc
    return PDBParser, MMCIFParser, is_aa

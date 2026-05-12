from __future__ import annotations

from pathlib import Path
from typing import Any


def read_generated_sdf(path: str | Path, *, remove_hs: bool = False) -> list[Any]:
    Chem = _import_rdkit()
    sdf_path = Path(path)
    if not sdf_path.exists():
        raise FileNotFoundError(f"Generated SDF not found: {sdf_path}")
    supplier = Chem.SDMolSupplier(str(sdf_path), sanitize=False, removeHs=remove_hs)
    return [mol for mol in supplier if mol is not None]


def write_sdf(molecules: list[Any], path: str | Path) -> None:
    Chem = _import_rdkit()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(output))
    try:
        for mol in molecules:
            writer.write(mol)
    finally:
        writer.close()


def standardize_generated_mol(mol: Any, *, largest_fragment: bool = True, sanitize: bool = False) -> tuple[Any | None, str]:
    Chem = _import_rdkit()
    try:
        work = Chem.Mol(mol)
        if largest_fragment:
            fragments = Chem.GetMolFrags(work, asMols=True, sanitizeFrags=False)
            if fragments:
                work = max(fragments, key=lambda candidate: candidate.GetNumHeavyAtoms())
        if sanitize:
            Chem.SanitizeMol(work)
        return work, "ok"
    except Exception as exc:
        return None, f"standardize_failed:{exc}"


def _import_rdkit() -> Any:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise ImportError("RDKit is required for generated ligand reading.") from exc
    return Chem

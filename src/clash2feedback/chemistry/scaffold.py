from __future__ import annotations

from typing import Any

from clash2feedback.data.schema import ScaffoldData


def get_murcko_scaffold_atom_indices(mol: Any) -> ScaffoldData:
    Chem, MurckoScaffold = _import_rdkit()
    try:
        scaffold_mol = MurckoScaffold.GetScaffoldForMol(mol)
    except Exception as exc:
        return _failed(f"scaffold_failed:{exc}")

    if scaffold_mol is None or scaffold_mol.GetNumAtoms() == 0:
        return _failed("scaffold_empty")

    match = mol.GetSubstructMatch(scaffold_mol)
    if not match:
        scaffold_query = Chem.MolFromSmarts(Chem.MolToSmarts(scaffold_mol))
        match = mol.GetSubstructMatch(scaffold_query) if scaffold_query is not None else ()
    if not match:
        return _failed("scaffold_mapping_failed")

    atom_indices = sorted(int(idx) for idx in match)
    if len(atom_indices) == mol.GetNumAtoms():
        return ScaffoldData(
            method="murcko",
            scaffold_smiles=Chem.MolToSmiles(scaffold_mol, canonical=True),
            atom_indices=atom_indices,
            num_atoms=len(atom_indices),
            num_heavy_atoms=_count_heavy_atoms(mol, atom_indices),
            success=False,
            failure_reason="scaffold_is_whole_ligand",
        )

    return ScaffoldData(
        method="murcko",
        scaffold_smiles=Chem.MolToSmiles(scaffold_mol, canonical=True),
        atom_indices=atom_indices,
        num_atoms=len(atom_indices),
        num_heavy_atoms=_count_heavy_atoms(mol, atom_indices),
        success=True,
        failure_reason=None,
    )


def validate_scaffold(
    mol: Any,
    scaffold: ScaffoldData,
    *,
    min_scaffold_atoms: int = 3,
) -> dict[str, Any]:
    fatal_errors: list[str] = []
    warnings: list[str] = []
    if not scaffold.success:
        fatal_errors.append(scaffold.failure_reason or "scaffold_failed")
    if scaffold.num_atoms < min_scaffold_atoms:
        fatal_errors.append("scaffold_too_small")
    if scaffold.num_atoms >= mol.GetNumAtoms():
        fatal_errors.append("scaffold_is_whole_ligand")
    if scaffold.num_heavy_atoms < min_scaffold_atoms:
        warnings.append("scaffold_heavy_atoms_small")
    return {
        "ok": not fatal_errors,
        "fatal_errors": _dedupe(fatal_errors),
        "warnings": warnings,
    }


def _count_heavy_atoms(mol: Any, atom_indices: list[int]) -> int:
    return sum(1 for idx in atom_indices if mol.GetAtomWithIdx(idx).GetAtomicNum() > 1)


def _failed(reason: str) -> ScaffoldData:
    return ScaffoldData(
        method="murcko",
        scaffold_smiles="",
        atom_indices=[],
        num_atoms=0,
        num_heavy_atoms=0,
        success=False,
        failure_reason=reason,
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _import_rdkit() -> tuple[Any, Any]:
    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
    except ImportError as exc:
        raise ImportError(
            "RDKit is required for scaffold extraction. Create the conda env with environment.yml."
        ) from exc
    return Chem, MurckoScaffold

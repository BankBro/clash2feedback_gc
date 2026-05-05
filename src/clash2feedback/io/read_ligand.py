from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from clash2feedback.data.schema import LigandData


def read_ligand_sdf(
    ligand_path: str | Path,
    *,
    sanitize: bool = True,
    remove_hs: bool = False,
) -> Any:
    Chem = _import_rdkit()
    path = Path(ligand_path)
    if not path.exists():
        raise FileNotFoundError(f"Ligand file does not exist: {path}")

    supplier = Chem.SDMolSupplier(str(path), sanitize=False, removeHs=remove_hs)
    mol = next((candidate for candidate in supplier if candidate is not None), None)
    if mol is None:
        raise ValueError(f"No readable molecule found in SDF: {path}")

    for atom in mol.GetAtoms():
        atom.SetIntProp("orig_atom_idx", atom.GetIdx())

    if sanitize:
        Chem.SanitizeMol(mol)
    return mol


def mol_to_ligand_data(mol: Any, *, keep_molblock: bool = True) -> LigandData:
    Chem = _import_rdkit()
    if mol.GetNumConformers() == 0:
        coords = np.zeros((mol.GetNumAtoms(), 3), dtype=np.float32)
        has_3d = False
    else:
        conf = mol.GetConformer()
        coords = np.asarray(conf.GetPositions(), dtype=np.float32)
        has_3d = bool(conf.Is3D())

    elements = [atom.GetSymbol() for atom in mol.GetAtoms()]
    atomic_numbers = [int(atom.GetAtomicNum()) for atom in mol.GetAtoms()]
    formal_charges = [int(atom.GetFormalCharge()) for atom in mol.GetAtoms()]
    is_aromatic = [bool(atom.GetIsAromatic()) for atom in mol.GetAtoms()]
    hybridization = [str(atom.GetHybridization()) for atom in mol.GetAtoms()]
    chiral_tags = [str(atom.GetChiralTag()) for atom in mol.GetAtoms()]

    edge_index: list[list[int]] = [[], []]
    bond_order: list[float] = []
    bond_type: list[str] = []
    bond_is_aromatic: list[bool] = []
    is_rotatable: list[bool] = []
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        order = float(bond.GetBondTypeAsDouble())
        btype = str(bond.GetBondType())
        aromatic = bool(bond.GetIsAromatic())
        rotatable = _is_simple_rotatable_bond(bond)
        for src, dst in ((begin, end), (end, begin)):
            edge_index[0].append(src)
            edge_index[1].append(dst)
            bond_order.append(order)
            bond_type.append(btype)
            bond_is_aromatic.append(aromatic)
            is_rotatable.append(rotatable)

    canonical_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False)
    isomeric_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    inchi_key = _safe_inchi_key(Chem, mol)
    sanitize_ok = _safe_sanitize(Chem, mol)
    fragments = Chem.GetMolFrags(mol, sanitizeFrags=False)

    return LigandData(
        molblock=Chem.MolToMolBlock(mol) if keep_molblock else "",
        canonical_smiles=canonical_smiles,
        isomeric_smiles=isomeric_smiles,
        inchi_key=inchi_key,
        elements=elements,
        atomic_numbers=atomic_numbers,
        coords=coords,
        formal_charges=formal_charges,
        is_aromatic=is_aromatic,
        hybridization=hybridization,
        chiral_tags=chiral_tags,
        bonds={
            "edge_index": np.asarray(edge_index, dtype=np.int64),
            "bond_order": bond_order,
            "bond_type": bond_type,
            "is_aromatic": bond_is_aromatic,
            "is_rotatable": is_rotatable,
        },
        rdkit_sanitize_ok=sanitize_ok,
        num_fragments=len(fragments),
        has_3d_conformer=has_3d,
    )


def _is_simple_rotatable_bond(bond: Any) -> bool:
    return (
        str(bond.GetBondType()) == "SINGLE"
        and not bond.IsInRing()
        and bond.GetBeginAtom().GetAtomicNum() > 1
        and bond.GetEndAtom().GetAtomicNum() > 1
    )


def _safe_sanitize(Chem: Any, mol: Any) -> bool:
    try:
        copy = Chem.Mol(mol)
        Chem.SanitizeMol(copy)
        return True
    except Exception:
        return False


def _safe_inchi_key(Chem: Any, mol: Any) -> str | None:
    try:
        return Chem.MolToInchiKey(mol)
    except Exception:
        return None


def _import_rdkit() -> Any:
    try:
        from rdkit import Chem
    except ImportError as exc:
        raise ImportError(
            "RDKit is required for ligand reading. Create the conda env with environment.yml."
        ) from exc
    return Chem

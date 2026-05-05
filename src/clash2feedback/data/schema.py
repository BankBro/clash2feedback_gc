from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ATOMIC_NUMBERS: dict[str, int] = {
    "H": 1,
    "C": 6,
    "N": 7,
    "O": 8,
    "F": 9,
    "P": 15,
    "S": 16,
    "Cl": 17,
    "Br": 35,
    "I": 53,
}


@dataclass(frozen=True)
class RawComplex:
    complex_id: str
    protein_path: Path
    ligand_path: Path
    metadata: dict[str, Any]


@dataclass
class ProteinAtoms:
    atom_names: list[str]
    elements: list[str]
    atomic_numbers: list[int]
    coords: np.ndarray
    chain_ids: list[str]
    residue_ids: list[int]
    insertion_codes: list[str]
    residue_names: list[str]
    is_backbone: np.ndarray
    is_hetero: np.ndarray
    occupancy: np.ndarray | None = None
    b_factor: np.ndarray | None = None
    warnings: list[str] | None = None

    @property
    def num_atoms(self) -> int:
        return int(self.coords.shape[0])

    def residue_key(self, atom_idx: int) -> tuple[str, int, str, str]:
        return (
            self.chain_ids[atom_idx],
            int(self.residue_ids[atom_idx]),
            self.insertion_codes[atom_idx],
            self.residue_names[atom_idx],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_atoms": self.num_atoms,
            "atom_names": self.atom_names,
            "elements": self.elements,
            "atomic_numbers": self.atomic_numbers,
            "coords": self.coords.astype(np.float32, copy=False),
            "chain_ids": self.chain_ids,
            "residue_ids": self.residue_ids,
            "insertion_codes": self.insertion_codes,
            "residue_names": self.residue_names,
            "is_backbone": self.is_backbone.astype(bool, copy=False),
            "is_hetero": self.is_hetero.astype(bool, copy=False),
            "occupancy": self.occupancy,
            "b_factor": self.b_factor,
            "warnings": self.warnings or [],
        }


@dataclass
class LigandData:
    molblock: str
    canonical_smiles: str
    isomeric_smiles: str
    inchi_key: str | None
    elements: list[str]
    atomic_numbers: list[int]
    coords: np.ndarray
    formal_charges: list[int]
    is_aromatic: list[bool]
    hybridization: list[str]
    chiral_tags: list[str]
    bonds: dict[str, Any]
    rdkit_sanitize_ok: bool
    num_fragments: int
    has_3d_conformer: bool

    @property
    def num_atoms(self) -> int:
        return int(self.coords.shape[0])

    @property
    def num_heavy_atoms(self) -> int:
        return int(sum(atomic_number > 1 for atomic_number in self.atomic_numbers))

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_atoms": self.num_atoms,
            "num_heavy_atoms": self.num_heavy_atoms,
            "elements": self.elements,
            "atomic_numbers": self.atomic_numbers,
            "coords": self.coords.astype(np.float32, copy=False),
            "formal_charges": self.formal_charges,
            "is_aromatic": self.is_aromatic,
            "hybridization": self.hybridization,
            "chiral_tags": self.chiral_tags,
            "bonds": self.bonds,
            "canonical_smiles": self.canonical_smiles,
            "isomeric_smiles": self.isomeric_smiles,
            "inchi_key": self.inchi_key,
            "molblock": self.molblock,
            "rdkit_sanitize_ok": self.rdkit_sanitize_ok,
            "num_fragments": self.num_fragments,
            "has_3d_conformer": self.has_3d_conformer,
        }


@dataclass
class PocketData:
    cutoff_angstrom: float
    by_residue: bool
    protein_atom_indices: np.ndarray
    protein_residue_keys: list[tuple[str, int, str, str]]
    coords: np.ndarray
    elements: list[str]
    atomic_numbers: list[int]
    center: np.ndarray
    num_atoms_6A: int
    num_atoms_8A: int

    @property
    def num_pocket_atoms(self) -> int:
        return int(self.protein_atom_indices.shape[0])

    @property
    def num_pocket_residues(self) -> int:
        return len(self.protein_residue_keys)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": "distance_to_ligand",
            "cutoff_angstrom": float(self.cutoff_angstrom),
            "by_residue": bool(self.by_residue),
            "protein_atom_indices": self.protein_atom_indices.astype(np.int64, copy=False),
            "protein_residue_keys": self.protein_residue_keys,
            "coords": self.coords.astype(np.float32, copy=False),
            "elements": self.elements,
            "atomic_numbers": self.atomic_numbers,
            "center": self.center.astype(np.float32, copy=False),
            "num_pocket_atoms": self.num_pocket_atoms,
            "num_pocket_residues": self.num_pocket_residues,
            "num_atoms_6A": int(self.num_atoms_6A),
            "num_atoms_8A": int(self.num_atoms_8A),
        }


@dataclass
class ScaffoldData:
    method: str
    scaffold_smiles: str
    atom_indices: list[int]
    num_atoms: int
    num_heavy_atoms: int
    success: bool
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "scaffold_smiles": self.scaffold_smiles,
            "atom_indices": self.atom_indices,
            "num_atoms": int(self.num_atoms),
            "num_heavy_atoms": int(self.num_heavy_atoms),
            "success": bool(self.success),
            "failure_reason": self.failure_reason,
        }


@dataclass
class RGroupData:
    rgroup_id: str
    atom_indices: list[int]
    heavy_atom_indices: list[int]
    anchor_ligand_atom_idx: int | None
    anchor_scaffold_atom_idx: int | None
    anchor_rgroup_atom_idx: int | None
    anchor_bond_idx: int | None
    anchor_bond_order: float | None
    num_anchors: int
    is_single_anchor: bool
    rotatable_bond_indices: list[int]
    is_valid_for_phase0: bool
    failure_reason: str | None = None

    @property
    def num_atoms(self) -> int:
        return len(self.atom_indices)

    @property
    def num_heavy_atoms(self) -> int:
        return len(self.heavy_atom_indices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rgroup_id": self.rgroup_id,
            "atom_indices": self.atom_indices,
            "heavy_atom_indices": self.heavy_atom_indices,
            "num_atoms": self.num_atoms,
            "num_heavy_atoms": self.num_heavy_atoms,
            "anchor_ligand_atom_idx": self.anchor_ligand_atom_idx,
            "anchor_scaffold_atom_idx": self.anchor_scaffold_atom_idx,
            "anchor_rgroup_atom_idx": self.anchor_rgroup_atom_idx,
            "anchor_bond_idx": self.anchor_bond_idx,
            "anchor_bond_order": self.anchor_bond_order,
            "num_anchors": int(self.num_anchors),
            "is_single_anchor": bool(self.is_single_anchor),
            "rotatable_bond_indices": self.rotatable_bond_indices,
            "is_valid_for_phase0": bool(self.is_valid_for_phase0),
            "failure_reason": self.failure_reason,
        }

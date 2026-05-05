from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from clash2feedback.data.schema import RGroupData, ScaffoldData


def decompose_rgroups(
    mol: Any,
    scaffold: ScaffoldData,
    *,
    min_heavy_atoms: int = 2,
    max_heavy_atoms: int = 15,
    single_anchor_only: bool = True,
) -> list[RGroupData]:
    if not scaffold.success:
        return []

    scaffold_atoms = set(scaffold.atom_indices)
    candidate_atoms = set(range(mol.GetNumAtoms())) - scaffold_atoms
    components = _connected_components(mol, candidate_atoms)
    rgroups: list[RGroupData] = []
    for index, component in enumerate(components, start=1):
        atom_indices = sorted(component)
        heavy_atom_indices = [
            atom_idx for atom_idx in atom_indices if mol.GetAtomWithIdx(atom_idx).GetAtomicNum() > 1
        ]
        anchor_bonds = _anchor_bonds(mol, component, scaffold_atoms)
        num_anchors = len(anchor_bonds)
        is_single_anchor = num_anchors == 1
        failure_reason: str | None = None
        if num_anchors == 0:
            failure_reason = "rgroup_no_anchor"
        elif single_anchor_only and not is_single_anchor:
            failure_reason = "unsupported_multi_anchor"
        elif len(heavy_atom_indices) < min_heavy_atoms:
            failure_reason = "rgroup_too_small"
        elif len(heavy_atom_indices) > max_heavy_atoms:
            failure_reason = "rgroup_too_large"

        anchor = anchor_bonds[0] if is_single_anchor else None
        rgroups.append(
            RGroupData(
                rgroup_id=f"R{index}",
                atom_indices=atom_indices,
                heavy_atom_indices=heavy_atom_indices,
                anchor_ligand_atom_idx=anchor["scaffold_atom_idx"] if anchor else None,
                anchor_scaffold_atom_idx=anchor["scaffold_atom_idx"] if anchor else None,
                anchor_rgroup_atom_idx=anchor["rgroup_atom_idx"] if anchor else None,
                anchor_bond_idx=anchor["bond_idx"] if anchor else None,
                anchor_bond_order=anchor["bond_order"] if anchor else None,
                num_anchors=num_anchors,
                is_single_anchor=is_single_anchor,
                rotatable_bond_indices=_rotatable_bond_indices(mol, component, scaffold_atoms),
                is_valid_for_phase0=failure_reason is None,
                failure_reason=failure_reason,
            )
        )
    return rgroups


def build_ligand_masks(mol: Any, scaffold: ScaffoldData, rgroups: list[RGroupData]) -> dict[str, Any]:
    num_atoms = mol.GetNumAtoms()
    scaffold_mask = np.zeros(num_atoms, dtype=bool)
    for atom_idx in scaffold.atom_indices:
        scaffold_mask[atom_idx] = True

    ligand_is_rgroup = np.zeros(num_atoms, dtype=bool)
    ligand_rgroup_id: list[str | None] = [None] * num_atoms
    for rgroup in rgroups:
        for atom_idx in rgroup.atom_indices:
            ligand_is_rgroup[atom_idx] = True
            ligand_rgroup_id[atom_idx] = rgroup.rgroup_id

    heavy_atom_mask = np.asarray(
        [mol.GetAtomWithIdx(atom_idx).GetAtomicNum() > 1 for atom_idx in range(num_atoms)],
        dtype=bool,
    )
    return {
        "ligand_scaffold_mask": scaffold_mask,
        "ligand_rgroup_id": ligand_rgroup_id,
        "ligand_is_rgroup": ligand_is_rgroup,
        "heavy_atom_mask": heavy_atom_mask,
    }


def _connected_components(mol: Any, atom_indices: set[int]) -> list[set[int]]:
    adjacency: dict[int, set[int]] = {atom_idx: set() for atom_idx in atom_indices}
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        if begin in atom_indices and end in atom_indices:
            adjacency[begin].add(end)
            adjacency[end].add(begin)

    components: list[set[int]] = []
    unseen = set(atom_indices)
    while unseen:
        start = unseen.pop()
        component = {start}
        queue: deque[int] = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return sorted(components, key=lambda comp: min(comp))


def _anchor_bonds(mol: Any, component: set[int], scaffold_atoms: set[int]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        if begin in component and end in scaffold_atoms:
            rgroup_atom, scaffold_atom = begin, end
        elif end in component and begin in scaffold_atoms:
            rgroup_atom, scaffold_atom = end, begin
        else:
            continue
        anchors.append(
            {
                "bond_idx": int(bond.GetIdx()),
                "rgroup_atom_idx": rgroup_atom,
                "scaffold_atom_idx": scaffold_atom,
                "bond_order": float(bond.GetBondTypeAsDouble()),
            }
        )
    return anchors


def _rotatable_bond_indices(mol: Any, component: set[int], scaffold_atoms: set[int]) -> list[int]:
    relevant = component | scaffold_atoms
    result: list[int] = []
    for bond in mol.GetBonds():
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        touches_component = begin in component or end in component
        if (
            touches_component
            and begin in relevant
            and end in relevant
            and str(bond.GetBondType()) == "SINGLE"
            and not bond.IsInRing()
            and bond.GetBeginAtom().GetAtomicNum() > 1
            and bond.GetEndAtom().GetAtomicNum() > 1
        ):
            result.append(int(bond.GetIdx()))
    return result

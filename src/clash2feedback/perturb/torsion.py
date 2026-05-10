from __future__ import annotations

from collections import deque
from typing import Any

from clash2feedback.perturb.rotation import rotate_target_rgroup


def torsion_perturb_target_rgroup(
    sample: dict[str, Any],
    mol: Any,
    rgroup: dict[str, Any],
    angle_deg: float,
) -> dict[str, Any] | None:
    target_atoms = {int(idx) for idx in rgroup.get("atom_indices", [])}
    anchor = rgroup.get("anchor_rgroup_atom_idx")
    if anchor is None:
        return None
    anchor_idx = int(anchor)
    for bond_idx in rgroup.get("rotatable_bond_indices", []):
        bond = mol.GetBondWithIdx(int(bond_idx))
        begin = int(bond.GetBeginAtomIdx())
        end = int(bond.GetEndAtomIdx())
        if begin not in target_atoms or end not in target_atoms:
            continue
        moving = _side_away_from_anchor(mol, begin, end, anchor_idx)
        if moving and moving.issubset(target_atoms):
            scaffold_axis_atom, rgroup_axis_atom = begin, end
            if end in moving:
                scaffold_axis_atom, rgroup_axis_atom = begin, end
            else:
                scaffold_axis_atom, rgroup_axis_atom = end, begin
            return rotate_target_rgroup(
                sample,
                {
                    **rgroup,
                    "anchor_scaffold_atom_idx": scaffold_axis_atom,
                    "anchor_rgroup_atom_idx": rgroup_axis_atom,
                    "atom_indices": sorted(moving),
                },
                angle_deg,
                atom_indices=sorted(moving),
            )
    return None


def _side_away_from_anchor(mol: Any, begin: int, end: int, anchor_idx: int) -> set[int]:
    left = _component_without_bond(mol, begin, forbidden_neighbor=end)
    right = _component_without_bond(mol, end, forbidden_neighbor=begin)
    if anchor_idx in left and anchor_idx not in right:
        return right
    if anchor_idx in right and anchor_idx not in left:
        return left
    return set()


def _component_without_bond(mol: Any, start: int, *, forbidden_neighbor: int) -> set[int]:
    seen = {int(start)}
    queue: deque[int] = deque([int(start)])
    while queue:
        current = queue.popleft()
        atom = mol.GetAtomWithIdx(current)
        for neighbor in atom.GetNeighbors():
            next_idx = int(neighbor.GetIdx())
            if current == int(start) and next_idx == int(forbidden_neighbor):
                continue
            if next_idx in seen:
                continue
            seen.add(next_idx)
            queue.append(next_idx)
    return seen

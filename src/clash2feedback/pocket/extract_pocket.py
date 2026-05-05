from __future__ import annotations

import numpy as np

from clash2feedback.data.schema import LigandData, PocketData, ProteinAtoms


def extract_pocket_atoms(
    protein: ProteinAtoms,
    ligand: LigandData,
    *,
    cutoff_angstrom: float = 8.0,
    by_residue: bool = True,
    ligand_heavy_only: bool = True,
) -> PocketData:
    protein_coords = np.asarray(protein.coords, dtype=np.float32)
    ligand_coords = np.asarray(ligand.coords, dtype=np.float32)
    if ligand_heavy_only:
        ligand_mask = np.asarray([atomic_number > 1 for atomic_number in ligand.atomic_numbers], dtype=bool)
        ligand_coords = ligand_coords[ligand_mask]
    if ligand_coords.size == 0:
        raise ValueError("Ligand has no coordinates available for pocket extraction")

    min_distances = min_distances_to_ligand(protein_coords, ligand_coords)
    nearby_indices = set(np.where(min_distances <= cutoff_angstrom)[0].astype(int).tolist())
    num_atoms_6a = int(np.sum(min_distances <= 6.0))

    if by_residue and nearby_indices:
        residue_keys = {protein.residue_key(atom_idx) for atom_idx in nearby_indices}
        pocket_indices = [
            atom_idx
            for atom_idx in range(protein.num_atoms)
            if protein.residue_key(atom_idx) in residue_keys
        ]
    else:
        residue_keys = {protein.residue_key(atom_idx) for atom_idx in nearby_indices}
        pocket_indices = sorted(nearby_indices)

    pocket_array = np.asarray(sorted(pocket_indices), dtype=np.int64)
    residue_key_list = sorted(residue_keys, key=lambda item: (item[0], item[1], item[2], item[3]))
    return PocketData(
        cutoff_angstrom=float(cutoff_angstrom),
        by_residue=bool(by_residue),
        protein_atom_indices=pocket_array,
        protein_residue_keys=residue_key_list,
        coords=protein_coords[pocket_array] if pocket_array.size else np.zeros((0, 3), dtype=np.float32),
        elements=[protein.elements[idx] for idx in pocket_array.tolist()],
        atomic_numbers=[protein.atomic_numbers[idx] for idx in pocket_array.tolist()],
        center=np.asarray(ligand_coords.mean(axis=0), dtype=np.float32),
        num_atoms_6A=num_atoms_6a,
        num_atoms_8A=int(pocket_array.shape[0]),
    )


def min_distances_to_ligand(protein_coords: np.ndarray, ligand_coords: np.ndarray) -> np.ndarray:
    if protein_coords.size == 0 or ligand_coords.size == 0:
        return np.full((protein_coords.shape[0],), np.inf, dtype=np.float32)
    min_distances = np.full((protein_coords.shape[0],), np.inf, dtype=np.float32)
    chunk_size = 512
    for start in range(0, protein_coords.shape[0], chunk_size):
        stop = min(start + chunk_size, protein_coords.shape[0])
        diff = protein_coords[start:stop, None, :] - ligand_coords[None, :, :]
        distances = np.sqrt(np.sum(diff * diff, axis=2))
        min_distances[start:stop] = distances.min(axis=1)
    return min_distances

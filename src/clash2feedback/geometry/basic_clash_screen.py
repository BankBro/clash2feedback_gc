from __future__ import annotations

import numpy as np

from clash2feedback.data.schema import LigandData, PocketData, ProteinAtoms


def basic_original_clash_screen(
    protein: ProteinAtoms,
    ligand: LigandData,
    pocket: PocketData,
    *,
    min_distance_threshold: float = 1.2,
    max_obvious_clash_pairs: int = 0,
) -> dict[str, float | int | bool]:
    ligand_heavy_mask = np.asarray([atomic_number > 1 for atomic_number in ligand.atomic_numbers], dtype=bool)
    ligand_coords = np.asarray(ligand.coords, dtype=np.float32)[ligand_heavy_mask]
    pocket_indices = np.asarray(pocket.protein_atom_indices, dtype=np.int64)
    protein_heavy_mask = np.asarray([atomic_number > 1 for atomic_number in protein.atomic_numbers], dtype=bool)
    pocket_heavy_indices = pocket_indices[protein_heavy_mask[pocket_indices]] if pocket_indices.size else pocket_indices
    pocket_coords = np.asarray(protein.coords, dtype=np.float32)[pocket_heavy_indices]

    if ligand_coords.size == 0 or pocket_coords.size == 0:
        return {
            "min_ligand_protein_distance": float("inf"),
            "num_obvious_clash_pairs": 0,
            "num_pairs_below_1_0": 0,
            "num_pairs_below_1_2": 0,
            "num_pairs_below_1_5": 0,
            "basic_clash_screen_pass": False,
        }

    min_distance = float("inf")
    clash_pairs = 0
    pairs_below_1_0 = 0
    pairs_below_1_2 = 0
    pairs_below_1_5 = 0
    chunk_size = 256
    for start in range(0, pocket_coords.shape[0], chunk_size):
        stop = min(start + chunk_size, pocket_coords.shape[0])
        diff = pocket_coords[start:stop, None, :] - ligand_coords[None, :, :]
        distances = np.sqrt(np.sum(diff * diff, axis=2))
        min_distance = min(min_distance, float(distances.min()))
        clash_pairs += int(np.sum(distances < min_distance_threshold))
        pairs_below_1_0 += int(np.sum(distances < 1.0))
        pairs_below_1_2 += int(np.sum(distances < 1.2))
        pairs_below_1_5 += int(np.sum(distances < 1.5))

    return {
        "min_ligand_protein_distance": min_distance,
        "num_obvious_clash_pairs": clash_pairs,
        "num_pairs_below_1_0": pairs_below_1_0,
        "num_pairs_below_1_2": pairs_below_1_2,
        "num_pairs_below_1_5": pairs_below_1_5,
        "basic_clash_screen_pass": clash_pairs <= max_obvious_clash_pairs,
    }

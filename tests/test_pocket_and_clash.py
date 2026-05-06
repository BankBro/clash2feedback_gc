import numpy as np

from clash2feedback.data.schema import LigandData, PocketData, ProteinAtoms
from clash2feedback.geometry.basic_clash_screen import basic_original_clash_screen
from clash2feedback.pocket.extract_pocket import extract_pocket_atoms, min_distances_to_ligand


def _protein() -> ProteinAtoms:
    return ProteinAtoms(
        atom_names=["CA", "CB", "CA", "CB"],
        elements=["C", "C", "C", "C"],
        atomic_numbers=[6, 6, 6, 6],
        coords=np.asarray([[0, 0, 0], [0, 1, 0], [20, 0, 0], [20, 1, 0]], dtype=np.float32),
        chain_ids=["A", "A", "A", "A"],
        residue_ids=[1, 1, 2, 2],
        insertion_codes=["", "", "", ""],
        residue_names=["ALA", "ALA", "GLY", "GLY"],
        is_backbone=np.asarray([True, False, True, False]),
        is_hetero=np.asarray([False, False, False, False]),
    )


def _ligand(coords: np.ndarray) -> LigandData:
    return LigandData(
        molblock="",
        canonical_smiles="CC",
        isomeric_smiles="CC",
        inchi_key=None,
        elements=["C", "C"],
        atomic_numbers=[6, 6],
        coords=coords.astype(np.float32),
        formal_charges=[0, 0],
        is_aromatic=[False, False],
        hybridization=["SP3", "SP3"],
        chiral_tags=["CHI_UNSPECIFIED", "CHI_UNSPECIFIED"],
        bonds={"edge_index": np.zeros((2, 0), dtype=np.int64)},
        rdkit_sanitize_ok=True,
        num_fragments=1,
        has_3d_conformer=True,
    )


def test_min_distances_to_ligand() -> None:
    protein_coords = np.asarray([[0, 0, 0], [3, 0, 0]], dtype=np.float32)
    ligand_coords = np.asarray([[1, 0, 0]], dtype=np.float32)
    distances = min_distances_to_ligand(protein_coords, ligand_coords)
    assert np.allclose(distances, [1.0, 2.0])


def test_extract_pocket_expands_to_residue() -> None:
    pocket = extract_pocket_atoms(_protein(), _ligand(np.asarray([[0.5, 0, 0], [0.5, 1, 0]])), cutoff_angstrom=2.0)
    assert pocket.num_pocket_atoms == 2
    assert pocket.num_pocket_residues == 1
    assert pocket.protein_residue_keys == [("A", 1, "", "ALA")]


def test_basic_clash_screen_counts_obvious_pairs() -> None:
    protein = _protein()
    ligand = _ligand(np.asarray([[0.2, 0, 0], [5, 5, 5]], dtype=np.float32))
    pocket = PocketData(
        cutoff_angstrom=8.0,
        by_residue=True,
        protein_atom_indices=np.asarray([0, 1], dtype=np.int64),
        protein_residue_keys=[("A", 1, "", "ALA")],
        coords=protein.coords[[0, 1]],
        elements=["C", "C"],
        atomic_numbers=[6, 6],
        center=np.asarray([2.6, 2.5, 2.5], dtype=np.float32),
        num_atoms_6A=2,
        num_atoms_8A=2,
    )
    result = basic_original_clash_screen(
        protein,
        ligand,
        pocket,
        min_distance_threshold=0.5,
        max_obvious_clash_pairs=0,
    )
    assert result["num_obvious_clash_pairs"] == 1
    assert result["num_pairs_below_1_0"] == 1
    assert result["num_pairs_below_1_2"] == 2
    assert result["num_pairs_below_1_5"] == 2
    assert result["basic_clash_screen_pass"] is False

import numpy as np

from clash2feedback.geometry.clash import detect_clashes


def _sample(protein_coords: np.ndarray, pocket_indices: list[int] | None = None) -> dict:
    pocket = np.asarray(pocket_indices if pocket_indices is not None else list(range(len(protein_coords))), dtype=np.int64)
    return {
        "sample_id": "mock_complex",
        "complex_id": "mock_complex",
        "metadata": {},
        "protein": {
            "num_atoms": int(len(protein_coords)),
            "elements": ["C"] * len(protein_coords),
            "atomic_numbers": [6] * len(protein_coords),
            "coords": protein_coords.astype(np.float32),
            "chain_ids": ["A"] * len(protein_coords),
            "residue_ids": list(range(1, len(protein_coords) + 1)),
            "insertion_codes": [""] * len(protein_coords),
            "residue_names": ["ALA"] * len(protein_coords),
            "is_hetero": np.zeros(len(protein_coords), dtype=bool),
        },
        "ligand": {
            "num_atoms": 2,
            "elements": ["C", "C"],
            "atomic_numbers": [6, 6],
            "coords": np.asarray([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float32),
        },
        "pocket": {"protein_atom_indices": pocket},
        "scaffold": {"atom_indices": [1]},
        "rgroups": [{"rgroup_id": "R1", "atom_indices": [0], "heavy_atom_indices": [0], "is_valid_for_phase0": True}],
        "masks": {
            "ligand_scaffold_mask": np.asarray([False, True]),
            "ligand_rgroup_id": ["R1", None],
            "ligand_is_rgroup": np.asarray([True, False]),
            "heavy_atom_mask": np.asarray([True, True]),
        },
    }


def test_far_atoms_have_no_clash() -> None:
    report = detect_clashes(_sample(np.asarray([[5.0, 0.0, 0.0]], dtype=np.float32)))
    assert report["num_clash_pairs"] == 0
    assert report["total_clash_score"] == 0.0


def test_near_atoms_have_clash_depth() -> None:
    report = detect_clashes(_sample(np.asarray([[2.5, 0.0, 0.0]], dtype=np.float32)))
    assert report["num_clash_pairs"] == 1
    assert report["num_severe_clash_pairs"] == 1
    assert report["clash_pairs"][0]["clash_depth"] > 0.0
    assert report["clash_pairs"][0]["ligand_region"] == "R1"


def test_receptor_scope_controls_protein_atoms() -> None:
    sample = _sample(
        np.asarray([[2.5, 0.0, 0.0], [2.6, 0.0, 0.0]], dtype=np.float32),
        pocket_indices=[0],
    )
    pocket_report = detect_clashes(sample, receptor_scope="phase0_pocket8")
    all_atom_report = detect_clashes(sample, receptor_scope="pocket10_all_atoms")
    assert pocket_report["num_clash_pairs"] == 1
    assert all_atom_report["num_clash_pairs"] == 2


def test_severe_threshold_is_applied() -> None:
    report = detect_clashes(
        _sample(np.asarray([[2.5, 0.0, 0.0]], dtype=np.float32)),
        severe_depth_threshold_angstrom=0.6,
    )
    assert report["num_clash_pairs"] == 1
    assert report["num_severe_clash_pairs"] == 0


def test_unsupported_ligand_element_is_reported() -> None:
    sample = _sample(np.asarray([[2.5, 0.0, 0.0]], dtype=np.float32))
    sample["ligand"]["elements"][0] = "Na"
    sample["ligand"]["atomic_numbers"][0] = 11
    report = detect_clashes(sample)
    assert report["analysis_status"] == "unsupported_chemistry"
    assert any("unsupported_metal" in reason for reason in report["unsupported_reasons"])


def test_covalent_ligand_metadata_is_unsupported() -> None:
    sample = _sample(np.asarray([[2.5, 0.0, 0.0]], dtype=np.float32))
    sample["metadata"]["is_covalent_ligand"] = True
    report = detect_clashes(sample)
    assert report["analysis_status"] == "unsupported_chemistry"
    assert report["num_clash_pairs"] == 0
    assert "unsupported_covalent_ligand" in report["unsupported_reasons"]

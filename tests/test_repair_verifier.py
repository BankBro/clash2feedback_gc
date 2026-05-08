import numpy as np

from clash2feedback.verifier.repair_verifier import verify_repair


def _sample() -> dict:
    return {
        "sample_id": "mock_complex",
        "metadata": {},
        "protein": {
            "num_atoms": 1,
            "elements": ["C"],
            "atomic_numbers": [6],
            "coords": np.asarray([[5.0, 0.0, 0.0]], dtype=np.float32),
            "chain_ids": ["A"],
            "residue_ids": [1],
            "insertion_codes": [""],
            "residue_names": ["ALA"],
            "is_hetero": np.asarray([False]),
        },
        "ligand": {
            "num_atoms": 3,
            "elements": ["C", "C", "C"],
            "atomic_numbers": [6, 6, 6],
            "coords": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float32),
        },
        "pocket": {"protein_atom_indices": np.asarray([0], dtype=np.int64)},
        "scaffold": {"atom_indices": [0, 1]},
        "rgroups": [{"rgroup_id": "R1", "atom_indices": [2], "heavy_atom_indices": [2], "is_valid_for_phase0": True}],
        "masks": {
            "ligand_scaffold_mask": np.asarray([True, True, False]),
            "ligand_rgroup_id": [None, None, "R1"],
            "ligand_is_rgroup": np.asarray([False, False, True]),
            "heavy_atom_mask": np.asarray([True, True, True]),
        },
    }


def _config() -> dict:
    return {
        "detector": {
            "default_old_scope": "phase0_pocket8",
            "default_new_scope": "pocket10_all_atoms",
            "delta_angstrom": 0.4,
            "severe_depth_threshold_angstrom": 0.4,
        },
        "verifier": {
            "old_clash_resolved_ratio": 0.1,
            "scaffold_rmsd_threshold": 0.5,
            "non_edit_rmsd_threshold": 0.8,
            "edit_region_outside_change_fraction": 0.2,
            "pocket_retention_min_contacts": None,
        },
    }


def test_clean_vs_clean_passes() -> None:
    sample = _sample()
    coords = sample["ligand"]["coords"]
    result = verify_repair(sample, coords, coords, edit_region=None, config=_config())
    assert result["repair_pass"] is True
    assert result["old_clash_resolved"] is True
    assert result["no_new_severe_clash"] is True


def test_repaired_coords_with_new_clash_fail() -> None:
    sample = _sample()
    failed = sample["ligand"]["coords"]
    repaired = failed.copy()
    repaired[2] = np.asarray([2.5, 0.0, 0.0], dtype=np.float32)
    result = verify_repair(sample, failed, repaired, edit_region="R1", config=_config())
    assert result["repair_pass"] is False
    assert result["no_new_severe_clash"] is False
    assert "new_severe_clash" in result["failure_reasons"]


def test_scaffold_drift_fails() -> None:
    sample = _sample()
    failed = sample["ligand"]["coords"]
    repaired = failed.copy()
    repaired[0] += np.asarray([1.0, 0.0, 0.0], dtype=np.float32)
    result = verify_repair(sample, failed, repaired, edit_region="R1", config=_config())
    assert result["repair_pass"] is False
    assert result["scaffold_stable"] is False
    assert "scaffold_drift" in result["failure_reasons"]


def test_non_edit_drift_fails() -> None:
    sample = _sample()
    failed = sample["ligand"]["coords"]
    repaired = failed.copy()
    repaired[1] += np.asarray([1.5, 0.0, 0.0], dtype=np.float32)
    result = verify_repair(sample, failed, repaired, edit_region="R1", config=_config())
    assert result["repair_pass"] is False
    assert result["non_edit_stable"] is False
    assert "non_edit_drift" in result["failure_reasons"]

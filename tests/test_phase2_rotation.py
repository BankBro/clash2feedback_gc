import numpy as np

from clash2feedback.perturb.rotation import rotate_target_rgroup


def _sample() -> dict:
    return {
        "sample_id": "mock",
        "ligand": {
            "coords": np.asarray(
                [
                    [0.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [1.0, 1.0, 0.0],
                    [0.0, 2.0, 0.0],
                ],
                dtype=np.float32,
            )
        },
    }


def _rgroup() -> dict:
    return {
        "rgroup_id": "R1",
        "atom_indices": [1, 2],
        "heavy_atom_indices": [1, 2],
        "anchor_scaffold_atom_idx": 0,
        "anchor_rgroup_atom_idx": 1,
        "anchor_bond_idx": 0,
    }


def test_rotate_only_target_rgroup() -> None:
    sample = _sample()
    result = rotate_target_rgroup(sample, _rgroup(), 90)
    failed = result["failed_coords"]
    assert np.allclose(failed[0], sample["ligand"]["coords"][0])
    assert np.allclose(failed[3], sample["ligand"]["coords"][3])
    assert not np.allclose(failed[2], sample["ligand"]["coords"][2])


def test_scaffold_and_anchor_bond_preserved_after_rotation() -> None:
    sample = _sample()
    result = rotate_target_rgroup(sample, _rgroup(), 180)
    original = sample["ligand"]["coords"]
    failed = result["failed_coords"]
    assert np.allclose(failed[0], original[0])
    assert np.allclose(failed[1], original[1])
    assert np.isclose(np.linalg.norm(original[0] - original[1]), np.linalg.norm(failed[0] - failed[1]))


def test_non_target_rgroups_unchanged() -> None:
    sample = _sample()
    failed = rotate_target_rgroup(sample, _rgroup(), 120)["failed_coords"]
    assert np.allclose(failed[3], sample["ligand"]["coords"][3])

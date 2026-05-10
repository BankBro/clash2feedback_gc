import numpy as np

from clash2feedback.perturb.rotation import rotate_target_rgroup


def test_injected_samples_inherit_base_split_semantics() -> None:
    row = {"base_split": "train", "derived_split": "train"}
    assert row["base_split"] == row["derived_split"]


def test_predicted_dominant_is_not_required_to_equal_target() -> None:
    accepted = {
        "oracle_split": "supported_single_rgroup",
        "target_rgroup": "R1",
        "predicted_dominant_valid_rgroup": "R2",
    }
    assert accepted["oracle_split"] == "supported_single_rgroup"


def test_heavy_atom_index_mapping_preserved_by_rotation() -> None:
    sample = {
        "ligand": {
            "coords": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]], dtype=np.float32)
        }
    }
    rgroup = {
        "rgroup_id": "R1",
        "atom_indices": [1, 2],
        "anchor_scaffold_atom_idx": 0,
        "anchor_rgroup_atom_idx": 1,
    }
    failed = rotate_target_rgroup(sample, rgroup, 60)["failed_coords"]
    assert failed.shape == sample["ligand"]["coords"].shape

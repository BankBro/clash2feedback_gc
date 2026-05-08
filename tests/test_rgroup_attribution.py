import numpy as np

from clash2feedback.geometry.rgroup_attribution import attribute_clashes_to_rgroups


def _sample() -> dict:
    return {
        "sample_id": "mock_complex",
        "ligand": {
            "num_atoms": 4,
            "atomic_numbers": [6, 6, 6, 6],
            "coords": np.zeros((4, 3), dtype=np.float32),
        },
        "scaffold": {"atom_indices": [0]},
        "rgroups": [
            {"rgroup_id": "R1", "atom_indices": [1], "heavy_atom_indices": [1], "is_valid_for_phase0": True},
            {"rgroup_id": "R2", "atom_indices": [2], "heavy_atom_indices": [2], "is_valid_for_phase0": True},
            {"rgroup_id": "R3", "atom_indices": [3], "heavy_atom_indices": [3], "is_valid_for_phase0": True},
        ],
        "masks": {
            "ligand_scaffold_mask": np.asarray([True, False, False, False]),
            "ligand_rgroup_id": [None, "R1", "R2", "R3"],
            "ligand_is_rgroup": np.asarray([False, True, True, True]),
            "heavy_atom_mask": np.asarray([True, True, True, True]),
        },
    }


def _pair(ligand_atom_idx: int, depth: float, region: str) -> dict:
    return {
        "ligand_atom_idx": ligand_atom_idx,
        "protein_atom_idx": 0,
        "protein_atom_position": 0,
        "ligand_element": "C",
        "protein_element": "C",
        "distance": 2.0,
        "vdw_sum": 3.4,
        "clash_depth": depth,
        "is_severe": depth >= 0.4,
        "ligand_region": region,
        "protein_residue_key": "A:1::ALA",
    }


def _report(pairs: list[dict], severe_count: int | None = None) -> dict:
    return {
        "sample_id": "mock_complex",
        "num_severe_clash_pairs": sum(pair["is_severe"] for pair in pairs) if severe_count is None else severe_count,
        "clash_pairs": pairs,
        "unsupported_reasons": [],
    }


def test_single_rgroup_dominant() -> None:
    attr = attribute_clashes_to_rgroups(_sample(), _report([_pair(2, 2.0, "R2"), _pair(1, 0.5, "R1")]))
    assert attr["failure_type"] == "single_rgroup_clash"
    assert attr["dominant_region"] == "R2"
    assert attr["recommended_action"] == "local_rgroup_repair"


def test_scaffold_clash_rejects() -> None:
    attr = attribute_clashes_to_rgroups(_sample(), _report([_pair(0, 2.0, "scaffold"), _pair(2, 1.0, "R2")]))
    assert attr["failure_type"] == "scaffold_clash"
    assert attr["recommended_action"] == "reject"


def test_multiple_regions_are_not_forced_to_single_rgroup() -> None:
    attr = attribute_clashes_to_rgroups(_sample(), _report([_pair(1, 1.0, "R1"), _pair(2, 0.9, "R2")]))
    assert attr["failure_type"] in {"ambiguous_region_clash", "multi_region_clash"}
    assert attr["recommended_action"] in {"reject_or_expand_mask", "reject"}


def test_no_severe_clash_reports_no_clash() -> None:
    attr = attribute_clashes_to_rgroups(_sample(), _report([], severe_count=0))
    assert attr["failure_type"] == "no_clash"
    assert attr["dominant_region"] == ""
    assert attr["dominant_ratio"] == 0.0

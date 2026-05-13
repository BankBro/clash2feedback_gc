from clash2feedback.feedback.mask_seed import (
    build_mask_bundle,
    choose_size_matched_random_rgroup,
    phase2_set_membership,
    target_in_top_n,
)


def _sample() -> dict:
    return {
        "ligand": {"num_atoms": 8, "atomic_numbers": [6, 6, 6, 6, 6, 6, 6, 6]},
        "rgroups": [
            {
                "rgroup_id": "R1",
                "atom_indices": [4, 5],
                "heavy_atom_indices": [4, 5],
                "anchor_scaffold_atom_idx": 1,
                "anchor_rgroup_atom_idx": 4,
                "anchor_bond_idx": 3,
                "is_valid_for_phase0": True,
                "is_single_anchor": True,
            },
            {
                "rgroup_id": "R2",
                "atom_indices": [6, 7],
                "heavy_atom_indices": [6, 7],
                "anchor_scaffold_atom_idx": 2,
                "anchor_rgroup_atom_idx": 6,
                "anchor_bond_idx": 4,
                "is_valid_for_phase0": True,
                "is_single_anchor": True,
            },
            {
                "rgroup_id": "R3",
                "atom_indices": [3],
                "heavy_atom_indices": [3],
                "anchor_scaffold_atom_idx": 0,
                "anchor_rgroup_atom_idx": 3,
                "anchor_bond_idx": 2,
                "is_valid_for_phase0": False,
                "is_single_anchor": True,
            },
        ],
    }


def test_mask_bundle_uses_entire_rgroup_and_keeps_complement() -> None:
    bundle = build_mask_bundle(_sample(), "R1")

    assert bundle["available"] is True
    assert bundle["atom_indices"] == [4, 5]
    assert bundle["keep_atom_indices"] == [0, 1, 2, 3, 6, 7]
    assert bundle["anchor_scaffold_atom_idx"] == 1
    assert bundle["anchor_rgroup_atom_idx"] not in bundle["atom_indices"] or bundle["anchor_rgroup_atom_idx"] == 4


def test_random_mask_excludes_oracle_and_predicted_when_possible() -> None:
    random_rgroup, reason = choose_size_matched_random_rgroup(
        _sample(),
        oracle_rgroup_id="R1",
        predicted_rgroup_id="R1",
        seed=20260513,
        case_id="case_000001",
    )

    assert random_rgroup == "R2"
    assert reason == "primary_exclude_oracle_and_predicted"


def test_random_mask_fallback_does_not_reuse_oracle() -> None:
    sample = _sample()
    sample["rgroups"] = [sample["rgroups"][0]]

    random_rgroup, reason = choose_size_matched_random_rgroup(
        sample,
        oracle_rgroup_id="R1",
        predicted_rgroup_id="R1",
        seed=20260513,
        case_id="case_000001",
    )

    assert random_rgroup == ""
    assert reason == "no_non_oracle_valid_single_anchor_rgroup"


def test_set_membership_keeps_s1_free_of_target_ratio_gate() -> None:
    row = {
        "ligand_valid": True,
        "ligand_internal_severe_clash_count": 0,
        "target_num_severe_pairs": 1,
        "scaffold_num_severe_pairs": 0,
        "non_target_num_severe_pairs": 0,
        "max_clash_depth": 1.0,
        "target_score_ratio_valid": 0.1,
        "oracle_split": "ambiguous_region",
    }

    flags = phase2_set_membership(row, max_depth=1.5)

    assert flags["set_membership_s1"] is True
    assert flags["set_membership_s2"] is False


def test_top3_is_construction_consistency_helper() -> None:
    top = '[{"region": "R2", "score": 3.0}, {"region": "R1", "score": 2.0}]'
    assert target_in_top_n(top, "R1", n=3) is True
    assert target_in_top_n(top, "R3", n=3) is False

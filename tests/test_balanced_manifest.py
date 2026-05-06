from __future__ import annotations

import pandas as pd

from clash2feedback.data.balanced_manifest import make_balanced_selection


def test_balanced_selection_caps_each_target_and_keeps_usable_only() -> None:
    rows = []
    for target, count in [("target_a", 7), ("target_b", 6), ("target_c", 3)]:
        for idx in range(count):
            rows.append(
                {
                    "sample_id": f"{target}_{idx}",
                    "complex_id": f"{target}_{idx}",
                    "phase0_usable": True,
                    "target_id": target,
                    "split_group": target,
                    "ligand_heavy_atoms": 20 + idx,
                    "num_pocket_atoms_8A": 100 + idx,
                    "num_valid_rgroups": 2,
                }
            )
    rows.append(
        {
            "sample_id": "target_a_bad",
            "complex_id": "target_a_bad",
            "phase0_usable": False,
            "target_id": "target_a",
            "split_group": "target_a",
            "ligand_heavy_atoms": 20,
            "num_pocket_atoms_8A": 100,
            "num_valid_rgroups": 2,
        }
    )
    result = make_balanced_selection(
        pd.DataFrame(rows),
        pd.DataFrame(),
        max_samples=30,
        min_samples=5,
        max_per_target=5,
        seed=20260504,
    )

    assert result.actual_samples == 13
    assert result.selected["balanced_target"].value_counts().max() == 5
    assert "target_a_bad" not in set(result.selected["sample_id"])
    assert "无法满 30" in result.reason


def test_balanced_selection_prioritizes_manual_pass_and_excludes_fail() -> None:
    manifest = pd.DataFrame(
        {
            "sample_id": ["sample_pass", "sample_unchecked", "sample_fail"],
            "complex_id": ["sample_pass", "sample_unchecked", "sample_fail"],
            "phase0_usable": [True, True, True],
            "target_id": ["target_a", "target_a", "target_a"],
            "split_group": ["target_a", "target_a", "target_a"],
            "ligand_heavy_atoms": [30, 20, 10],
            "num_pocket_atoms_8A": [120, 130, 140],
            "num_valid_rgroups": [3, 2, 2],
        }
    )
    visual = pd.DataFrame(
        {
            "sample_id": ["sample_pass", "sample_unchecked", "sample_fail"],
            "manual_check_status": ["pass", "unchecked", "fail"],
            "recommended_check_priority": ["low", "high", "high"],
        }
    )

    result = make_balanced_selection(manifest, visual, max_samples=2, min_samples=1, max_per_target=2)

    assert result.selected["sample_id"].tolist()[0] == "sample_pass"
    assert "sample_fail" not in set(result.selected["sample_id"])

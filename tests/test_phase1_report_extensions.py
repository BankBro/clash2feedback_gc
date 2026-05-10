from pathlib import Path
import importlib.util

import pandas as pd


def _phase1_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "phase1_check_clashes.py"
    spec = importlib.util.spec_from_file_location("phase1_check_clashes", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset_name": "clean",
                "sample_id": "s1",
                "receptor_scope": "phase0_pocket8",
                "delta_angstrom": 0.4,
                "num_clash_pairs": 1,
                "num_severe_clash_pairs": 0,
                "total_clash_score": 0.1,
                "max_clash_depth": 0.2,
            },
            {
                "dataset_name": "clean",
                "sample_id": "s1",
                "receptor_scope": "pocket10_all_atoms",
                "delta_angstrom": 0.4,
                "num_clash_pairs": 2,
                "num_severe_clash_pairs": 0,
                "total_clash_score": 0.2,
                "max_clash_depth": 0.3,
            },
            {
                "dataset_name": "clean",
                "sample_id": "s2",
                "receptor_scope": "phase0_pocket8",
                "delta_angstrom": 0.3,
                "num_clash_pairs": 1,
                "num_severe_clash_pairs": 1,
                "total_clash_score": 0.5,
                "max_clash_depth": 0.6,
                "dominant_region": "R1",
                "dominant_ratio_all_regions": 0.6,
                "dominant_valid_rgroup": "R1",
                "dominant_ratio_valid_rgroups": 1.0,
                "failure_type": "ambiguous_region_clash",
                "top_regions_json": "[]",
                "top_clash_pairs_json": "[]",
            },
        ]
    )


def test_nonsevere_contact_stats_counts_mild_pairs() -> None:
    module = _phase1_module()
    stats = module._nonsevere_contact_stats(_rows())
    row = stats[(stats["dataset_name"] == "clean") & (stats["delta_angstrom"] == 0.4)].iloc[0]
    assert int(row["num_samples_with_nonsevere_clash_pair"]) == 1


def test_scope_comparison_reports_differences() -> None:
    module = _phase1_module()
    comparison = module._scope_comparison(_rows())
    assert len(comparison) == 1
    assert bool(comparison.loc[0, "scope_result_same"]) is False


def test_strict_delta_false_positive_cases_filters_below_default_delta() -> None:
    module = _phase1_module()
    rows = _rows()
    cases = module._strict_delta_false_positive_cases(rows, pd.DataFrame(), default_delta=0.4)
    assert len(cases) == 1
    assert cases.loc[0, "sample_id"] == "s2"

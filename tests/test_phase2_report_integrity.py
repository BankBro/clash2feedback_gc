import json
from pathlib import Path

import pandas as pd
import pytest


REPORT_ROOT = Path(__file__).resolve().parents[1] / "reports" / "phase2_injection"


pytestmark = pytest.mark.skipif(not REPORT_ROOT.exists(), reason="phase2 reports are not available")


def test_phase2_summary_and_delta_report_integrity() -> None:
    summary_path = REPORT_ROOT / "summary.json"
    delta_path = REPORT_ROOT / "delta_sensitivity.csv"
    if not summary_path.exists() or not delta_path.exists():
        pytest.skip("phase2 summary or delta report is not available")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    delta = pd.read_csv(delta_path)

    assert summary["phase2_acceptance_status"] == "complete"
    assert int(summary["num_accepted_supported"]) > 0
    assert all(str(column).strip() for column in delta.columns)


def test_phase2_supported_cases_preserve_main_gates() -> None:
    path = REPORT_ROOT / "supported_single_rgroup_cases.csv"
    if not path.exists():
        pytest.skip("phase2 supported cases report is not available")

    df = pd.read_csv(path)

    assert not df.empty
    assert int(df["non_target_num_severe_pairs"].max()) == 0
    assert int(df["scaffold_num_severe_pairs"].max()) == 0
    assert bool((df["base_split"] == df["derived_split"]).all())


def test_phase2_visual_qc_cases_cover_required_groups() -> None:
    path = REPORT_ROOT / "visual_qc_cases.csv"
    if not path.exists():
        pytest.skip("phase2 visual QC cases report is not available")

    df = pd.read_csv(path)
    splits = set(df["oracle_split"])

    assert "supported_single_rgroup" in splits
    assert "invalid_conformer" in splits
    assert {"global_pose_failure", "ambiguous_region"} & splits
    assert {"near_miss_contact", "duplicate_removed"} & splits

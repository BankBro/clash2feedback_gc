from pathlib import Path
import importlib.util

import pandas as pd


def _phase2_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "phase2_inject_artificial_clashes.py"
    spec = importlib.util.spec_from_file_location("phase2_inject_artificial_clashes", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_dataframe_has_required_columns() -> None:
    module = _phase2_module()
    df = module._manifest_dataframe([{"case_id": "case_000001", "oracle_split": "invalid_conformer"}])
    assert "case_id" in df.columns
    assert "oracle_split" in df.columns
    assert "predicted_dominant_valid_rgroup" in df.columns


def test_delta_sensitivity_report_counts_status() -> None:
    module = _phase2_module()
    df = pd.DataFrame(
        [
            {"delta03_status": "target_severe", "delta04_status": "target_severe", "delta05_status": "no_target_severe"},
            {"delta03_status": "no_target_severe", "delta04_status": "target_severe", "delta05_status": "no_target_severe"},
        ]
    )
    report = module._delta_sensitivity_report(df)
    assert set(report["delta_angstrom"]) == {0.3, 0.4, 0.5}


def test_supported_cases_csv_filter_semantics() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "a", "oracle_split": "supported_single_rgroup"},
            {"case_id": "b", "oracle_split": "invalid_conformer"},
        ]
    )
    supported = df[df["oracle_split"] == "supported_single_rgroup"]
    assert list(supported["case_id"]) == ["a"]

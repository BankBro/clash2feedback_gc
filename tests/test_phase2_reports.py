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
            {"delta03_status": "", "delta04_status": "", "delta05_status": ""},
        ]
    )
    report = module._delta_sensitivity_report(df)
    assert set(report["delta_angstrom"]) == {0.3, 0.4, 0.5}
    assert all(str(column).strip() for column in report.columns)
    assert "unsupported_or_unavailable" in report.columns
    assert report["unsupported_or_unavailable"].sum() == 3


def test_energy_delta_reports_are_record_only_summaries() -> None:
    module = _phase2_module()
    df = pd.DataFrame(
        [
            {
                "case_id": "case_000001",
                "oracle_split": "supported_single_rgroup",
                "injection_mode": "easy_rotation",
                "target_rgroup": "R1",
                "forcefield_type": "MMFF",
                "energy_original": 1.0,
                "energy_failed": 2.0,
                "energy_delta": 1.0,
                "ligand_valid": True,
                "ligand_internal_severe_clash_count": 0,
                "target_num_severe_pairs": 1,
                "max_clash_depth": 0.6,
                "sample_path": "samples/case_000001.pkl",
                "failed_ligand_sdf": "ligands/case_000001_failed.sdf",
            },
            {
                "case_id": "case_000002",
                "oracle_split": "supported_single_rgroup",
                "injection_mode": "easy_rotation",
                "target_rgroup": "R1",
                "forcefield_type": "MMFF",
                "energy_original": 1.0,
                "energy_failed": 100.0,
                "energy_delta": 99.0,
                "ligand_valid": True,
                "ligand_internal_severe_clash_count": 0,
                "target_num_severe_pairs": 1,
                "max_clash_depth": 0.7,
                "sample_path": "samples/case_000002.pkl",
                "failed_ligand_sdf": "ligands/case_000002_failed.sdf",
            },
        ]
    )

    stats = module._energy_delta_stats_report(df)
    outliers = module._energy_delta_outliers_report(df)

    assert "num_large_positive_delta" in stats.columns
    assert int(stats["num_large_positive_delta"].sum()) == 1
    assert "energy_delta_strict_pass" in outliers.columns
    assert not bool(outliers.loc[outliers["case_id"] == "case_000002", "energy_delta_strict_pass"].iloc[0])


def test_supported_cases_csv_filter_semantics() -> None:
    df = pd.DataFrame(
        [
            {"case_id": "a", "oracle_split": "supported_single_rgroup"},
            {"case_id": "b", "oracle_split": "invalid_conformer"},
        ]
    )
    supported = df[df["oracle_split"] == "supported_single_rgroup"]
    assert list(supported["case_id"]) == ["a"]

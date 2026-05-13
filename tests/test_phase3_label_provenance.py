from pathlib import Path

import pandas as pd

from clash2feedback.feedback.mask_seed import (
    build_construction_consistency_report,
    build_field_dependency_table,
    build_phase3_outputs,
)
from clash2feedback.utils.config import load_yaml_config


def test_field_dependency_records_predicted_as_policy_not_truth() -> None:
    table = build_field_dependency_table()
    predicted = table[table["field_or_artifact"] == "predicted_dominant_valid_rgroup"].iloc[0]

    assert "operational predicted mask policy" in predicted["phase3_interpretation"]
    assert "not ground truth" in predicted["phase3_interpretation"]


def test_construction_consistency_uses_only_s2_denominator() -> None:
    manifest = pd.DataFrame(
        [
            {
                "case_id": "a",
                "set_membership_s2": True,
                "target_rgroup": "R1",
                "predicted_dominant_valid_rgroup": "R1",
                "top_valid_rgroups_json": '[{"region": "R1", "score": 1.0}]',
            },
            {
                "case_id": "b",
                "set_membership_s2": False,
                "target_rgroup": "R2",
                "predicted_dominant_valid_rgroup": "R2",
                "top_valid_rgroups_json": '[{"region": "R2", "score": 1.0}]',
            },
        ]
    )

    report = build_construction_consistency_report(manifest)
    top1 = report[report["metric_name"] == "construction_consistency_top1_predicted_equals_oracle"].iloc[0]

    assert int(top1["denominator"]) == 1
    assert bool(top1["not_independent_locator_benchmark"]) is True


def test_real_phase3_inputs_build_in_memory_when_available() -> None:
    config_path = Path("configs/phase3_label_provenance_audit.yaml")
    phase2_manifest = Path("data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet")
    processed_root = Path("data/processed/v0_1/complexes")
    if not config_path.exists() or not phase2_manifest.exists() or not processed_root.exists():
        return

    config = load_yaml_config(config_path)
    result = build_phase3_outputs(config, repo_root=Path.cwd(), write_outputs=False)
    summary = result.summary

    assert summary["phase3_not_independent_locator_benchmark"] is True
    assert summary["phase2_5_model_induced_audit"]["included_in_construction_consistency_denominator"] is False
    assert summary["phase4_mask_seed"]["rows"] == summary["set_counts"]["S2_phase2_supported_single_rgroup"]

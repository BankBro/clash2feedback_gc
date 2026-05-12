import pandas as pd

from clash2feedback.generation_audit.gap_analysis import artificial_vs_model_induced_gap
from clash2feedback.generation_audit.reports import (
    GENERATION_MANIFEST_COLUMNS,
    build_summary,
    empty_dataframe,
    schema_empty_reports,
)
from clash2feedback.generation_audit.taxonomy import FAILURE_TAXONOMY_COLUMNS, REPAIRABILITY_PROXY_COLUMNS


def test_generation_manifest_includes_all_samples_columns() -> None:
    df = empty_dataframe(GENERATION_MANIFEST_COLUMNS)
    for column in ["candidate_id", "generation_status", "postprocess_stage", "failure_taxonomy"]:
        assert column in df.columns


def test_summary_json_schema() -> None:
    summary = build_summary(
        config={"baseline": {"model_name": "DiffSBDD", "checkpoint_name": "x"}, "constraints": {}},
        overlap_summary={"tier_counts": {"T_unknown": 2}, "external_validity_subset_size": 2, "same_source_debug_subset_size": 0},
        base_selection=pd.DataFrame([{"selected_for_generation": True}]),
        generation_manifest=empty_dataframe(GENERATION_MANIFEST_COLUMNS),
        ligand_validity=pd.DataFrame(columns=["ligand_validity_status"]),
        failure_taxonomy=empty_dataframe(FAILURE_TAXONOMY_COLUMNS),
        repairability_proxy=empty_dataframe(REPAIRABILITY_PROXY_COLUMNS),
        blocked_reasons=["checkpoint_missing"],
    )
    assert summary["schema_version"] == "phase2_5_v0_1"
    assert summary["training_overlap_audit_done"] is True
    assert summary["does_not_repair"] is True


def test_failure_taxonomy_covers_all_samples_schema() -> None:
    reports = schema_empty_reports()
    assert "failure_taxonomy.csv" in reports
    assert "candidate_id" in reports["failure_taxonomy.csv"].columns


def test_gap_analysis_has_phase2_and_model_induced_groups() -> None:
    phase2 = pd.DataFrame(
        [
            {
                "oracle_split": "supported_single_rgroup",
                "target_num_severe_pairs": 1,
                "max_clash_depth": 0.5,
                "total_clash_score": 0.25,
                "dominant_ratio_valid_rgroups": 1.0,
                "ligand_internal_severe_clash_count": 0,
            }
        ]
    )
    model = pd.DataFrame([{"candidate_id": "c1", "num_severe_clash_pairs": 1, "max_clash_depth": 0.6, "total_clash_score": 0.36}])
    taxonomy = pd.DataFrame([{"candidate_id": "c1", "failure_taxonomy": "single_rgroup_clash"}])
    proxy = pd.DataFrame([{"candidate_id": "c1", "repairability_proxy": "local_rgroup_repair_possible"}])
    gap = artificial_vs_model_induced_gap(phase2, model, taxonomy, proxy)
    assert {"phase2_supported_single_rgroup", "model_induced_single_rgroup_clash", "model_induced_all_failures"}.issubset(set(gap["group"]))

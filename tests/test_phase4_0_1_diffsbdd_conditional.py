from pathlib import Path

import pandas as pd

from clash2feedback.repair.diffsbdd_anchor_filter import anchor_aware_filter_row
from clash2feedback.repair.fragment_diagnostics import analyze_candidate_fragment
from clash2feedback.repair.phase4_0_1 import (
    _backend_config_for_budget,
    _budget_curve,
    _failure_funnel,
    _select_preflight_cases,
)
from clash2feedback.repair.phase4_inputs import load_phase4_case_inputs
from clash2feedback.utils.config import load_yaml_config
from clash2feedback.verifier.phase4_adapter import RELIABLE_REPAIR_FIELDS


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs/phase4_0_1_diffsbdd_conditional_repair.yaml"


def _config() -> dict:
    return load_yaml_config(CONFIG_PATH)


def _selected_cases() -> pd.DataFrame:
    config = _config()
    return pd.read_csv(REPO_ROOT / config["inputs"]["phase4_0_selected_cases"])


def _case_input():
    config = _config()
    selected = _select_preflight_cases(_selected_cases(), config).head(1)
    return load_phase4_case_inputs(
        selected,
        phase2_manifest_path=REPO_ROOT / config["inputs"]["phase2_manifest"],
        phase2_benchmark_root=REPO_ROOT / config["inputs"]["phase2_benchmark_root"],
        processed_root=REPO_ROOT / config["inputs"]["processed_root"],
    )[0]


def test_phase4_0_1_config_only_runs_diffsbdd_conditional_pocket() -> None:
    config = _config()

    assert set(config["backends"]) == {"diffsbdd_conditional_inpainting"}
    assert config["experiment"]["center"] == "pocket"
    assert config["experiment"]["formal_budget_ks"] == [8, 16, 32]
    assert config["backends"]["diffsbdd_conditional_inpainting"]["uses_h_clash_in_generation"] is False
    assert config["backends"]["diffsbdd_conditional_inpainting"]["source_patch"]["modifies_denoising"] is False


def test_phase4_0_1_preflight_reuses_five_phase4_0_cases() -> None:
    selected = _select_preflight_cases(_selected_cases(), _config())

    assert selected["case_id"].tolist() == ["case_001300", "case_000509", "case_001316", "case_002080", "case_001704"]
    assert selected.shape[0] == 5
    assert selected["case_id"].isin(_selected_cases()["case_id"]).all()


def test_phase4_0_1_budget_maps_to_diffsbdd_n_samples_and_pocket_center() -> None:
    config = _config()
    backend_cfg = _backend_config_for_budget(config, 16)

    assert backend_cfg["n_samples"] == 16
    assert backend_cfg["centers"] == ["pocket"]


def test_fragment_diagnostics_and_anchor_filter_on_same_topology_candidate() -> None:
    case_input = _case_input()
    candidate = {
        "backend_name": "mock",
        "case_id": case_input.case_id,
        "attempt_id": f"mock:pocket:{case_input.case_id}",
        "candidate_id": "mock:001",
        "candidate_index": 1,
        "candidate_path": str(case_input.failed_ligand_sdf),
        "candidate_budget_k": 8,
    }

    diagnostics = analyze_candidate_fragment(candidate, case_input, tolerance=0.35)
    filter_row = anchor_aware_filter_row(diagnostics)

    assert diagnostics["fixed_structure_mapping_success_for_diagnostics"] is True
    assert diagnostics["generated_size_status"] == "matched"
    assert diagnostics["anchor_match_success"] is True
    assert diagnostics["generated_fragment_connected_to_anchor"] is True
    assert diagnostics["local_reconnect_pass"] is True
    assert filter_row["anchor_aware_filter_pass"] is True


def test_phase4_0_1_report_schema_helpers() -> None:
    selected = _selected_cases().head(2)
    candidate_rows = [
        {"candidate_budget_k": 8, "attempt_id": "a", "case_id": selected.iloc[0]["case_id"], "candidate_count": 1, "proposal_count": 8, "runtime_sec": 1.0, "failure_stage": ""},
        {"candidate_budget_k": 8, "attempt_id": "b", "case_id": selected.iloc[1]["case_id"], "candidate_count": 1, "proposal_count": 8, "runtime_sec": 1.0, "failure_stage": ""},
    ]
    verifier_rows = [
        {
            "candidate_budget_k": 8,
            "case_id": selected.iloc[0]["case_id"],
            "candidate_readable": True,
            "ligand_valid": True,
            "fixed_structure_match_success": True,
            "anchor_match_success": True,
            "local_reconnect_pass": True,
            "anchor_integrity": True,
            "old_clash_resolved": True,
            "no_new_severe_clash": True,
            "scaffold_stable": True,
            "keep_region_stable": True,
            "edit_compliance": True,
            "pocket_retention": True,
            "reliable_repair_success": True,
        },
        {"candidate_budget_k": 8, "case_id": selected.iloc[1]["case_id"], "reliable_repair_success": False},
    ]

    budget_curve = _budget_curve(selected, candidate_rows, verifier_rows)
    failure_funnel = _failure_funnel(selected, candidate_rows, verifier_rows)

    assert {"candidate_budget_k", "sample_reliable_success_count", "local_reconnect_pass_rate"} <= set(budget_curve.columns)
    assert {"candidate_budget_k", "funnel_step", "count", "denominator", "rate"} <= set(failure_funnel.columns)
    assert "local_reconnect_pass" in set(failure_funnel["funnel_step"])


def test_phase4_0_reliable_repair_standard_is_unchanged() -> None:
    assert RELIABLE_REPAIR_FIELDS == [
        "candidate_readable",
        "ligand_valid",
        "fixed_structure_match_success",
        "old_clash_resolved",
        "no_new_severe_clash",
        "scaffold_stable",
        "keep_region_stable",
        "anchor_integrity",
        "edit_compliance",
        "pocket_retention",
    ]

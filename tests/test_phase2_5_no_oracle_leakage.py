import inspect
from pathlib import Path

import yaml

from clash2feedback.generation_audit.taxonomy import classify_failure_taxonomy


def test_no_target_rgroup_required_for_model_induced_audit() -> None:
    signature = inspect.signature(classify_failure_taxonomy)
    assert "target_rgroup" not in signature.parameters


def test_predicted_dominant_not_ground_truth() -> None:
    row = classify_failure_taxonomy(
        candidate_id="c1",
        postprocess_stage="raw_generated",
        num_severe_clash_pairs=1,
        attribution_failure_type="single_rgroup_clash",
        dominant_valid_rgroup="R1",
        dominant_ratio_valid=1.0,
    )
    assert row["predicted_dominant_is_oracle_ground_truth"] is False


def test_generated_samples_not_mixed_into_phase3_top1() -> None:
    cfg = yaml.safe_load(Path("configs/phase2_5_model_induced_audit.yaml").read_text(encoding="utf-8"))
    assert cfg["constraints"]["do_not_mix_model_induced_into_phase3_main"] is True
    assert cfg["constraints"]["do_not_use_predicted_dominant_as_oracle"] is True

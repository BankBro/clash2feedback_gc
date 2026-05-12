from __future__ import annotations

from typing import Any

from clash2feedback.generation_audit import REPAIRABILITY_PROXY_LABELS, TAXONOMY_LABELS


FAILURE_TAXONOMY_COLUMNS = [
    "candidate_id",
    "postprocess_stage",
    "failure_taxonomy",
    "taxonomy_reason",
    "rgroup_attributable",
    "dominant_valid_rgroup",
    "dominant_ratio_valid",
    "dominant_ratio_all",
    "predicted_dominant_is_oracle_ground_truth",
]

REPAIRABILITY_PROXY_COLUMNS = [
    "candidate_id",
    "postprocess_stage",
    "repairability_proxy",
    "repairability_reason",
]


def classify_failure_taxonomy(
    *,
    candidate_id: str,
    postprocess_stage: str,
    generation_status: str = "ok",
    postprocess_status: str = "ok",
    ligand_valid: bool = True,
    ligand_validity_reason: str = "",
    num_clash_pairs: int = 0,
    num_severe_clash_pairs: int = 0,
    max_clash_depth: float = 0.0,
    rgroup_attributable: bool = True,
    attribution_failure_type: str = "",
    dominant_valid_rgroup: str = "",
    dominant_ratio_valid: float = 0.0,
    dominant_ratio_all: float = 0.0,
    scaffold_score: float = 0.0,
    unsupported_reasons: list[str] | None = None,
    global_pose_max_depth_angstrom: float = 1.5,
    global_pose_severe_pair_count: int = 20,
) -> dict[str, Any]:
    reasons = unsupported_reasons or []
    taxonomy = "valid_no_severe_clash"
    reason = ""
    if generation_status not in {"ok", "generated"} or postprocess_status not in {"ok", "standardized", "raw"}:
        taxonomy = "postprocess_failed"
        reason = f"generation_status={generation_status};postprocess_status={postprocess_status}"
    elif _unsupported_chemistry(ligand_validity_reason, reasons):
        taxonomy = "unsupported_chemistry"
        reason = ligand_validity_reason or ";".join(reasons)
    elif not ligand_valid:
        taxonomy = "ligand_only_invalid"
        reason = ligand_validity_reason
    elif num_severe_clash_pairs <= 0:
        taxonomy = "near_miss_contact" if num_clash_pairs > 0 else "valid_no_severe_clash"
        reason = "no_severe_clash"
    elif max_clash_depth > float(global_pose_max_depth_angstrom) or int(num_severe_clash_pairs) >= int(global_pose_severe_pair_count):
        taxonomy = "global_pose_failure"
        reason = "global_pose_threshold_exceeded"
    elif not rgroup_attributable:
        taxonomy = "rgroup_unattributable"
        reason = "scaffold_or_rgroup_decomposition_failed"
    elif attribution_failure_type == "single_rgroup_clash":
        taxonomy = "single_rgroup_clash"
        reason = "dominant_valid_rgroup"
    elif attribution_failure_type == "scaffold_clash" or scaffold_score > 0.0:
        taxonomy = "scaffold_clash"
        reason = "scaffold_region_dominant_or_scored"
    elif attribution_failure_type in {"multi_region_clash", "ambiguous_region_clash"}:
        taxonomy = "multi_region_clash"
        reason = attribution_failure_type
    elif attribution_failure_type == "global_pose_failure":
        taxonomy = "global_pose_failure"
        reason = attribution_failure_type
    elif attribution_failure_type in {"unsupported_chemistry", "unknown_or_unsupported"}:
        taxonomy = "unsupported_chemistry" if attribution_failure_type == "unsupported_chemistry" else "rgroup_unattributable"
        reason = attribution_failure_type
    else:
        taxonomy = "global_pose_failure"
        reason = "severe_clash_without_local_attribution"
    if taxonomy not in TAXONOMY_LABELS:
        raise ValueError(f"Unsupported taxonomy label: {taxonomy}")
    return {
        "candidate_id": candidate_id,
        "postprocess_stage": postprocess_stage,
        "failure_taxonomy": taxonomy,
        "taxonomy_reason": reason,
        "rgroup_attributable": bool(rgroup_attributable),
        "dominant_valid_rgroup": dominant_valid_rgroup,
        "dominant_ratio_valid": float(dominant_ratio_valid),
        "dominant_ratio_all": float(dominant_ratio_all),
        "predicted_dominant_is_oracle_ground_truth": False,
    }


def classify_repairability_proxy(
    taxonomy_row: dict[str, Any],
    *,
    max_clash_depth: float = 0.0,
    scaffold_score: float = 0.0,
    local_max_depth: float = 1.5,
) -> dict[str, Any]:
    taxonomy = str(taxonomy_row.get("failure_taxonomy", ""))
    proxy = "reject"
    reason = taxonomy
    if taxonomy == "single_rgroup_clash":
        if (
            bool(taxonomy_row.get("rgroup_attributable"))
            and str(taxonomy_row.get("dominant_valid_rgroup") or "")
            and float(taxonomy_row.get("dominant_ratio_valid") or 0.0) >= 0.7
            and float(scaffold_score) <= 0.0
            and float(max_clash_depth) <= float(local_max_depth)
        ):
            proxy = "local_rgroup_repair_possible"
            reason = "dominant_local_rgroup_and_depth_within_proxy"
        else:
            proxy = "reject"
            reason = "single_rgroup_proxy_gate_failed"
    elif taxonomy in {"global_pose_failure", "pocket_mismatch_or_out_of_scope"}:
        proxy = "global_repose_needed"
    elif taxonomy in {"ligand_only_invalid", "postprocess_failed"}:
        proxy = "invalid_unrepairable"
    elif taxonomy in {"unsupported_chemistry", "rgroup_unattributable"}:
        proxy = "unsupported"
    if proxy not in REPAIRABILITY_PROXY_LABELS:
        raise ValueError(f"Unsupported repairability proxy: {proxy}")
    return {
        "candidate_id": taxonomy_row.get("candidate_id", ""),
        "postprocess_stage": taxonomy_row.get("postprocess_stage", ""),
        "repairability_proxy": proxy,
        "repairability_reason": reason,
    }


def _unsupported_chemistry(reason: str, unsupported_reasons: list[str]) -> bool:
    text = " ".join([reason, *unsupported_reasons]).lower()
    return any(token in text for token in ["unsupported", "metal", "macrocycle", "disallowed_elements", "covalent"])

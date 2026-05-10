from __future__ import annotations

from typing import Any


REJECT_SPLITS = {"ambiguous_region", "multi_region", "scaffold_clash", "global_pose_failure"}


def region_clash_stats(clash_report: dict[str, Any], target_rgroup: str) -> dict[str, Any]:
    target_pairs = 0
    non_target_pairs = 0
    scaffold_pairs = 0
    total_severe = 0
    target_score = 0.0
    total_score = 0.0
    top_residue = ""
    top_depth = -1.0
    top_pairs: list[dict[str, Any]] = []
    for pair in clash_report.get("clash_pairs", []):
        depth = float(pair.get("clash_depth") or 0.0)
        region = str(pair.get("ligand_region") or "")
        score = depth * depth
        total_score += score
        if region == str(target_rgroup):
            target_score += score
        if depth > top_depth:
            top_depth = depth
            top_residue = str(pair.get("protein_residue_key") or "")
        if bool(pair.get("is_severe")):
            total_severe += 1
            if region == str(target_rgroup):
                target_pairs += 1
            elif region == "scaffold":
                scaffold_pairs += 1
            elif region.startswith("R"):
                non_target_pairs += 1
        top_pairs.append(pair)
    top_pairs = sorted(top_pairs, key=lambda item: float(item.get("clash_depth") or 0.0), reverse=True)[:5]
    return {
        "target_num_severe_pairs": int(target_pairs),
        "non_target_num_severe_pairs": int(non_target_pairs),
        "scaffold_num_severe_pairs": int(scaffold_pairs),
        "num_total_severe_pairs": int(total_severe),
        "target_total_score": float(target_score),
        "total_clash_score": float(total_score),
        "target_score_ratio_all": float(target_score / total_score) if total_score > 0.0 else 0.0,
        "top_clash_residue": top_residue,
        "top_clash_pairs": top_pairs,
    }


def target_score_ratio_valid(attribution: dict[str, Any], target_rgroup: str) -> float:
    scores = attribution.get("valid_rgroup_scores", {}) or {}
    total = float(sum(float(value) for value in scores.values() if float(value) > 0.0))
    target = float(scores.get(str(target_rgroup), 0.0))
    return float(target / total) if total > 0.0 else 0.0


def assign_oracle_split(
    *,
    ligand_quality: dict[str, Any],
    clash_report: dict[str, Any],
    attribution: dict[str, Any],
    target_rgroup: str,
    acceptance_cfg: dict[str, Any],
) -> dict[str, Any]:
    stats = region_clash_stats(clash_report, target_rgroup)
    ratio_valid = target_score_ratio_valid(attribution, target_rgroup)
    max_depth = float(clash_report.get("max_clash_depth") or 0.0)
    analysis_status = str(clash_report.get("analysis_status") or "ok")
    unsupported_reasons = list(clash_report.get("unsupported_reasons", []))

    oracle_split = "supported_single_rgroup"
    acceptance_status = "accepted"
    reject_reason = ""
    invalid_reason = ""
    unsupported_reason = ""

    if analysis_status != "ok" or unsupported_reasons:
        oracle_split = "unsupported"
        acceptance_status = "unsupported"
        unsupported_reason = ";".join(str(reason) for reason in unsupported_reasons) or analysis_status
    elif not bool(ligand_quality.get("ligand_valid", False)):
        oracle_split = "invalid_conformer"
        acceptance_status = "invalid"
        invalid_reason = ";".join(str(reason) for reason in ligand_quality.get("fatal_errors", [])) or "ligand_invalid"
    elif stats["target_num_severe_pairs"] < int(acceptance_cfg.get("min_target_severe_pairs", 1)):
        oracle_split = "near_miss_contact"
        acceptance_status = "near_miss"
        reject_reason = "target_severe_pairs_below_threshold"
    elif stats["scaffold_num_severe_pairs"] > int(acceptance_cfg.get("max_scaffold_severe_pairs", 0)):
        oracle_split = "scaffold_clash"
        acceptance_status = "reject"
        reject_reason = "scaffold_severe_pairs"
    elif stats["non_target_num_severe_pairs"] > int(acceptance_cfg.get("max_non_target_severe_pairs", 0)):
        oracle_split = "multi_region"
        acceptance_status = "reject"
        reject_reason = "non_target_severe_pairs"
    elif ratio_valid < float(acceptance_cfg.get("min_target_score_ratio_valid", 0.7)):
        oracle_split = "ambiguous_region"
        acceptance_status = "reject"
        reject_reason = "target_score_ratio_below_threshold"
    elif max_depth > float(acceptance_cfg.get("max_clash_depth_angstrom", 1.5)):
        oracle_split = "global_pose_failure"
        acceptance_status = "reject"
        reject_reason = "max_clash_depth_exceeds_threshold"

    return {
        **stats,
        "target_score_ratio_valid": float(ratio_valid),
        "oracle_split": oracle_split,
        "acceptance_status": acceptance_status,
        "reject_reason": reject_reason,
        "invalid_reason": invalid_reason,
        "unsupported_reason": unsupported_reason,
    }


def difficulty_bin(oracle_split: str, target_ratio: float, max_depth: float) -> tuple[str, str]:
    if oracle_split == "invalid_conformer":
        return "invalid", "ligand_self_invalid"
    if oracle_split == "unsupported":
        return "unsupported", "unsupported_chemistry_or_mask"
    if oracle_split != "supported_single_rgroup":
        return "hard", oracle_split
    if target_ratio >= 0.9 and max_depth <= 0.9:
        return "easy", "high_target_ratio_and_moderate_depth"
    return "medium", "supported_with_moderate_ambiguity_or_depth"
